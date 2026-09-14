import os
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.riksdagen_fetcher import RiksdagenFetcher
from src.db.firebase_client import db_client
from src.embeddings.embedder import Embedder
from src.services.sync_service import DEFAULT_STATUTES

# En enda kalla: samma lista som veckosynken anvander, sa de aldrig glider isar.
DEFAULT_LAWS = list(DEFAULT_STATUTES)

def run_ingestion(laws=None):
    if laws is None:
        laws = DEFAULT_LAWS

    # Utan databas skriver ingestionen ingenting. Sag det innan arbetet borjar
    # i stallet for att kora klart och rapportera rader som aldrig sparades.
    if db_client.db is None:
        print("\n" + "=" * 60)
        print("AVBRUTET: Firestore ar inte initierat.")
        print("Ingenting skulle sparas - allt hamnar bara i minnet och")
        print("forsvinner nar processen avslutas.")
        print("")
        print("Kontrollera .env:")
        print("  FIREBASE_PROJECT_ID=paygap-prod")
        print("  FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json")
        print("=" * 60 + "\n")
        return None

    print(f"Starting ingestion for {len(laws)} statutes from Riksdagens API...")

    total_sections_count = 0
    statutes_summary = []

    for sfs in laws:
        try:
            print(f"\n--> Fetching SFS {sfs}...")
            metadata, sections = RiksdagenFetcher.get_statute(sfs)
            print(f"    Fetched {metadata.title}: parsed {len(sections)} sections.")

            # Save metadata
            db_client.save_statute(metadata.model_dump())

            # Rakna det som FAKTISKT persisterades. Tidigare rakandes varje
            # forsok, sa skriptet kunde rapportera "492 sections indexed" med
            # noll rader i databasen - antingen for att credentials saknades
            # eller for att skrivfelet svaldes.
            for sec in sections:
                sec_dict = sec.model_dump()
                sec_dict["embedding"] = Embedder.get_embedding(sec.raw_text)
                if db_client.save_statute_section(sec_dict):
                    total_sections_count += 1

            statutes_summary.append({
                "sfs": sfs,
                "short": metadata.short_name,
                "sections": len(sections)
            })
        except Exception as e:
            print(f"    Error processing SFS {sfs}: {e}")

    print(f"\n==========================================")
    if total_sections_count == 0:
        print("INGET SPARADES. Noll paragrafer nadde databasen.")
        print("Kontrollera behorigheter och projekt-id innan du litar pa nagot ovan.")
    else:
        print(f"Ingestion completed! Total sections PERSISTED: {total_sections_count}")
    for s in statutes_summary:
        print(f" - {s['short']} ({s['sfs']}): {s['sections']} paragrafer")
    print(f"==========================================")
    return total_sections_count

if __name__ == "__main__":
    target = sys.argv[1:] if len(sys.argv) > 1 else None
    resultat = run_ingestion(target)
    # Exit-kod skild fran noll nar ingenting sparades, sa ett skal-skript eller
    # en agent inte gar vidare i tron att steget lyckades.
    sys.exit(1 if not resultat else 0)
