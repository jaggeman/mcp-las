import hmac
import hashlib
import secrets
import logging
from threading import RLock
from src.config import settings
import time
from collections import defaultdict, OrderedDict
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from src.db.firebase_client import db_client

class AuthService:
    """Hanterar validering av API-nycklar, rate limiting och loggning till Firebase."""
    
    def __init__(self):
        # In-memory sliding window rate limiter: client_id -> list of timestamps
        self._request_history: Dict[str, List[float]] = defaultdict(list)
        self._deadlines = {}
        self._lock = RLock()
        self._next_cleanup = 0
        self._key_cache = OrderedDict()
        self._key_cache_ttl = 30
        self._key_cache_max = 1000

    def check_rate_limit(self, client_id: str = "anon", max_requests: int = 60, window_seconds: int = 60) -> bool:
        """
        Sliding-window rate limiter.
        Returnerar True om anropet tillåts, False om gränsen är nådd.
        """
        if db_client.db is not None:
            if client_id == 'mcp:http-preauth':
                # Fixed partitions preserve the aggregate upper bound without
                # serializing every request on a single Firestore document.
                # A full randomly selected partition fails closed; no borrowing.
                partitions = min(16, max_requests)
                shard = secrets.randbelow(partitions)
                capacity = max_requests // partitions + (shard < max_requests % partitions)
                return self._distributed_limit(f'{client_id}:v2:{shard}', capacity, window_seconds)
            return self._distributed_limit(client_id, max_requests, window_seconds)
        now = time.monotonic()
        with self._lock:
            if now >= self._next_cleanup:
                for key, deadline in list(self._deadlines.items()):
                    if deadline <= now:
                        self._request_history.pop(key, None)
                        self._deadlines.pop(key, None)
                self._next_cleanup = now + 60
            if client_id not in self._request_history and len(self._request_history) >= 10000:
                return False
            history = [t for t in self._request_history.get(client_id, []) if t > now - window_seconds]
            if len(history) >= max_requests:
                return False
            history.append(now)
            self._request_history[client_id] = history
            self._deadlines[client_id] = now + window_seconds
            return True

    @staticmethod
    def _distributed_limit(client_id, max_requests, window_seconds):
        from google.cloud import firestore
        identifier = hashlib.sha256(client_id.encode('utf-8')).hexdigest()
        ref = db_client.db.collection('mcp_rate_limits').document(identifier)

        @firestore.transactional
        def update(transaction):
            now = time.time()
            snapshot = ref.get(transaction=transaction)
            data = snapshot.to_dict() if snapshot.exists else {}
            history = [t for t in data.get('timestamps', []) if t > now - window_seconds]
            if len(history) >= max_requests:
                return False
            transaction.set(ref, {
                'timestamps': history + [now],
                'expires_at': datetime.now(timezone.utc) + timedelta(seconds=window_seconds),
            })
            return True
        try:
            return update(db_client.db.transaction())
        except Exception:
            logging.error('Rate limit storage unavailable; request denied')
            return False

    def validate_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        if not isinstance(api_key, str) or not api_key or len(api_key) > 512 or '/' in api_key:
            return None
            
        master_key = settings.MASTER_ADMIN_KEY
        if master_key and hmac.compare_digest(api_key.encode('utf-8'), master_key.encode('utf-8')):
            return {"name": "Master Admin", "is_active": True}

        cache_key = hashlib.sha256(api_key.encode('utf-8')).hexdigest()
        now = time.monotonic()
        with self._lock:
            cached = self._key_cache.get(cache_key)
            if cached and cached[0] > now:
                self._key_cache.move_to_end(cache_key)
                return dict(cached[1])
            if cached:
                self._key_cache.pop(cache_key, None)

        if db_client.db:
            try:
                doc = db_client.db.collection("api_keys").document(cache_key).get()
                if doc.exists:
                    data = doc.to_dict()
                    stored_digest = data.get("key_digest")
                    digest_matches = isinstance(stored_digest, str) and hmac.compare_digest(
                        cache_key.encode("ascii"), stored_digest.encode("ascii")
                    )
                    if digest_matches and data.get("is_active") is True:
                        with self._lock:
                            self._key_cache[cache_key] = (now + self._key_cache_ttl, dict(data))
                            self._key_cache.move_to_end(cache_key)
                            while len(self._key_cache) > self._key_cache_max:
                                self._key_cache.popitem(last=False)
                        return data
            except Exception:
                logging.error('API key lookup failed')
                
        return None

    @staticmethod
    def log_access(api_key: str, key_info: Optional[Dict[str, Any]], tool_name: str, params: Dict[str, Any], duration_ms: float, status: str = "success"):
        """Sparar en logg i Firestore i samlingen 'access_logs'."""
        if not db_client.db:
            return
            
        try:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
                "tool_called": tool_name,
                "duration_ms": round(duration_ms, 2),
                "status": status
            }
            db_client.db.collection("access_logs").add(log_entry)
        except Exception as e:
            print(f"Log error: {e}")

auth_service = AuthService()
