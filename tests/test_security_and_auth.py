import pytest
from src.db.auth_service import auth_service
from src.config import settings

LEAKED_KEY = 'las_master_admin_key_2026'


def test_leaked_master_key_no_longer_works(monkeypatch):
    """Den hardkodade nyckeln lag i ett publikt repo. Den far aldrig ge atkomst igen."""
    monkeypatch.setattr(settings, 'MASTER_ADMIN_KEY', None)
    assert auth_service.validate_key(LEAKED_KEY) is None


def test_master_path_is_closed_when_unconfigured(monkeypatch):
    """Utan konfigurerad nyckel ska master-vagen vara helt stangd - fail closed."""
    monkeypatch.setattr(settings, 'MASTER_ADMIN_KEY', None)
    assert auth_service.validate_key('nagon_nyckel_alls') is None


def test_master_key_accepted_when_configured(monkeypatch):
    monkeypatch.setattr(settings, 'MASTER_ADMIN_KEY', 'en-roterad-hemlighet')
    valid = auth_service.validate_key('en-roterad-hemlighet')
    assert valid is not None
    assert valid['name'] == 'Master Admin'
    # En annan nyckel far inte slinka igenom pa samma vag
    assert auth_service.validate_key('en-roterad-hemlighe') is None

def test_auth_validate_invalid_key():
    invalid = auth_service.validate_key('totally_invalid_key_xyz')
    assert invalid is None

def test_rate_limiter_sliding_window():
    client_id = 'test_client_rate_limit'
    # Limit to 3 requests per 10 seconds
    for _ in range(3):
        assert auth_service.check_rate_limit(client_id, max_requests=3, window_seconds=10) is True
    # 4th request must be blocked
    assert auth_service.check_rate_limit(client_id, max_requests=3, window_seconds=10) is False
