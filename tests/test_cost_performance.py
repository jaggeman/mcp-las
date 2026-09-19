from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.config import settings
from src.db.auth_service import AuthService
from src.db.firebase_client import FirebaseLaborLawDB
from src.services import usage_logging


def test_valid_key_cache_avoids_repeated_firestore_reads(monkeypatch):
    service = AuthService()
    reads=[]
    doc=SimpleNamespace(exists=True,to_dict=lambda:{'is_active':True,'name':'test'})
    db=SimpleNamespace(collection=lambda _:SimpleNamespace(document=lambda _:
        SimpleNamespace(get=lambda:(reads.append(1) or doc))))
    monkeypatch.setattr('src.db.auth_service.db_client.db',db)
    assert service.validate_key('valid-key')['name']=='test'
    assert service.validate_key('valid-key')['name']=='test'
    assert len(reads)==1
    assert 'valid-key' not in repr(service._key_cache)


def test_key_cache_expires_and_is_bounded(monkeypatch):
    service=AuthService(); clock=[100.0]; reads=[]
    doc=SimpleNamespace(exists=True,to_dict=lambda:{'is_active':True})
    db=SimpleNamespace(collection=lambda _:SimpleNamespace(document=lambda _:
        SimpleNamespace(get=lambda:(reads.append(1) or doc))))
    monkeypatch.setattr('src.db.auth_service.db_client.db',db)
    monkeypatch.setattr('src.db.auth_service.time.monotonic',lambda:clock[0])
    for n in range(1100): service.validate_key(f'key-{n}')
    assert len(service._key_cache)<=1000
    clock[0]+=31
    service.validate_key('key-1099')
    assert len(reads)==1101


def test_usage_firestore_copy_disabled_by_default(monkeypatch, capsys):
    put=Mock(); monkeypatch.setattr(usage_logging._pending,'put_nowait',put)
    monkeypatch.setattr(settings,'STORE_USAGE_IN_FIRESTORE',False)
    usage_logging.emit(tool='lookup_statute',transport='mcp',jurisdiction='SE',status='success',duration_ms=1)
    put.assert_not_called()
    assert 'las_tool_usage' in capsys.readouterr().out


def test_country_cache_reads_only_requested_jurisdiction(monkeypatch):
    db=FirebaseLaborLawDB.__new__(FirebaseLaborLawDB)
    db._local_sections={}; db._cached_statute_sections=None
    db._statute_cache_lock=__import__('threading').RLock()
    marker=SimpleNamespace(exists=True,to_dict=lambda:{'version':'v1'})
    query=SimpleNamespace(stream=lambda:[SimpleNamespace(to_dict=lambda:{'jurisdiction':'ES','active':True})])
    collection=SimpleNamespace(document=lambda _:SimpleNamespace(get=lambda:marker),where=lambda **_:query)
    db.db=SimpleNamespace(collection=lambda _:collection)
    rows=db._get_statute_items('ES')
    assert len(rows)==1 and rows[0]['jurisdiction']=='ES'


def test_coverage_uses_aggregate_counts_not_full_corpus(monkeypatch):
    db=FirebaseLaborLawDB.__new__(FirebaseLaborLawDB); db.db=SimpleNamespace()
    monkeypatch.setattr(db,'_aggregate_country_count',lambda country:{'SE':537,'DE':405}.get(country,0))
    monkeypatch.setattr(db,'_get_statute_items',Mock(side_effect=AssertionError('full corpus read')))
    assert db.count_sections_by_jurisdiction()=={'SE':537,'DE':405}


def test_cloud_run_cost_caps_are_declared():
    workflow=open('.github/workflows/ci.yml',encoding='utf-8').read()
    assert '--max-instances=5' in workflow
    assert '--concurrency=40' in workflow
    server=open('src/server.py',encoding='utf-8').read()
    assert '"access_log": False' in server
