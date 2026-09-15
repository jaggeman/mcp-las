import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.firebase_client import db_client
from src.embeddings.embedder import Embedder

from src.db.cba_data import CBA_RULES_DATA

CURATED_COLLECTIVE_AGREEMENTS = CBA_RULES_DATA

sparade = 0
if db_client.db is None:
    print("AVBRUTET: Firestore ar inte initierat - ingenting skulle sparas.")
    print("Kontrollera FIREBASE_PROJECT_ID och FIREBASE_CREDENTIALS_PATH i .env.")
    sys.exit(1)

print(f"Laddar upp {len(CURATED_COLLECTIVE_AGREEMENTS)} kollektivavtal till Firebase...")
misslyckade = []
for rule in CURATED_COLLECTIVE_AGREEMENTS:
    rule_dict = dict(rule)
    rule_dict["embedding"] = Embedder.get_embedding(rule_dict["topic"] + " " + rule_dict["rule_content"])
    etikett = f"{rule_dict['agreement_name']} ({rule_dict['topic']})"
    if db_client.save_cba_rule(rule_dict):
        sparade += 1
        print(f" - Sparad i Firestore: {etikett}")
    else:
        misslyckade.append(etikett)
        print(f" - MISSLYCKADES: {etikett}")

print(f"\nKlart: {sparade} av {len(CURATED_COLLECTIVE_AGREEMENTS)} regler sparade i Firestore.")
if misslyckade:
    print(f"{len(misslyckade)} skrivningar gick inte igenom - se varningarna ovan.")

# Samma krav som pa de ovriga ingestionsskripten sedan #32: skriv bara ut det
# som faktiskt hamnade i databasen, och avsluta med en kod som gor att ett
# skal-skript eller en agent inte gar vidare i tron att steget lyckades.
sys.exit(0 if sparade == len(CURATED_COLLECTIVE_AGREEMENTS) else 1)
