from unittest.mock import patch
from types import SimpleNamespace
import pytest
from src.db.firebase_client import db_client
from src.services.sync_service import SourceSyncService
from src.scrapers.european_labor_fetcher import EuropeanLaborFetcher
from src.mcp_tools.tools import search_labor_law
from tests.test_no_de_sources import DE_XML, NO_HTML

class Store:
    def publish_statute(self, source_id, metadata, rows, statute_id, country, state):
        if self.fail: return False
        for row in rows: self.rows[row['id']] = row.copy()
        self.retire_missing_sections(statute_id, country, {row['id'] for row in rows})
        self.states[source_id] = state.copy()
        return True
    def __init__(self): self.states={}; self.rows={}; self.fail=None
    def get_sync_state(self,key): return self.states.get(key)
    def save_statute(self,row): return True
    def save_statute_section(self,row):
        if self.fail: return False
        self.rows[row['id']]=row.copy(); return True
    def retire_missing_sections(self,statute_id,jurisdiction,ids):
        for row in self.rows.values():
            if row['statute_id']==statute_id and row['jurisdiction']==jurisdiction and row['id'] not in ids:
                row['active']=False
        return True
    def save_sync_state(self,key,row): self.states[key]=row.copy(); return True

class Embedding:
    identity='v1'
    def fingerprint(self): return self.identity
    def get_embedding(self,text): return [1.0]

def document(id='X'):
    return EuropeanLaborFetcher.parse('DE',{'id':id,'name':id,'url':'https://example.test'},DE_XML)

def test_sync_retires_missing_and_reindexes_provider_change():
    db=Store(); embed=Embedding(); service=SourceSyncService(db=db,embedder=embed)
    meta,sections=document()
    extra=sections[0].model_copy(update={'id':'extra','section_number':'2','raw_text':'2 text'})
    with patch.object(EuropeanLaborFetcher,'iter_documents',return_value=iter([(meta,sections+[extra])])):
        assert service.sync_european_statutes('DE')['changed']==1
    with patch.object(EuropeanLaborFetcher,'iter_documents',return_value=iter([(meta,sections)])):
        assert service.sync_european_statutes('DE')['changed']==1
    assert db.rows['extra']['active'] is False
    embed.identity='v2'
    with patch.object(EuropeanLaborFetcher,'iter_documents',return_value=iter([(meta,sections)])):
        assert service.sync_european_statutes('DE')['changed']==1

def test_failure_does_not_stop_following_law():
    class FailFirst(Store):
        def publish_statute(self, source_id, metadata, *args):
            return False if metadata['id']=='DE:X' else super().publish_statute(source_id, metadata, *args)
    with patch.object(EuropeanLaborFetcher,'iter_documents',return_value=iter([document(),document('Y')])):
        result=SourceSyncService(db=FailFirst(),embedder=Embedding()).sync_european_statutes('DE')
    assert (result['errors'],result['changed'])==(1,1)

def test_norwegian_default_paragraph_is_preserved():
    _,sections=EuropeanLaborFetcher.parse('NO',{'id':'x','name':'X','url':'https://example.test'},NO_HTML.replace('class="legalP"','class="defaultP"'))
    assert 'varsle' in sections[0].content

def test_explicit_se_overrides_legacy_filter(monkeypatch):
    calls=[]
    monkeypatch.setattr(db_client,'search_statute_sections',lambda **kw: calls.append(kw) or [])
    search_labor_law('x',jurisdiction='SE',filters={'jurisdiction':'DK'})
    assert calls[-1]['filters']['jurisdiction']=='SE'
    search_labor_law('x',filters={'jurisdiction':'DK'})
    assert calls[-1]['filters']['jurisdiction']=='DK'

def test_cache_expires_and_retired_rows_are_hidden(monkeypatch):
    clock=[100.0]; rows=[{'id':'a','active':True}]
    class Collection:
        def document(self, id): return SimpleNamespace(get=lambda: SimpleNamespace(exists=False))
        def stream(self): return [SimpleNamespace(to_dict=lambda r=r:r) for r in rows]
    monkeypatch.setattr(db_client,'db',SimpleNamespace(collection=lambda _:Collection()))
    monkeypatch.setattr(db_client,'_cached_statute_sections',None)
    monkeypatch.setattr(db_client,'_statute_cache_at',0,raising=False)
    monkeypatch.setattr('src.db.firebase_client.time.monotonic',lambda:clock[0])
    assert len(db_client._get_statute_items())==1
    rows.extend([{'id':'b'},{'id':'old','active':False}]);clock[0]+=61
    assert len(db_client._get_statute_items())==2

def test_excel_mcp_returns_result(monkeypatch):
    import src.server as server
    monkeypatch.setattr(server,'_generate_turordningslista_excel',lambda **kw:{'download_url':'test.xlsx'})
    monkeypatch.setattr(server,'_check_rate_limit',lambda *args:None)
    monkeypatch.setattr(server.auth_service,'log_access',lambda *a:None)
    fn=getattr(server.generate_turordningslista_excel,'fn',server.generate_turordningslista_excel)
    assert fn()=={'download_url':'test.xlsx'}


def test_fetch_failure_continues_with_other_german_laws(monkeypatch):
    import io, zipfile
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w') as z: z.writestr('law.xml',DE_XML)
    calls=[]
    def download(url):
        calls.append(url)
        if len(calls)==1: raise RuntimeError('source unavailable')
        return archive.getvalue()
    monkeypatch.setattr(EuropeanLaborFetcher,'_download',download)
    results=list(EuropeanLaborFetcher.iter_documents('DE'))
    from src.scrapers.european_labor_fetcher import GERMAN_LAWS
    assert len(results)==len(GERMAN_LAWS) and isinstance(results[0][1],Exception)
    assert len(results[-1][1])==1


def test_retirement_scopes_country_and_keeps_recoverable_records(monkeypatch):
    changes={}
    class Doc:
        def __init__(self,id,country):
            self.id=id; self.country=country
            self.reference=SimpleNamespace(update=lambda patch:changes.update({id:patch}))
        def to_dict(self): return {'jurisdiction':self.country,'content':'original'}
    class Collection:
        def where(self,*,filter):
            assert filter.field_path=='statute_id' and filter.value=='X'
            return self
        def stream(self): return [Doc('keep','DE'),Doc('retire','DE'),Doc('foreign','NO')]
    monkeypatch.setattr(db_client,'db',SimpleNamespace(collection=lambda _:Collection()))
    monkeypatch.setattr(db_client,'_local_sections',{})
    assert db_client.retire_missing_sections('X','DE',{'keep'}) is True
    assert changes=={'retire':{'active':False}}


def test_failed_writes_never_report_success_for_sweden():
    from tests.test_sync_service import FakeFetcher
    db=Store(); db.fail=True
    result=SourceSyncService(db=db,fetcher=FakeFetcher,embedder=Embedding()).sync_statutes(['1982:80'])
    assert result['errors']==1 and result['changed']==0
    assert db.states['statute:1982:80']['status']=='error'


def test_embedding_provider_is_explicit_and_does_not_fallback(monkeypatch):
    from src.config import settings
    from src.embeddings.embedder import Embedder
    monkeypatch.setattr(settings,'EMBEDDING_PROVIDER','mock')
    monkeypatch.setattr(settings,'OPENAI_API_KEY','unused')
    monkeypatch.setattr(Embedder,'_embed_openai',lambda _:pytest.fail('mock must not call OpenAI'))
    assert len(Embedder.get_embedding('test'))==1536
    monkeypatch.setattr(settings,'EMBEDDING_PROVIDER','openai')
    monkeypatch.setattr(settings,'OPENAI_API_KEY',None)
    with pytest.raises(ValueError): Embedder.get_embedding('test')
