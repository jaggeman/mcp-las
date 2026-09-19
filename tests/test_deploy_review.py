import asyncio
import time
from threading import Event
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from src import server
from src.mcp_tools import tools
from src.db.firebase_client import db_client
from src.services import usage_logging


def test_no_de_coverage_uses_database(monkeypatch):
    monkeypatch.setattr(db_client, 'count_sections_by_jurisdiction', lambda: {})
    coverage = tools.get_legal_coverage()['jurisdictions']
    for code in ('NO', 'DE'):
        assert coverage[code]['statutes'] is False
        assert coverage[code]['section_count'] == 0


def test_empty_law_is_rejected(monkeypatch):
    read = Mock(return_value=[])
    monkeypatch.setattr(db_client, '_get_statute_items', read)
    with pytest.raises(ValueError): db_client.get_statute_section(' ', '1')
    read.assert_not_called()


def test_failed_refresh_never_pretends_database_is_empty(monkeypatch):
    monkeypatch.setattr(db_client, '_cached_statute_sections', [{'active': True}])
    monkeypatch.setattr(db_client, '_statute_cache_at', time.monotonic() - 61, raising=False)
    def fail(): raise RuntimeError('PRIVATE')
    monkeypatch.setattr(db_client, 'db', SimpleNamespace(collection=lambda _: SimpleNamespace(stream=fail)))
    with pytest.raises(RuntimeError, match='Statute database unavailable'):
        db_client._get_statute_items()
    assert db_client._cached_statute_sections == [{'active': True}]


def test_concurrent_refresh_reads_once(monkeypatch):
    calls = []
    def stream():
        calls.append(1)
        time.sleep(.03)
        return [SimpleNamespace(to_dict=lambda: {'active': True})]
    monkeypatch.setattr(db_client, '_cached_statute_sections', None)
    monkeypatch.setattr(db_client, 'db', SimpleNamespace(collection=lambda _: SimpleNamespace(stream=stream, document=lambda _: SimpleNamespace(get=lambda: SimpleNamespace(exists=False)))))
    with ThreadPoolExecutor(4) as pool: list(pool.map(lambda _: db_client._get_statute_items(), range(4)))
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_rest_does_not_block_event_loop(monkeypatch):
    monkeypatch.setattr(server.auth_service, 'validate_key', lambda _: {'is_active': True})
    monkeypatch.setattr(server, '_check_rate_limit', lambda _: None)
    monkeypatch.setattr(usage_logging, 'emit', lambda **kw: None)
    done = []
    async def ticker():
        await asyncio.sleep(.01)
        done.append(True)
    def slow():
        time.sleep(.08)
        assert done
        return {}
    monkeypatch.setitem(server.DIRECT_TOOLS_MAP, 'get_legal_coverage', slow)
    async def body(): return {}
    request = SimpleNamespace(method='POST', headers={'X-API-Key': 'test'}, path_params={'tool_name': 'get_legal_coverage'}, json=body)
    _, response = await asyncio.gather(ticker(), server.execute_tool_direct_rest(request))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_raw_exceptions_never_logged(monkeypatch, caplog):
    monkeypatch.setattr(server.auth_service, 'validate_key', lambda _: {'is_active': True})
    monkeypatch.setattr(server, '_check_rate_limit', lambda _: None)
    monkeypatch.setattr(usage_logging, 'emit', lambda **kw: None)
    def fail(): raise ValueError('PRIVATE')
    monkeypatch.setitem(server.DIRECT_TOOLS_MAP, 'get_legal_coverage', fail)
    async def body(): return {}
    response = await server.execute_tool_direct_rest(SimpleNamespace(method='POST', headers={'X-API-Key':'test'}, path_params={'tool_name':'get_legal_coverage'}, json=body))
    assert response.status_code == 400
    assert 'PRIVATE' not in caplog.text


def test_slow_usage_storage_does_not_delay_tool(monkeypatch):
    release, started = Event(), Event()
    def write(event):
        started.set()
        release.wait(timeout=2)
    db = SimpleNamespace(collection=lambda _: SimpleNamespace(document=lambda _: SimpleNamespace(set=write)))
    monkeypatch.setattr(usage_logging.db_client, 'db', db)
    monkeypatch.setattr(usage_logging.settings, 'STORE_USAGE_IN_FIRESTORE', True)
    @usage_logging.tracked_tool
    def sample(): return {'ok': True}
    try:
        before = time.perf_counter()
        assert sample() == {'ok': True}
        assert time.perf_counter() - before < .5
        assert started.wait(timeout=1)
    finally:
        release.set()


@pytest.mark.asyncio
async def test_rest_rejects_non_object_json(monkeypatch):
    monkeypatch.setattr(usage_logging, 'emit', lambda **kw: None)
    async def body(): return ['bad']
    response = await server.execute_tool_direct_rest(SimpleNamespace(method='POST', headers={}, path_params={'tool_name':'get_legal_coverage'}, json=body))
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_mcp_errors_never_expose_details(monkeypatch, caplog):
    from fastmcp import Client
    monkeypatch.setattr(server, '_check_rate_limit', lambda _: None)
    monkeypatch.setattr(usage_logging, 'emit', lambda **kw: None)
    def fail(): raise RuntimeError('SYNTHETIC_PRIVATE_DETAIL')
    monkeypatch.setattr(server, '_get_legal_coverage', fail)
    async with Client(server.mcp) as client:
        result = await client.call_tool('get_legal_coverage', {}, raise_on_error=False)
    assert result.is_error
    assert 'SYNTHETIC_PRIVATE_DETAIL' not in str(result.content)
    assert 'SYNTHETIC_PRIVATE_DETAIL' not in caplog.text
