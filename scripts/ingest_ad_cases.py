import sys
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.firebase_client import db_client
from src.embeddings.embedder import Embedder
from src.db.ad_cases_data import AD_PRECEDENTS_DATA

CENTRAL_AD_CASES = AD_PRECEDENTS_DATA

sparade = 0
if db_client.db is None:
    print("AVBRUTET: Firestore ar inte initierat - ingenting skulle sparas.")
    print("Kontrollera FIREBASE_PROJECT_ID och FIREBASE_CREDENTIALS_PATH i .env.")
    sys.exit(1)

print(f"Laddar upp {len(CENTRAL_AD_CASES)} AD-domar till Firestore...")
for c in CENTRAL_AD_CASES:
    c_dict = dict(c)
    c_dict["embedding"] = Embedder.get_embedding(c_dict["title"] + " " + c_dict["summary"] + " " + c_dict["domskal"])
    sparade += 1 if db_client.save_precedent(c_dict) else 0
    print(f" - Sparad: {c_dict['case_number']}: {c_dict['title']}")

print(f"\nKlart: {sparade} av {len(CENTRAL_AD_CASES)} rader sparade i databasen.")
sys.exit(0 if sparade else 1)
