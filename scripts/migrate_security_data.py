"""One-off, idempotent migration for hashed API keys and request retention."""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.firebase_client import db_client
from src.services.api_key_digest import migrate_v2_identifier


def prepare_api_keys() -> dict:
    """Create peppered v3 copies of existing v2 digest-addressed records."""
    prepared = skipped = 0
    for document in db_client.db.collection("api_keys").stream():
        data = document.to_dict()
        old_identifier = data.get("key_digest")
        if data.get("key_version") != 2 or not isinstance(old_identifier, str) or len(old_identifier) != 64:
            skipped += 1
            continue
        clean = dict(data)
        clean["key_version"] = 3
        clean["key_digest"] = migrate_v2_identifier(old_identifier)
        db_client.db.collection("api_keys").document(clean["key_digest"]).set(clean)
        prepared += 1
    return {"prepared": prepared, "skipped": skipped}


def cleanup_legacy_api_keys() -> dict:
    """Remove v2 records only after their peppered v3 replacement exists."""
    removed = skipped = 0
    documents = list(db_client.db.collection("api_keys").stream())
    for document in documents:
        data = document.to_dict()
        old_identifier = data.get("key_digest")
        if data.get("key_version") != 2 or not isinstance(old_identifier, str):
            skipped += 1
            continue
        digest = migrate_v2_identifier(old_identifier)
        target = db_client.db.collection("api_keys").document(digest).get()
        if not target.exists or target.to_dict().get("key_version") != 3:
            raise RuntimeError("Hash-addressed replacement is missing; refusing cleanup")
        document.reference.delete()
        removed += 1
    return {"removed": removed, "skipped": skipped}


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
    if not isinstance(result, dict):
        raise RuntimeError("Migration returned an invalid result")
    print("Migration completed successfully.")


if __name__ == "__main__":
    main()
