import pytest
from unittest.mock import patch

from src.scrapers.european_labor_fetcher import EuropeanLaborFetcher
from src.services.sync_service import SourceSyncService
from src.db.firebase_client import db_client
from src.mcp_tools.tools import lookup_statute, search_labor_law, get_legal_coverage


DE_XML = '''<dokumente><norm><metadaten><enbez>§ 1a</enbez><titel>Urlaub</titel></metadaten>
<textdaten><text><Content><P>Urlaub gemäß § 2.</P><P>Zweiter Absatz.</P></Content></text>
<fussnoten>Redaktionelle Notiz</fussnoten></textdaten></norm></dokumente>'''
NO_HTML = '''<html><main class="documentBody"><article class="legalArticle">
<h3><span class="legalArticleValue">§ 2 A-1</span><span class="legalArticleTitle">Varsling</span></h3>
<article class="legalP">Rett til å varsle etter § 2 A-2.</article>
<article class="changesToParent">Endret ved lov.</article></article></main></html>'''


@pytest.mark.parametrize('country,payload,number,word', [('NO', NO_HTML, '2 a-1', 'varsle'), ('DE', DE_XML, '1a', 'Urlaub')])
def test_structured_sections_preserve_references(country, payload, number, word):
    doc = {'id': 'test', 'name': 'Test', 'url': 'https://example.test'}
    metadata, sections = EuropeanLaborFetcher.parse(country, doc, payload)
    assert len(sections) == 1
    assert sections[0].section_number == number
    assert word in sections[0].content
    assert 'Notiz' not in sections[0].content and 'Endret' not in sections[0].content
    assert metadata['jurisdiction'] == country


@pytest.mark.parametrize('country', ['NO', 'DE'])
def test_empty_source_is_an_error(country):
    with pytest.raises(ValueError):
        EuropeanLaborFetcher.parse(country, {'id':'x','name':'X','url':'https://example.test'}, '<html/>')


def test_duplicate_sections_fail_closed():
    with pytest.raises(ValueError):
        EuropeanLaborFetcher.parse('DE', {'id':'x','name':'X','url':'https://example.test'}, DE_XML.replace('</dokumente>', DE_XML.split('<dokumente>')[1]))


def test_norwegian_numbered_paragraphs_and_treaty_appendix():
    payload = NO_HTML.replace('class="legalP"', 'class="numberedLegalP"').replace('</main>',
        '<article class="legalArticle"><span class="legalArticleValue">Art 1</span><article class="legalP">Treaty appendix</article></article></main>')
    _, sections = EuropeanLaborFetcher.parse('NO', {'id':'x','name':'X','url':'https://example.test'}, payload)
    assert len(sections) == 1 and 'varsle' in sections[0].content


@pytest.mark.parametrize('country', ['NO', 'DE'])
def test_country_lookup_and_search_are_isolated(monkeypatch, country):
    rows = [{'id': c, 'statute_short': 'Test', 'statute_id':'test', 'section_number':'1',
             'content':'Urlaub varsling', 'keywords':[], 'jurisdiction':c, 'language':lang,
             'source':'official', 'source_url':'https://example.test'}
            for c,lang in [('SE','sv'), ('NO','nb'), ('DE','de')]]
    monkeypatch.setattr(db_client, '_get_statute_items', lambda: rows)
    assert lookup_statute('Test','1',jurisdiction=country)['jurisdiction'] == country
    results = search_labor_law('Urlaub varsling',jurisdiction=country)
    assert results and all(r['jurisdiction']==country for r in results)
    assert get_legal_coverage()['jurisdictions'][country]['calculators'] == []


def test_new_sync_does_not_accept_failed_writes():
    metadata, sections = EuropeanLaborFetcher.parse('DE', {'id':'x','name':'X','url':'https://example.test'}, DE_XML)
    class DB:
        def get_sync_state(self, key): return None
        def publish_statute(self, *args): return False
        def save_statute(self, row): return True
        def save_statute_section(self, row): return False
        def save_sync_state(self, key, row):
            assert row['status'] != 'success'
    with patch.object(EuropeanLaborFetcher, 'iter_documents', return_value=iter([(metadata, sections)])):
        result = SourceSyncService(db=DB()).sync_european_statutes('DE')
    assert result['errors'] == 1 and result['changed'] == 0


def test_sync_then_lookup_with_source_and_idempotency(monkeypatch):
    metadata, sections = EuropeanLaborFetcher.parse('DE', {'id':'KSchG','name':'KSchG','url':'https://example.test'}, DE_XML)
    class DB:
        states = {}
        rows = []
        def publish_statute(self, source_id, metadata, rows, statute_id, country, state):
            self.rows.extend(rows); self.states[source_id]=state; return True
        def retire_missing_sections(self, statute_id, jurisdiction, ids): return True
        def get_sync_state(self, key): return self.states.get(key)
        def save_statute(self, row): return True
        def save_statute_section(self, row): self.rows.append(row); return True
        def save_sync_state(self, key, row): self.states[key]=row; return True
    db = DB()
    service = SourceSyncService(db=db)
    with patch.object(EuropeanLaborFetcher, 'iter_documents', side_effect=lambda _: iter([(metadata,sections)])):
        assert service.sync_european_statutes('DE')['changed'] == 1
        assert service.sync_european_statutes('DE')['skipped'] == 1
    monkeypatch.setattr(db_client,'_get_statute_items',lambda: db.rows)
    result = lookup_statute('kschg','1a',jurisdiction='DE')
    assert result['found'] and result['source_url']=='https://example.test'


def test_search_preserves_german_and_norwegian_letters(monkeypatch):
    monkeypatch.setattr(db_client,'_get_statute_items',lambda: [
        {'statute_short':'X', 'statute_id':'x', 'section_number':'1', 'content':'ø', 'jurisdiction':'NO', 'keywords':[]},
    ])
    assert search_labor_law('ø',jurisdiction='NO')


def test_lookup_reads_beyond_one_thousand_sections(monkeypatch):
    class Doc:
        def __init__(self, number): self.number=number
        def to_dict(self):
            return {'statute_short':'Test', 'statute_id':'Test', 'section_number':str(self.number), 'jurisdiction':'DE'}
    class Collection:
        def document(self, id):
            from types import SimpleNamespace
            return SimpleNamespace(get=lambda: SimpleNamespace(exists=False))
        def limit(self, n): raise AssertionError('Global truncation hides whole countries')
        def stream(self): return iter(Doc(n) for n in range(1002))
    class DB:
        def collection(self, name): return Collection()
    monkeypatch.setattr(db_client,'db',DB())
    monkeypatch.setattr(db_client,'_cached_statute_sections',None)
    assert db_client.get_statute_section('Test','1001',jurisdiction='DE') is not None


def test_failed_sync_state_is_not_cached_as_success(monkeypatch):
    monkeypatch.setattr(db_client, 'db', None)
    monkeypatch.setattr(db_client, '_local_sync_state', {}, raising=False)
    assert db_client.save_sync_state('DE:test', {'status':'success'}) is False
    assert db_client.get_sync_state('DE:test') is None
