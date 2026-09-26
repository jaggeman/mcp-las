from pathlib import Path
from unittest.mock import Mock

from src.db.auth_service import AuthService
from src.db.firebase_client import db_client


def test_preauth_is_distributed_without_increasing_total_quota(monkeypatch):
    monkeypatch.setattr(db_client, 'db', object())
    calls = []
    monkeypatch.setattr(AuthService, '_distributed_limit', staticmethod(lambda *a: calls.append(a) or True))
    for shard in range(16):
        monkeypatch.setattr('src.db.auth_service.secrets.randbelow', lambda n, shard=shard: shard)
        assert AuthService().check_rate_limit('mcp:http-preauth', 600, 60)
    assert len({call[0] for call in calls}) == 16
    assert sum(call[1] for call in calls) == 600
    assert all(call[2] == 60 for call in calls)


def test_regular_client_keeps_its_quota(monkeypatch):
    monkeypatch.setattr(db_client, 'db', object())
    limit = Mock(return_value=False)
    monkeypatch.setattr(AuthService, '_distributed_limit', limit)
    assert not AuthService().check_rate_limit('client', 300, 60)
    limit.assert_called_once_with('client', 300, 60)


def test_weekly_sync_uses_oidc_and_includes_no_de():
    workflow = Path('.github/workflows/sync-sources.yml').read_text(encoding='utf-8')
    assert 'credentials_json:' not in workflow
    assert 'id-token: write' in workflow
    assert 'GCP_SYNC_WORKLOAD_IDENTITY_PROVIDER' in workflow
    assert 'gcloud run jobs execute mcp-las-source-sync' in workflow
    assert '--wait' in workflow
def test_swedish_sync_runs_on_runner_and_foreign_sync_in_frankfurt():
    from pathlib import Path
    workflow = Path('.github/workflows/sync-sources.yml').read_text(encoding='utf-8')
    ci = Path('.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert 'python scripts/sync_sources.py --swedish' in workflow
    assert '--args="scripts/sync_sources.py,--danish,--finnish,--norwegian,--german,--spanish,--dutch,--british"' in ci
