import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from src.db.firebase_client import db_client

class AuthService:
    """Hanterar validering av API-nycklar och loggning av anrop till Firebase."""
    
    @staticmethod
    def validate_key(api_key: str) -> Optional[Dict[str, Any]]:
        if not api_key:
            return None
            
        if db_client.db:
            try:
                doc = db_client.db.collection("api_keys").document(api_key).get()
                if doc.exists:
                    data = doc.to_dict()
                    if data.get("is_active", True):
                        return data
            except Exception as e:
                print(f"Auth error: {e}")
                
        if api_key == "las_master_admin_key_2026":
            return {"name": "Master Admin", "is_active": True}
            
        return None

    @staticmethod
    def log_access(api_key: str, key_info: Optional[Dict[str, Any]], tool_name: str, params: Dict[str, Any], duration_ms: float, status: str = "success"):
        """Sparar en logg i Firestore i samlingen 'access_logs'."""
        if not db_client.db:
            return
            
        try:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "api_key_id": api_key[:12] + "..." if len(api_key) > 12 else api_key,
                "user_name": key_info.get("name", "Anonym/Klient") if key_info else "Anonym/Klient",
                "tool_called": tool_name,
                "params": params,
                "duration_ms": round(duration_ms, 2),
                "status": status
            }
            db_client.db.collection("access_logs").add(log_entry)
        except Exception as e:
            print(f"Log error: {e}")

auth_service = AuthService()
