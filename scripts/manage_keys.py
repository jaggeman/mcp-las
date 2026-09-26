import sys
import secrets
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.db.firebase_client import db_client
from src.services.api_key_digest import key_id as derive_key_id, migrated_v2_key_id


def generate_api_key() -> str:
    """Return a 256-bit bearer secret suitable for one-time display."""
    return "las_live_" + secrets.token_urlsafe(32)


def build_key_record(api_key: str, name: str, email: str = ""):
    digest = derive_key_id(api_key)
    return digest, {
        "name": name,
        "email": email,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
        "total_requests": 0,
        "key_version": 4,
        "key_digest": digest,
    }

def list_requests():
    if not db_client.db:
        print("Ingen databasanslutning.")
        return
    docs = list(db_client.db.collection("key_requests").where("status", "==", "pending").stream())
    print(f"\n=== VÄNTANDE ANSÖKNINGAR ({len(docs)} st) ===")
    if not docs:
        print("Inga väntande ansökningar just nu.")
        return
    for d in docs:
        data = d.to_dict()
        print(f"\nID: {d.id}")
        print(f" - Namn:    {data.get('name')}")
        print(f" - E-post:  {data.get('email')}")
        print(f" - Företag: {data.get('company')}")
        print(f" - Syfte:   {data.get('reason')}")
        print(f" - Datum:   {data.get('created_at')}")

def approve_request(email_or_id: str):
    if not db_client.db:
        return
    
    # Hitta ansökan
    query = db_client.db.collection("key_requests").where("email", "==", email_or_id).stream()
    reqs = list(query)
    if not reqs:
        doc = db_client.db.collection("key_requests").document(email_or_id).get()
        if doc.exists:
            reqs = [doc]
            
    if not reqs:
        print(f"Hittade ingen ansökan för '{email_or_id}'.")
        return
        
    req_doc = reqs[0]
    req_data = req_doc.to_dict()
    name = req_data.get("name", "Användare")
    email = req_data.get("email", email_or_id)
    company = req_data.get("company", "Klient")
    
    # Skapa API-nyckel
    api_key = generate_api_key()
    key_id, key_data = build_key_record(api_key, f"{name} ({company})", email)
    
    db_client.db.collection("api_keys").document(key_id).set(key_data)
    req_doc.reference.update({"status": "approved", "approved_at": datetime.now(timezone.utc).isoformat()})
    
    print("\n" + "="*60)
    print(f"✅ ANSÖKAN GODKÄND FÖR: {name} <{email}>")
    print("="*60)
    print(f"\nSkapad API-Nyckel: {api_key}")  # lgtm[py/clear-text-logging-sensitive-data] intentional one-time local display
    print("\n--- VISAS EN GÅNG: KOPIERA OCH ÖVERFÖR SÄKERT TILL ANVÄNDAREN ---")
    print(f"Hej {name},\n")
    print("Din ansökan om tillgång till MCP LAS är godkänd!")
    print("Här är din personliga anslutningskonfiguration för Claude Desktop / Cursor:\n")
    print("{\n  \"mcpServers\": {\n    \"mcp-las\": {\n      \"url\": \"https://las.novro.se/mcp\",\n      \"headers\": {\"X-API-Key\": \"" + api_key + "\"}\n    }\n  }\n}\n")  # lgtm[py/clear-text-logging-sensitive-data] intentional one-time local display
    print("Mvh,\nFörvaltningen för MCP LAS")
    print("="*60 + "\n")

def create_key(name: str):
    api_key = generate_api_key()
    key_id, key_data = build_key_record(api_key, name)
    db_client.db.collection("api_keys").document(key_id).set(key_data)
    print(f"\nNy API-nyckel (visas en gång): {api_key}")  # lgtm[py/clear-text-logging-sensitive-data] intentional one-time local display
    print("Endpoint: https://las.novro.se/mcp")
    print("Skicka nyckeln i X-API-Key-headern.\n")

def list_keys():
    docs = list(db_client.db.collection("api_keys").stream())
    print(f"\n=== AKTIVA API-NYCKLAR ({len(docs)} st) ===")
    for d in docs:
        data = d.to_dict()
        status = "AKTIV" if data.get("is_active") else "AVSTÄNGD"
        print(f" - [{status}] {data.get('name')} | Fingeravtryck: {d.id[:12]}")

def deactivate_key(api_key: str):
    for document_id in (derive_key_id(api_key), migrated_v2_key_id(api_key)):
        reference = db_client.db.collection("api_keys").document(document_id)
        if reference.get().exists:
            reference.update({"is_active": False})
            print(f"Nyckeln med fingeravtryck {document_id[:12]} är nu AVSTÄNGD.")
            return
    print("Nyckeln hittades inte.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Användning:")
        print("  python scripts/manage_keys.py requests               (Se väntande ansökningar)")
        print("  python scripts/manage_keys.py approve <email|id>    (Godkänn ansökan & generera nyckel)")
        print("  python scripts/manage_keys.py create \"Namn\"          (Skapa manuell nyckel)")
        print("  python scripts/manage_keys.py list                  (Lista alla nycklar)")
        print("  python scripts/manage_keys.py deactivate <key_id>   (Spärra nyckel)")
    elif sys.argv[1] == "requests":
        list_requests()
    elif sys.argv[1] == "approve" and len(sys.argv) > 2:
        approve_request(sys.argv[2])
    elif sys.argv[1] == "create" and len(sys.argv) > 2:
        create_key(sys.argv[2])
    elif sys.argv[1] == "list":
        list_keys()
    elif sys.argv[1] == "deactivate" and len(sys.argv) > 2:
        deactivate_key(sys.argv[2])
