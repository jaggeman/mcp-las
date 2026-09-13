import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.firebase_client import db_client
from src.embeddings.embedder import Embedder

from src.db.cba_data import CBA_RULES_DATA

CURATED_COLLECTIVE_AGREEMENTS = CBA_RULES_DATA

print(f"Laddar upp {len(CURATED_COLLECTIVE_AGREEMENTS)} kollektivavtal till Firebase...")
for rule in CURATED_COLLECTIVE_AGREEMENTS:
    rule_dict = dict(rule)
    rule_dict["embedding"] = Embedder.get_embedding(rule_dict["topic"] + " " + rule_dict["rule_content"])
    db_client.save_cba_rule(rule_dict)
    print(f" - Sparad i Firestore: {rule_dict['agreement_name']} ({rule_dict['topic']})")

print("\nAlla kollektivavtal är uppladdade till Firebase Firestore!")
