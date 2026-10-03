"""Synchronise official AD referats to Firestore.

No local summaries are accepted. Decisions that Arbetsdomstolen marks as not
reported are excluded because there is no public source text to index.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.firebase_client import db_client
from src.embeddings.embedder import Embedder
from src.scrapers.arbetsdomstolen_fetcher import fetch_verified_precedents


_SYNC_FIELDS = (
    "case_number", "year", "title", "summary", "source", "source_url",
    "verification_status", "active",
)


def run(start_year=2003, end_year=None, *, database=db_client,
        fetcher=fetch_verified_precedents, embedder=Embedder.get_embedding):
    if database.db is None:
        raise RuntimeError("Firestore är inte initierat; inga rättsfall har sparats")

    rows = fetcher(
        start_year=start_year,
        end_year=end_year or date.today().year,
    )
    if not rows:
        raise RuntimeError("Arbetsdomstolens arkiv gav inga verifierade referat")

    existing = {
        row.get("case_number"): row
        for row in database.list_precedents_for_sync()
        if row.get("case_number")
    }
    changed = 0
    skipped = 0
    for row in rows:
        previous = existing.get(row["case_number"])
        if previous and all(previous.get(field) == row.get(field) for field in _SYNC_FIELDS):
            skipped += 1
            continue
        stored = dict(row)
        stored["embedding"] = embedder(stored["summary"])
        if not database.save_precedent(stored):
            raise RuntimeError(f"Kunde inte spara verifierat rättsfall: {row['case_number']}")
        changed += 1
    report = {"fetched": len(rows), "changed": changed, "skipped": skipped}
    print(f"AD-synk klar: {changed} uppdaterade, {skipped} oförändrade av {len(rows)} referat.")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synka officiella AD-referat till Firestore")
    parser.add_argument("--start-year", type=int, default=2003)
    parser.add_argument("--end-year", type=int)
    args = parser.parse_args()
    try:
        run(args.start_year, args.end_year)
    except Exception as exc:
        print(f"AD-synk misslyckades: {exc}", file=sys.stderr)
        raise SystemExit(1)
