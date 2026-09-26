from starlette.middleware import Middleware
from starlette.testclient import TestClient


def test_stateless_initialize_and_tool_call(monkeypatch):
    from src import server
    from src.services.request_limits import RequestSizeLimit
    monkeypatch.setattr(server.auth_service, 'check_rate_limit', lambda *a, **k: True)
    monkeypatch.setattr(server, '_get_legal_coverage', lambda: {'test': True})
    app = server.mcp.http_app(stateless_http=True, middleware=[Middleware(RequestSizeLimit)])
    with TestClient(app) as client:
        headers = {'Accept': 'application/json, text/event-stream'}
        response = client.post('/mcp', headers=headers, json={
            'jsonrpc':'2.0', 'id':1, 'method':'initialize',
            'params':{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'test','version':'1'}}})
        assert response.status_code == 200
        assert 'mcp-session-id' not in response.headers
        response = client.post('/mcp', headers=headers, json={
            'jsonrpc':'2.0','id':2,'method':'tools/call',
            'params':{'name':'get_legal_coverage','arguments':{}}})
        assert response.status_code == 200
        assert '"test":true' in response.text
        assert not app.routes[0].app.session_manager._server_instances
