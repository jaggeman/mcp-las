"""Allowlisted usage metadata only: never persist tool input or output."""
import inspect
import json
import time
import uuid
from queue import Queue, Full
from threading import Thread
from datetime import datetime, timedelta, timezone
from functools import wraps

from src.db.firebase_client import db_client
from src.config import settings
from src.jurisdictions import JURISDICTION_CODES

_pending = Queue(maxsize=1000)


def _store_events():
    while True:
        db, event = _pending.get()
        try:
            db.collection('access_logs').document(event['event_id']).set(event)
        except Exception:
            print(json.dumps({'event': 'las_usage_storage_error', 'severity': 'WARNING'}), flush=True)
        finally:
            _pending.task_done()


Thread(target=_store_events, daemon=True, name='usage-writer').start()


def country(tool, arguments):
    if tool == 'get_legal_coverage':
        return 'all'
    value = arguments.get('jurisdiction')
    if value is None and tool == 'search_labor_law':
        filters = arguments.get('filters')
        value = filters.get('jurisdiction') if isinstance(filters, dict) else None
    if value is None:
        return 'SE'
    return value.upper() if isinstance(value, str) and value.upper() in JURISDICTION_CODES else 'unknown'


def outcome(result):
    rows = result if isinstance(result, list) else [result]
    for row in rows:
        if isinstance(row, dict):
            if row.get('status') in ('unauthorized', 'rate_limited'):
                return row['status']
            if row.get('error') or row.get('success') is False:
                return 'error'
    return 'success'


def emit(*, tool, transport, jurisdiction, status, duration_ms):
    now = datetime.now(timezone.utc)
    event = {
        'event': 'las_tool_usage', 'schema_version': 1,
        'event_id': uuid.uuid4().hex, 'timestamp': now.isoformat(),
        'tool_called': tool, 'transport': transport,
        'jurisdiction': jurisdiction, 'status': status,
        'duration_ms': round(max(0, duration_ms), 2),
    }
    # Cloud Run ingests JSON stdout as structured jsonPayload. It also works
    # without Firestore; no external logging credentials or configuration.
    print(json.dumps(event), flush=True)
    if settings.STORE_USAGE_IN_FIRESTORE and db_client.db is not None:
        try:
            _pending.put_nowait((db_client.db, {
                **event, 'expires_at': now + timedelta(days=30),
            }))
        except Full:
            print(json.dumps({'event': 'las_usage_queue_full', 'severity': 'WARNING'}), flush=True)


def tracked_tool(fn):
    signature = inspect.signature(fn)
    @wraps(fn)
    def wrapper(*args, **kwargs):
        started = time.perf_counter()
        status, jurisdiction = 'error', 'unknown'
        try:
            arguments = signature.bind(*args, **kwargs).arguments
            jurisdiction = country(fn.__name__, arguments)
            result = fn(*args, **kwargs)
            status = outcome(result)
            return result
        except Exception:
            # FastMCP logs tool exceptions as well as returning them. Suppress
            # the original chain so neither path receives raw user/source data.
            raise RuntimeError('Tool execution failed') from None
        finally:
            safe_emit(tool=fn.__name__, transport='mcp', jurisdiction=jurisdiction,
                 status=status, duration_ms=(time.perf_counter() - started) * 1000)
    return wrapper


def tracked_rest(fn):
    @wraps(fn)
    async def wrapper(request):
        if request.method == 'OPTIONS':
            return await fn(request)
        from src.server import DIRECT_TOOLS_MAP
        requested = request.path_params.get('tool_name', '')
        tool = requested if requested in DIRECT_TOOLS_MAP else 'unknown'
        started = time.perf_counter()
        status, jurisdiction = 'error', 'unknown'
        try:
            # Starlette caches parsed JSON; these arguments are never logged.
            try:
                args = await request.json()
                if isinstance(args, dict) and tool != 'unknown':
                    jurisdiction = country(tool, args)
            except Exception:
                pass
            response = await fn(request)
            status = {400: 'bad_request', 401: 'unauthorized', 403: 'unauthorized',
                      404: 'not_found', 429: 'rate_limited'}.get(response.status_code, 'error')
            if response.status_code < 400:
                payload = json.loads(response.body)
                status = outcome(payload.get('result', payload))
            return response
        finally:
            safe_emit(tool=tool, transport='rest', jurisdiction=jurisdiction,
                 status=status, duration_ms=(time.perf_counter() - started) * 1000)
    return wrapper


def safe_emit(**event):
    try:
        emit(**event)
    except Exception:
        # Observability must never replace a tool result or its exception.
        pass
