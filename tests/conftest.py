import pytest

from src.config import settings


@pytest.fixture(autouse=True)
def api_key_pepper_for_tests(monkeypatch):
    """Keep production fail-closed while giving tests a non-secret pepper."""
    monkeypatch.setattr(settings, "API_KEY_PEPPER", "test-only-pepper-" * 4)
