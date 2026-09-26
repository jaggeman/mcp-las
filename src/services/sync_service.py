"""Idempotent synchronization of official legal sources into the search index."""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Iterable

from src.db.firebase_client import db_client
from src.embeddings.embedder import Embedder
from src.scrapers.riksdagen_fetcher import RiksdagenFetcher
from src.scrapers.retsinformation_fetcher import RetsinformationFetcher
from src.scrapers.finlex_fetcher import FinlexFetcher


DEFAULT_STATUTES = (
    "1982:80",    # LAS
    "1977:480",   # Semesterlagen
    "1976:580",   # MBL
    "1982:673",   # Arbetstidslagen
    "2008:567",   # Diskrimineringslagen
    "1991:1047",  # Sjuklonelagen
    "1977:1160",  # Arbetsmiljolagen
    "1995:584",   # Foraldraledighetslagen
    "1974:981",   # Studieledighetslagen
    "1997:1293",  # Ledighet for att bedriva naringsverksamhet
    "1970:215",   # Arbetsgivares kvittningsratt
)


def content_hash(value: str) -> str:
    """Return a stable SHA-256 fingerprint for source content."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class SourceSyncService:
    """Independent source updates, with confirmed writes and recoverable retirement."""

    def __init__(self, db=db_client, fetcher=RiksdagenFetcher, embedder=Embedder,
                 danish_fetcher=RetsinformationFetcher, finnish_fetcher=FinlexFetcher):
        self.db, self.fetcher, self.embedder = db, fetcher, embedder
        self.danish_fetcher, self.finnish_fetcher = danish_fetcher, finnish_fetcher

    def _sync_one(self, source_id, metadata, sections, country):
        if isinstance(sections, Exception):
            raise sections
        if not sections:
            raise ValueError("Empty source; refusing to replace existing statute")
        metadata = dict(metadata)
        metadata.setdefault("jurisdiction", country)
        metadata.setdefault("language", {"SE":"sv","DK":"da","FI":"fi","NO":"nb","DE":"de","ES":"es"}[country])
        model = self.embedder.fingerprint()
        fingerprint = content_hash('atomic-v1:' + str(metadata) + model + "\n" + "\n".join(s.raw_text for s in sections))
        previous = self.db.get_sync_state(source_id) or {}
        if previous.get("content_hash") == fingerprint and previous.get("status") == "success":
            if self.db.save_sync_state(source_id, dict(previous, checked_at=datetime.now(timezone.utc).isoformat())) is not True:
                raise RuntimeError("Could not persist sync check")
            return {"source_id":source_id, "status":"skipped"}
        rows = []
        for section in sections:
            row = section.model_dump()
            row.update({k:metadata[k] for k in ("jurisdiction","language","source","source_url","license","attribution") if k in metadata})
            row.update(active=True, embedding_model=model, embedding=self.embedder.get_embedding(section.raw_text))
            rows.append(row)
        ids = {r["id"] for r in rows}
        if len(ids) != len(rows):
            raise ValueError("Duplicate section IDs")
        statute_id = rows[0].get("statute_id") or metadata.get("statute_id") or metadata["id"]
        metadata["total_sections"] = len(rows)
        state = {"source_id":source_id, "content_hash":fingerprint, "embedding_model":model,
                 "synced_at":datetime.now(timezone.utc).isoformat(), "status":"success",
                 "section_count":len(rows), "source_url":metadata.get("source_url") or metadata.get("document_url")}
        if self.db.publish_statute(source_id, metadata, rows, statute_id, country, state) is not True:
            raise RuntimeError('Could not publish statute')
        return {"source_id":source_id, "status":"changed", "sections":len(rows)}

    def _run(self, jobs, country):
        result = {"changed":0,"skipped":0,"errors":0,"items":[]}
        try:
            for source_id, loader in jobs:
                try:
                    metadata, sections = loader()
                    item = self._sync_one(source_id, metadata, sections, country)
                    result[item["status"]] += 1
                    result["items"].append(item)
                except Exception as exc:
                    result["errors"] += 1
                    result["items"].append({"source_id":source_id,"status":"error","error":str(exc)})
                    self.db.save_sync_state(source_id, {"source_id":source_id,"status":"error",
                        "error":str(exc),"synced_at":datetime.now(timezone.utc).isoformat()})
        except Exception as exc:
            result["errors"] += 1
            result["items"].append({"source_id":country,"status":"error","error":str(exc)})
        result["status"] = "error" if result["errors"] else "success"
        save_sync_state = getattr(self.db, "save_sync_state", None)
        if not callable(save_sync_state):
            return result
        status_saved = save_sync_state(f"coverage:{country}", {
            "jurisdiction": country,
            "status": result["status"],
            "changed": result["changed"],
            "skipped": result["skipped"],
            "errors": result["errors"],
            "synced_at": datetime.now(timezone.utc).isoformat(),
        })
        if status_saved is not True:
            if result["errors"] == 0:
                result["errors"] = 1
            result["status"] = "error"
            result["items"].append({"source_id": f"coverage:{country}", "status": "error",
                                    "error": "Could not persist country sync status"})
        return result

    def sync_statutes(self, statutes=DEFAULT_STATUTES):
        def load(sfs):
            metadata, sections = self.fetcher.get_statute(sfs)
            return metadata.model_dump(), sections
        return self._run(((f"statute:{sfs}",lambda sfs=sfs:load(sfs)) for sfs in statutes),"SE")

    def sync_european_statutes(self, jurisdiction):
        from src.scrapers.european_labor_fetcher import EuropeanLaborFetcher
        def jobs():
            for meta, sections in EuropeanLaborFetcher.iter_documents(jurisdiction):
                yield meta["id"], lambda m=meta,s=sections:(m,s)
        return self._run(jobs(),jurisdiction)

    def sync_spanish_statutes(self):
        from src.scrapers.boe_fetcher import BoeFetcher
        def jobs():
            for meta, sections in BoeFetcher.iter_documents():
                yield meta['id'], lambda m=meta, s=sections: (m, s)
        return self._run(jobs(), 'ES')

    def _sync_foreign(self, documents, fetcher, country):
        def jobs():
            sources = documents if documents is not None else fetcher.catalog_documents()
            for document in sources:
                doc_id = document.get("id") or document.get("documentId") or document.get("document_id") or document.get("akn_uri")
                prefix = "finnish" if country=="FI" else "danish"
                try:
                    metadata, sections = fetcher.get_document(document)
                    if country=="FI":
                        doc_id = str(metadata.get("statute_id") or doc_id).replace("/","_")
                    yield f"{prefix}:{doc_id}", lambda m=metadata,s=sections:(m,s)
                except Exception as exc:
                    yield f"{prefix}:{str(doc_id).replace('/','_')}", lambda e=exc:({},e)
        return self._run(jobs(),country)

    def sync_danish_documents(self, documents=None):
        return self._sync_foreign(documents,self.danish_fetcher,"DK")

    def sync_finnish_documents(self, documents=None):
        return self._sync_foreign(documents,self.finnish_fetcher,"FI")
