"""Reject oversized bodies before JSON/MCP parsing, including chunked bodies."""
import asyncio
import json
from starlette.responses import JSONResponse


class RequestSizeLimit:
    def __init__(self, app, max_bytes=1024 * 1024):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        async def observed_send(message):
            if message['type'] == 'http.response.start' and message['status'] >= 400:
                path = scope.get('path', '')
                route = 'mcp' if path in ('/mcp', '/sse') else 'api' if path.startswith('/api/') else 'other'
                try:
                    print(json.dumps({'event': 'las_http_rejected', 'route': route,
                                      'status_code': message['status']}), flush=True)
                except Exception:
                    pass
            await send(message)
        return await self._dispatch(scope, receive, observed_send)

    async def _dispatch(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
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
