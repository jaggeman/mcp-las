"""Idempotent synchronization of official legal sources into the search index."""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Iterable

from src.db.firebase_client import db_client
from src.embeddings.embedder import Embedder
from src.scrapers.riksdagen_fetcher import RiksdagenFetcher


DEFAULT_STATUTES = (
    "1982:80",
    "1977:480",
    "1976:580",
    "1982:673",
    "2008:567",
)


def content_hash(value: str) -> str:
    """Return a stable SHA-256 fingerprint for source content."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class SourceSyncService:
    """Fetch, fingerprint and index statutes without rewriting unchanged data."""

    def __init__(self, db: Any = db_client, fetcher: Any = RiksdagenFetcher, embedder: Any = Embedder):
        self.db = db
        self.fetcher = fetcher
        self.embedder = embedder

    def sync_statutes(self, statutes: Iterable[str] = DEFAULT_STATUTES) -> Dict[str, Any]:
        result: Dict[str, Any] = {"changed": 0, "skipped": 0, "errors": 0, "items": []}

        for sfs_number in statutes:
            source_id = f"statute:{sfs_number}"
            try:
                metadata, sections = self.fetcher.get_statute(sfs_number)
                fingerprint_input = metadata.model_dump_json() if hasattr(metadata, "model_dump_json") else str(metadata.model_dump())
                fingerprint_input += "\n" + "\n".join(section.raw_text for section in sections)
                fingerprint = content_hash(fingerprint_input)
                previous = self.db.get_sync_state(source_id) or {}

                if previous.get("content_hash") == fingerprint and previous.get("status") == "success":
                    result["skipped"] += 1
                    result["items"].append({"source_id": source_id, "status": "skipped"})
                    continue

                self.db.save_statute(metadata.model_dump())
                for section in sections:
                    section_data = section.model_dump()
                    section_data["embedding"] = self.embedder.get_embedding(section.raw_text)
                    self.db.save_statute_section(section_data)

                state = {
                    "source_id": source_id,
                    "content_hash": fingerprint,
                    "source_url": metadata.document_url,
                    "section_count": len(sections),
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                    "status": "success",
                }
                self.db.save_sync_state(source_id, state)
                result["changed"] += 1
                result["items"].append({"source_id": source_id, "status": "changed", "sections": len(sections)})
            except Exception as exc:
                result["errors"] += 1
                result["items"].append({"source_id": source_id, "status": "error", "error": str(exc)})
                self.db.save_sync_state(source_id, {
                    "source_id": source_id,
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                    "status": "error",
                    "error": str(exc),
                })

        result["status"] = "error" if result["errors"] else "success"
        return result
