import ssl
from unittest.mock import Mock

import pytest
from starlette.testclient import TestClient


def test_options_never_allocates_mcp_session(monkeypatch):
    from src import server
    from starlette.middleware import Middleware
    from src.services.request_limits import RequestSizeLimit
    monkeypatch.setattr(server.auth_service, 'check_rate_limit', lambda *a, **k: True)
    app = server.mcp.http_app(middleware=[Middleware(RequestSizeLimit)])
    with TestClient(app) as client:
        for _ in range(3):
            response = client.options('/mcp')
            assert 'mcp-session-id' not in response.headers
        assert not app.routes[0].app.session_manager._server_instances


def test_foreign_origin_rejected_before_database(monkeypatch):
    from src import server
    from starlette.middleware import Middleware
    from src.services.request_limits import RequestSizeLimit
    quota = Mock(side_effect=AssertionError('database must not be called'))
    monkeypatch.setattr(server.auth_service, 'check_rate_limit', quota)
    app = server.mcp.http_app(middleware=[Middleware(RequestSizeLimit)])
    with TestClient(app) as client:
        response = client.post('/api/request-key', headers={'Origin': 'https://evil.example'}, json={})
        assert response.status_code == 403
        quota.assert_not_called()


@pytest.mark.parametrize('port', [465, 587])
def test_smtp_verifies_peer(monkeypatch, port):
    from src.services import notification_service as module
    contexts = []
    class SMTP:
        def __init__(self, *a, **kw):
            if 'context' in kw: contexts.append(kw['context'])
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def starttls(self, **kw): contexts.append(kw.get('context'))
        def login(self, *a): pass
        def sendmail(self, *a): pass
    monkeypatch.setattr(module.smtplib, 'SMTP', SMTP)
    monkeypatch.setattr(module.smtplib, 'SMTP_SSL', SMTP)
    service = module.NotificationService()
    service.smtp_user, service.smtp_pass, service.smtp_port = 'test', 'test', port
    assert service.send_key_request_notification({})
    assert len(contexts) == 1
    assert contexts[0].verify_mode == ssl.CERT_REQUIRED
    assert contexts[0].check_hostname


@pytest.mark.parametrize('identifier', ['../foo', 'x?y=z', 'x' * 129])
def test_bad_document_id_never_fetches(monkeypatch, identifier):
    from src.services.riksdagen_api_service import RiksdagenAPIService
    fetch = Mock(side_effect=AssertionError('network must not be called'))
    monkeypatch.setattr('src.services.riksdagen_api_service.httpx.get', fetch)
    with pytest.raises(ValueError):
        RiksdagenAPIService().get_document_details(identifier)
    fetch.assert_not_called()


@pytest.mark.parametrize('kwargs', [{'query': 'x'*2001}, {'query': 'x', 'page': 0}, {'query': 'x', 'limit': 100}])
def test_invalid_search_never_fetches(monkeypatch, kwargs):
    from src.services.riksdagen_api_service import RiksdagenAPIService
    fetch = Mock(side_effect=AssertionError('network must not be called'))
    monkeypatch.setattr('src.services.riksdagen_api_service.httpx.get', fetch)
    with pytest.raises(ValueError):
        RiksdagenAPIService().search_documents(**kwargs)
    fetch.assert_not_called()
