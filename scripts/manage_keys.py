import sys
import secrets
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.db.firebase_client import db_client

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
    random_part = secrets.token_hex(6)
    safe_comp = company.lower().replace(" ", "_")
    key_id = f"las_live_{safe_comp}_{random_part}"
    
    key_data = {
        "key": key_id,
        "name": f"{name} ({company})",
        "email": email,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
        "total_requests": 0
    }
    
    db_client.db.collection("api_keys").document(key_id).set(key_data)
    req_doc.reference.update({"status": "approved", "approved_at": datetime.now(timezone.utc).isoformat(), "key_issued": key_id})
    
    print("\n" + "="*60)
    print(f"✅ ANSÖKAN GODKÄND FÖR: {name} <{email}>")
    print("="*60)
    print(f"\nSkapad API-Nyckel: {key_id}")
    print(f"\n--- KOPIERA OCH MAILA DETTA TILL ANVÄNDAREN ---")
    print(f"Hej {name},\n")
    print("Din ansökan om tillgång till MCP LAS är godkänd!")
    print("Här är din personliga anslutningskonfiguration för Claude Desktop / Cursor:\n")
    print("{\n  \"mcpServers\": {\n    \"mcp-las\": {\n      \"url\": \"https://mcp-las-511579677488.europe-north1.run.app/sse?key=" + key_id + "\"\n    }\n  }\n}\n")
    print("Mvh,\nFörvaltningen för MCP LAS")
    print("="*60 + "\n")

def create_key(name: str):
    random_part = secrets.token_hex(6)
    safe_name = name.lower().replace(" ", "_")
    key_id = f"las_live_{safe_name}_{random_part}"
    
    key_data = {
        "key": key_id,
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
        "total_requests": 0
    }
    db_client.db.collection("api_keys").document(key_id).set(key_data)
    print(f"\nNy API-nyckel skapad: {key_id}\nLänk: https://mcp-las-511579677488.europe-north1.run.app/sse?key={key_id}\n")

def list_keys():
    docs = list(db_client.db.collection("api_keys").stream())
    print(f"\n=== AKTIVA API-NYCKLAR ({len(docs)} st) ===")
    for d in docs:
        data = d.to_dict()
        status = "AKTIV" if data.get("is_active") else "AVSTÄNGD"
        print(f" - [{status}] {data.get('name')} | Nyckel: {data.get('key')}")

def deactivate_key(key_id: str):
    db_client.db.collection("api_keys").document(key_id).update({"is_active": False})
    print(f"Nyckeln {key_id} är nu AVSTÄNGD.")

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
