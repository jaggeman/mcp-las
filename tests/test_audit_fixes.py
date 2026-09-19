import io
import json
import runpy
from contextlib import redirect_stdout
from unittest.mock import patch
import pytest
from src.db.firebase_client import db_client
from src.scrapers.european_labor_fetcher import EuropeanLaborFetcher


@pytest.mark.parametrize('query,limit', [('x', -1), ('x', 51), ('x', True), ('', 5), ('x'*2001, 5)])
def test_search_rejects_expensive_or_invalid_parameters(query, limit):
    with patch.object(db_client, '_get_statute_items', side_effect=AssertionError('must reject before reading')):
        with pytest.raises(ValueError):
            db_client.search_statute_sections(query, limit=limit)


def test_repealed_german_sections_excluded():
    xml='<dokumente>' + ''.join('<norm><metadaten><enbez>§ '+str(i)+'</enbez></metadaten><textdaten><text><Content><P>'+text+'</P></Content></text></textdaten></norm>' for i,text in enumerate(['(weggefallen)', '(aufgehoben)', 'Geltender Text.'],1)) + '</dokumente>'
    _, sections=EuropeanLaborFetcher.parse('DE', {'id':'T','name':'T','url':'https://example.test'}, xml)
    assert [s.section_number for s in sections]==['3']


def test_summary_does_not_mutate_country_items():
    class Sync:
        def sync_statutes(self,*args): return {'changed':1,'skipped':0,'errors':0,'items':[{'source_id':'SE'}],'status':'success'}
        def sync_spanish_statutes(self): return {'changed':1,'skipped':0,'errors':0,'items':[{'source_id':'ES'}],'status':'success'}
    output=io.StringIO()
    with patch('src.services.sync_service.SourceSyncService', Sync), patch('sys.argv', ['sync','--swedish','--spanish']), redirect_stdout(output):
        with pytest.raises(SystemExit) as exc: runpy.run_path('scripts/sync_sources.py',run_name='__main__')
    assert exc.value.code==0
    assert json.loads(output.getvalue())['swedish']['items']==[{'source_id':'SE'}]


def test_search_reuses_country_index(monkeypatch):
    rows=[{'id':'a','jurisdiction':'ES','content':'vacaciones','keywords':[]}, {'id':'b','jurisdiction':'DE','content':'Urlaub','keywords':[]}]
    monkeypatch.setattr(db_client,'_get_statute_items',lambda: rows)
    db_client.search_statute_sections('vacaciones',{'jurisdiction':'ES'})
    with patch.object(db_client,'_prepare_search_row',side_effect=AssertionError('index rebuilt')):
        assert db_client.search_statute_sections('vacaciones',{'jurisdiction':'ES'})


def test_publication_commits_all_writes_together(monkeypatch):
    from types import SimpleNamespace
    staged=[]; committed=[]
    class Tx:
        def get(self, query): return []
        def set(self, ref, row): staged.append((ref,row))
        def update(self, ref, row): staged.append((ref,row))
    class Collection:
        def document(self,id): return id
        def where(self,**kwargs): return self
    monkeypatch.setattr(db_client,'db',SimpleNamespace(transaction=Tx,collection=lambda _:Collection()))
    def transactional(fn):
        def run(tx):
            result=fn(tx)
            committed.extend(staged)
            return result
        return run
    monkeypatch.setattr('google.cloud.firestore_v1.transactional',transactional)
    assert db_client.publish_statute('SE:test',{'id':'test'},[{'id':'a','statute_id':'test','jurisdiction':'SE'}],'test','SE',{'status':'success'})
    assert len(committed)==4  # section, metadata, sync state, cache version


def test_publication_failure_does_not_publish(monkeypatch):
    from types import SimpleNamespace
    class Tx:
        def get(self, query): return []
        def set(self,*args): raise RuntimeError('failed staging')
    class Collection:
        def document(self,id): return id
        def where(self,**kwargs): return self
    monkeypatch.setattr(db_client,'db',SimpleNamespace(transaction=Tx,collection=lambda _:Collection()))
    monkeypatch.setattr('google.cloud.firestore_v1.transactional',lambda fn:fn)
    monkeypatch.setattr(db_client,'_cached_statute_sections',[{'content':'old'}])
    with pytest.raises(RuntimeError):
        db_client.publish_statute('SE:test',{'id':'test'},[{'id':'a'}],'test','SE',{})
    assert db_client._cached_statute_sections==[{'content':'old'}]


def test_cache_checks_version_without_reloading_unchanged_corpus(monkeypatch):
    from types import SimpleNamespace
    clock=[100.0]; version=['a']; reads=[]
    class Collection:
        def document(self, id): return SimpleNamespace(get=lambda: SimpleNamespace(exists=True,to_dict=lambda:{'version':version[0]}))
        def stream(self):
            reads.append(1)
            return [SimpleNamespace(to_dict=lambda:{'id':version[0]})]
    monkeypatch.setattr(db_client,'db',SimpleNamespace(collection=lambda _:Collection()))
    monkeypatch.setattr(db_client,'_cached_statute_sections',None)
    monkeypatch.setattr('src.db.firebase_client.time.monotonic',lambda:clock[0])
    first=db_client._get_statute_items()
    clock[0]+=61
    assert db_client._get_statute_items() is first
    assert len(reads)==1
    version[0]='b'; clock[0]+=61
    assert db_client._get_statute_items()[0]['id']=='b'
    clock[0]+=301
    db_client._get_statute_items()
    assert len(reads)==3


def test_country_filter_applied_before_tokenization(monkeypatch):
    rows=[{'id':'a','jurisdiction':'ES','content':'vacaciones','keywords':[]}, {'id':'b','jurisdiction':'DE','content':'Urlaub','keywords':[]}]
    monkeypatch.setattr(db_client,'_get_statute_items',lambda:rows)
    with patch.object(db_client,'_prepare_search_row',wraps=db_client._prepare_search_row) as prepare:
        db_client.search_statute_sections('vacaciones',{'jurisdiction':'ES'})
    assert prepare.call_count==1
    assert prepare.call_args.args[0]['id']=='a'


def test_oversized_atomic_publication_rejected_before_transaction(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(db_client,'db',SimpleNamespace())
    with pytest.raises(ValueError,match='limits'):
        db_client.publish_statute('test',{},[{'id':str(i)} for i in range(448)],'test','SE',{})


def test_failed_commit_keeps_cached_snapshot(monkeypatch):
    from types import SimpleNamespace
    class Tx:
        def get(self, query): return []
        def set(self,*args): pass
    class Collection:
        def document(self,id): return id
        def where(self,**kwargs): return self
    def transactional(fn):
        def run(tx):
            fn(tx)
            raise RuntimeError('commit failed')
        return run
    monkeypatch.setattr(db_client,'db',SimpleNamespace(transaction=Tx,collection=lambda _:Collection()))
    monkeypatch.setattr('google.cloud.firestore_v1.transactional',transactional)
    old=[{'content':'old'}]
    monkeypatch.setattr(db_client,'_cached_statute_sections',old)
    with pytest.raises(RuntimeError,match='commit failed'):
        db_client.publish_statute('test',{'id':'test'},[{'id':'a'}],'test','SE',{})
    assert db_client._cached_statute_sections is old
