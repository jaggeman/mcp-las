import json
from types import SimpleNamespace

import pytest
from src import server
from src.services import usage_logging as usage


@pytest.fixture
def events(monkeypatch):
    rows = []
    monkeypatch.setattr(usage, 'emit', lambda **event: rows.append(event))
    monkeypatch.setattr(server, '_check_rate_limit', lambda _: None)
    return rows


def test_mcp_logs_once_with_country_without_arguments(events, monkeypatch):
    monkeypatch.setattr(server, '_lookup_statute', lambda **kw: {'content': 'PRIVATE'})
    fn = getattr(server.lookup_statute, 'fn', server.lookup_statute)
    fn(law='PRIVATE', section='1', jurisdiction='DK', api_key='SECRET')
    assert len(events) == 1
    assert events[0]['jurisdiction'] == 'DK'
    assert events[0]['transport'] == 'mcp'
    assert 'PRIVATE' not in str(events) and 'SECRET' not in str(events)


def test_mcp_denials_and_exceptions(events, monkeypatch):
    fn = getattr(server.get_legal_coverage, 'fn', server.get_legal_coverage)
    monkeypatch.setattr(server, '_check_rate_limit', lambda _: {'status': 'unauthorized', 'error': 'SECRET'})
    fn()
    assert events[-1]['status'] == 'unauthorized'
    monkeypatch.setattr(server, '_check_rate_limit', lambda _: None)
    def fail(): raise RuntimeError('SECRET')
    monkeypatch.setattr(server, '_get_legal_coverage', fail)
    with pytest.raises(RuntimeError): fn()
    assert events[-1]['status'] == 'error'
    assert 'SECRET' not in str(events)


@pytest.mark.asyncio
async def test_rest_unauthorized_counted_once(events):
    async def body(): return {}
    response = await server.execute_tool_direct_rest(SimpleNamespace(method='POST', path_params={'tool_name': 'lookup_statute'}, headers={}, json=body))
    assert response.status_code == 401
    assert len(events) == 1 and events[0]['status'] == 'unauthorized'


def test_emission_without_database_and_failed_database(monkeypatch, capsys):
    monkeypatch.setattr(usage.db_client, 'db', None)
    usage.emit(tool='lookup_statute', transport='mcp', jurisdiction='SE', status='success', duration_ms=4)
    event = json.loads(capsys.readouterr().out)
    assert event['event'] == 'las_tool_usage'
    assert event['duration_ms'] == 4
    def fail(*a): raise RuntimeError('SECRET')
    monkeypatch.setattr(usage.db_client, 'db', SimpleNamespace(collection=fail))
    usage.emit(tool='lookup_statute', transport='mcp', jurisdiction='SE', status='success', duration_ms=4)
    assert 'SECRET' not in capsys.readouterr().out


def test_legacy_filter_and_unknown_country():
    assert usage.country('search_labor_law', {'filters': {'jurisdiction': 'NO'}}) == 'NO'
    assert usage.country('search_labor_law', {'jurisdiction': 'SE', 'filters': {'jurisdiction': 'NO'}}) == 'SE'
    assert usage.country('lookup_statute', {'jurisdiction': 'PRIVATE'}) == 'unknown'


def test_usage_summary():
    from scripts.usage_report import summarize
    report = summarize([
        {'event': 'las_tool_usage', 'timestamp': '2026-09-19T01:00:00+00:00', 'tool_called': 'lookup_statute', 'transport': 'mcp', 'jurisdiction': 'DK', 'status': 'success', 'duration_ms': 10},
        {'event': 'las_tool_usage', 'timestamp': '2026-09-19T02:00:00+00:00', 'tool_called': 'lookup_statute', 'transport': 'rest', 'jurisdiction': 'SE', 'status': 'unauthorized', 'duration_ms': 30},
        {'tool_called': 'legacy'},
    ])
    assert report['total_calls'] == 2
    assert report['by_tool']['lookup_statute'] == 2
    assert report['by_day']['2026-09-19'] == 2
    assert report['latency_ms']['average'] == 20
    assert report['legacy_rows_excluded'] == 1
