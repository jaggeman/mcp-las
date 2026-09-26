import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from src import server
from src.db.auth_service import AuthService


@pytest.mark.parametrize('metadata', [{}, {'is_active': 'false'}, {'is_active': 1}])
def test_activation_is_explicit(monkeypatch, metadata):
    doc = SimpleNamespace(id="invalid", exists=True, to_dict=lambda: metadata)
    monkeypatch.setattr(server.db_client, 'db', SimpleNamespace(collection=lambda _: SimpleNamespace(document=lambda _: SimpleNamespace(get=lambda: doc))))
    monkeypatch.setattr(server.settings, 'MASTER_ADMIN_KEY', None)
    assert AuthService().validate_key('synthetic') is None


def test_logs_do_not_store_inputs_or_key_parts(monkeypatch):
    rows = []
    monkeypatch.setattr(server.db_client, 'db', SimpleNamespace(collection=lambda _: SimpleNamespace(add=rows.append)))
    AuthService.log_access('secret-key', {'name': 'PERSON'}, 'lookup_statute', {'query': 'PRIVATE'}, 10)
    assert 'secret-key' not in str(rows)
    assert 'PERSON' not in str(rows) and 'PRIVATE' not in str(rows)
    assert 'expires_at' in rows[0]


@pytest.mark.asyncio
async def test_url_key_is_rejected(monkeypatch):
    validate = Mock(return_value={'is_active': True})
    monkeypatch.setattr(server.auth_service, 'validate_key', validate)
    response = await server.list_available_tools_rest(SimpleNamespace(method='GET', headers={}, query_params={'api_key': 'secret'}))
    assert response.status_code == 401
    validate.assert_not_called()


@pytest.mark.asyncio
async def test_forwarded_header_cannot_rotate_quota(monkeypatch):
    limiter = AuthService()
    monkeypatch.setattr(server.db_client, 'db', None)
    monkeypatch.setattr(server.auth_service, 'check_rate_limit', limiter.check_rate_limit)
    monkeypatch.setattr(server.notification_service, 'send_key_request_notification', lambda _: True)
    async def body(): return {'name': 'Test', 'email': 'test@example.invalid'}
    codes = []
    for n in range(6):
        request = SimpleNamespace(method='POST', headers={'x-forwarded-for': f'192.0.2.{n}'}, client=SimpleNamespace(host='192.0.2.100'), json=body)
        codes.append((await server.handle_key_request(request)).status_code)
    assert codes[-1] == 429


def test_limiter_storage_is_bounded(monkeypatch):
    monkeypatch.setattr(server.db_client, 'db', None)
    limiter = AuthService()
    for n in range(11000): limiter.check_rate_limit(str(n))
    assert len(limiter._request_history) <= 10000


@pytest.mark.asyncio
async def test_oversized_chunked_body_never_reaches_app():
    from src.services.request_limits import RequestSizeLimit
    called = []
    async def app(*args): called.append(True)
    chunks = iter([{'type': 'http.request', 'body': b'123', 'more_body': True}, {'type': 'http.request', 'body': b'456', 'more_body': False}])
    async def receive(): return next(chunks)
    messages = []
    async def send(message): messages.append(message)
    await RequestSizeLimit(app, max_bytes=5)({'type': 'http', 'method': 'POST', 'headers': [], 'path': '/mcp'}, receive, send)
    assert not called and messages[0]['status'] == 413


def test_shared_quota_and_storage_failure(monkeypatch):
    from google.cloud import firestore
    state = {}
    class Transaction:
        def set(self, ref, value): state.update(value)
    ref = SimpleNamespace(get=lambda **kw: SimpleNamespace(exists=bool(state), to_dict=lambda: dict(state)))
    db = SimpleNamespace(collection=lambda name: SimpleNamespace(document=lambda _: ref), transaction=Transaction)
    monkeypatch.setattr(server.db_client, 'db', db)
    monkeypatch.setattr(firestore, 'transactional', lambda fn: fn)
    first, second = AuthService(), AuthService()
    assert first.check_rate_limit('same-client', 2, 60)
    assert second.check_rate_limit('same-client', 2, 60)
    assert not first.check_rate_limit('same-client', 2, 60)
    assert 'expires_at' in state
    db.transaction = Mock(side_effect=RuntimeError('offline'))
    assert not second.check_rate_limit('other-client', 2, 60)


@pytest.mark.asyncio
async def test_small_body_replayed_intact(monkeypatch):
    from src.services.request_limits import RequestSizeLimit
    monkeypatch.setattr(server.auth_service, 'check_rate_limit', lambda *a: True)
    seen = []
    async def app(scope, receive, send): seen.append(await receive())
    async def receive(): return {'type': 'http.request', 'body': b'{}', 'more_body': False}
    async def send(message): pass
    await RequestSizeLimit(app)({'type': 'http', 'method': 'POST', 'headers': [], 'path': '/mcp'}, receive, send)
    assert seen[0]['body'] == b'{}'


@pytest.mark.asyncio
async def test_pre_auth_quota_applies_before_parsing(monkeypatch):
    from src.services.request_limits import RequestSizeLimit
    monkeypatch.setattr(server.auth_service, 'check_rate_limit', lambda *a: False)
    async def forbidden(*a): pytest.fail('Must not parse or dispatch')
    sent = []
    async def send(message): sent.append(message)
    await RequestSizeLimit(forbidden)({'type': 'http', 'method': 'POST', 'headers': [], 'path': '/mcp'}, forbidden, send)
    assert sent[0]['status'] == 429
