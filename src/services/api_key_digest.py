"""Deterministic, peppered identifiers for bearer API keys."""

import hashlib
import hmac

from src.config import settings


def _pepper() -> bytes:
    value = settings.API_KEY_PEPPER
    if not isinstance(value, str) or len(value) < 32:
        raise RuntimeError("API_KEY_PEPPER must contain at least 32 characters")
    return value.encode("utf-8")


def key_id(api_key: str) -> str:
    """Current identifier: HMAC the full, high-entropy bearer token."""
    return hmac.new(_pepper(), api_key.encode("utf-8"), hashlib.sha256).hexdigest()


def migrated_v2_key_id(api_key: str) -> str:
    """Identifier for v2 records migrated without access to the bearer token."""
    # Compatibility only: v2 already stored this identifier. The result is
    # immediately protected by a server-secret HMAC and v4 keys skip this step.
    old_identifier = hashlib.sha256(api_key.encode("utf-8")).hexdigest()  # lgtm[py/weak-sensitive-data-hashing]
    return hmac.new(_pepper(), old_identifier.encode("ascii"), hashlib.sha256).hexdigest()


def migrate_v2_identifier(old_identifier: str) -> str:
    """Convert an existing v2 SHA-256 identifier to its peppered v3 form."""
    return hmac.new(_pepper(), old_identifier.encode("ascii"), hashlib.sha256).hexdigest()


def rate_limit_id(client_id: str) -> str:
    """Pseudonymise a rate-limit subject with the same server-only pepper."""
    return hmac.new(_pepper(), client_id.encode("utf-8"), hashlib.sha256).hexdigest()
