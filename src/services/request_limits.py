"""Reject oversized bodies before JSON/MCP parsing, including chunked bodies."""
import asyncio
import json
from starlette.responses import JSONResponse, Response
from src.services.request_context import reset_api_key, set_api_key


class RequestSizeLimit:
    allowed_origins = {'https://las.novro.se', 'https://mcp.novro.se'}
    def __init__(self, app, max_bytes=1024 * 1024):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get('headers', [])) if scope.get('type') == 'http' else {}
        raw_key = headers.get(b'x-api-key')
        api_key = raw_key.decode('utf-8', 'replace') if raw_key else None
        token = set_api_key(api_key)
        async def observed_send(message):
            if message['type'] == 'http.response.start':
                response_headers = [(k, v) for k, v in message.get('headers', [])
                                    if not k.lower().startswith(b'access-control-')]
                origin = headers.get(b'origin', b'').decode('latin-1')
                if origin in self.allowed_origins:
                    response_headers.extend([
                        (b'access-control-allow-origin', origin.encode('ascii')),
                        (b'access-control-allow-methods', b'GET, POST, DELETE, OPTIONS'),
                        (b'access-control-allow-headers', b'Content-Type, X-API-Key, MCP-Protocol-Version, MCP-Session-Id'),
                        (b'vary', b'Origin'),
                    ])
                response_headers.append((b'x-content-type-options', b'nosniff'))
                message = {**message, 'headers': response_headers}
            if message['type'] == 'http.response.start' and message['status'] >= 400:
                path = scope.get('path', '')
                route = 'mcp' if path in ('/mcp', '/sse') else 'api' if path.startswith('/api/') else 'other'
                try:
                    print(json.dumps({'event': 'las_http_rejected', 'route': route,
                                      'status_code': message['status']}), flush=True)
                except Exception:
                    pass
            await send(message)
        try:
            return await self._dispatch(scope, receive, observed_send)
        finally:
            reset_api_key(token)

    async def _dispatch(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        origin = dict(scope.get('headers', [])).get(b'origin', b'').decode('latin-1')
        if origin and origin not in self.allowed_origins:
            return await JSONResponse({'error': 'Origin not allowed'}, 403)(scope, receive, send)
        # Preflight must never reach the MCP stateful session allocator.
        if scope['method'] == 'OPTIONS':
            return await Response(status_code=204)(scope, receive, send)
        if scope['method'] != 'OPTIONS' and (scope['path'].startswith('/api/') or scope['path'] in ('/mcp', '/sse')):
            from src.db.auth_service import auth_service
            allowed = await asyncio.to_thread(auth_service.check_rate_limit,
                                             'mcp:http-preauth', 600, 60)
            if not allowed:
                return await JSONResponse({'error': 'Request limit exceeded'}, 429)(scope, receive, send)
        if scope['method'] not in ('POST', 'PUT', 'PATCH'):
            return await self.app(scope, receive, send)
        limit = min(self.max_bytes, 16 * 1024) if scope['path'] == '/api/request-key' else self.max_bytes
        headers = dict(scope.get('headers', []))
        try:
            declared = int(headers.get(b'content-length', b'0'))
        except ValueError:
            return await JSONResponse({'error': 'Invalid Content-Length'}, 400)(scope, receive, send)
        if declared < 0 or declared > limit:
            return await JSONResponse({'error': 'Request body too large'}, 413)(scope, receive, send)
        body = bytearray()
        async def read():
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return False
                body.extend(message.get('body', b''))
                if len(body) > limit:
                    return False
                if not message.get('more_body', False):
                    return True
        try:
            accepted = await asyncio.wait_for(read(), timeout=10)
        except asyncio.TimeoutError:
            return await JSONResponse({'error': 'Request body timeout'}, 408)(scope, receive, send)
        if not accepted:
            return await JSONResponse({'error': 'Request body too large'}, 413)(scope, receive, send)
        delivered = False
        async def replay():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
        await self.app(scope, replay, send)
