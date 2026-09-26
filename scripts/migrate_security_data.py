"""One-off, idempotent migration for hashed API keys and request retention."""

import argparse
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.firebase_client import db_client


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def prepare_api_keys() -> dict:
    """Create hash-addressed copies while legacy readers still use raw IDs."""
    prepared = skipped = 0
    for document in db_client.db.collection("api_keys").stream():
        data = document.to_dict()
        raw_key = data.get("key")
        if not isinstance(raw_key, str) or not raw_key:
            skipped += 1
            continue
        clean = {key: value for key, value in data.items() if key != "key"}
        clean["key_version"] = 2
        clean["key_digest"] = _digest(raw_key)
        db_client.db.collection("api_keys").document(clean["key_digest"]).set(clean)
        prepared += 1
    return {"prepared": prepared, "skipped": skipped}


def cleanup_legacy_api_keys() -> dict:
    """Remove records whose raw bearer secret is stored in an ID or field."""
    removed = cleaned = 0
    documents = list(db_client.db.collection("api_keys").stream())
    for document in documents:
        data = document.to_dict()
        raw_key = data.get("key")
        if not isinstance(raw_key, str) or not raw_key:
            continue
        digest = _digest(raw_key)
        target = db_client.db.collection("api_keys").document(digest).get()
        if not target.exists:
            raise RuntimeError("Hash-addressed replacement is missing; refusing cleanup")
        if document.id == digest:
            clean = {key: value for key, value in data.items() if key != "key"}
            clean["key_version"] = 2
            clean["key_digest"] = digest
            document.reference.set(clean)
            cleaned += 1
        else:
            document.reference.delete()
            removed += 1
    return {"removed": removed, "cleaned": cleaned}


def backfill_request_expiry(days: int = 90) -> dict:
    updated = 0
    now = datetime.now(timezone.utc)
    for document in db_client.db.collection("key_requests").stream():
        data = document.to_dict()
        if data.get("expires_at") is not None:
            continue
        created = data.get("created_at")
        try:
            created_at = datetime.fromisoformat(created) if isinstance(created, str) else now
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
        except ValueError:
            created_at = now
        updates = {"expires_at": created_at + timedelta(days=days)}
        if "key_issued" in data:
            from google.cloud import firestore
            updates["key_issued"] = firestore.DELETE_FIELD
        document.reference.update(updates)
        updated += 1
    return {"request_expiry_updated": updated}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "cleanup", "retention"))
    args = parser.parse_args()
    if db_client.db is None:
        raise SystemExit("Firestore is unavailable")
    if args.phase == "prepare":
        result = prepare_api_keys()
    elif args.phase == "cleanup":
        result = cleanup_legacy_api_keys()
    else:
        result = backfill_request_expiry()
    print(result)


if __name__ == "__main__":
    main()
