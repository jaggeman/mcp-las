import pytest
from src.db.auth_service import auth_service

def test_auth_validate_master_key():
    valid = auth_service.validate_key('las_master_admin_key_2026')
    assert valid is not None
    assert valid['name'] == 'Master Admin'

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
