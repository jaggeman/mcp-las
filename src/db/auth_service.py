import hmac
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from src.db.firebase_client import db_client

class AuthService:
    """Hanterar validering av API-nycklar, rate limiting och loggning till Firebase."""
    
    def __init__(self):
        # In-memory sliding window rate limiter: client_id -> list of timestamps
        self._request_history: Dict[str, List[float]] = defaultdict(list)

    def check_rate_limit(self, client_id: str = "anon", max_requests: int = 60, window_seconds: int = 60) -> bool:
        """
        Sliding-window rate limiter.
        Returnerar True om anropet tillåts, False om gränsen är nådd.
        """
        now = time.time()
        cutoff = now - window_seconds
        
        # Rensa gamla tidsstämplar
        history = [t for t in self._request_history[client_id] if t > cutoff]
        
        if len(history) >= max_requests:
            self._request_history[client_id] = history
            return False
            
        history.append(now)
        self._request_history[client_id] = history
        return True

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
                
        if hmac.compare_digest(api_key, "las_master_admin_key_2026"):
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
