import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.firebase_client import db_client
from src.embeddings.embedder import Embedder
from src.db.ad_cases_data import AD_PRECEDENTS_DATA

CENTRAL_AD_CASES = AD_PRECEDENTS_DATA

print(f"Laddar upp {len(CENTRAL_AD_CASES)} AD-domar till Firestore...")
for c in CENTRAL_AD_CASES:
    c_dict = dict(c)
    c_dict["embedding"] = Embedder.get_embedding(c_dict["title"] + " " + c_dict["summary"] + " " + c_dict["domskal"])
    db_client.save_precedent(c_dict)
    print(f" - Sparad: {c_dict['case_number']}: {c_dict['title']}")

print(f"\nKlar! Nu finns alla {len(CENTRAL_AD_CASES)} AD-domar sparade!")
