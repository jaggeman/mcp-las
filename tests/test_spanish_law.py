import datetime
import pytest
from src.scrapers.boe_fetcher import BoeFetcher


XML = '''<response><status><code>200</code></status><data><texto>
<bloque id="a1" tipo="precepto" titulo="Artículo 1.">
<version fecha_publicacion="20200101" fecha_vigencia="20200102"><p>Artículo 1. Ámbito.</p><p>Antiguo.</p></version>
<version fecha_publicacion="20240101" fecha_vigencia="20240201"><p>Artículo 1. Ámbito.</p><p>Trabajo <b>actual</b>.</p></version>
<version fecha_publicacion="20250101" fecha_vigencia="20990101"><p>Futuro.</p></version>
</bloque>
<bloque id="a20bis" tipo="precepto" titulo="Artículo 20 bis."><version fecha_publicacion="20200101"><p>Privacidad.</p></version></bloque>
<bloque id="a2" tipo="precepto" titulo="Artículo 2."><version fecha_publicacion="20200101"><p>Artículo 2.</p><p>(Derogado).</p></version></bloque>
<bloque id="da1" tipo="precepto" titulo="Disposición adicional primera"><version fecha_publicacion="20200101"><p>Artículo 3. Referencia, no artículo independiente.</p></version></bloque>
</texto></data></response>'''


def test_versions_article_boundaries_repeals_and_metadata():
    metadata, sections = BoeFetcher.parse('BOE-A-2015-11430', 'ET', XML, as_of=datetime.date(2026, 9, 19))
    assert [s.section_number for s in sections] == ['1', '20 bis']
    assert 'Trabajo actual.' in sections[0].content
    assert 'Futuro' not in sections[0].content and 'Antiguo' not in sections[0].content
    assert metadata['jurisdiction'] == 'ES' and metadata['language'] == 'es'
    assert metadata['source'] == 'BOE'


def test_duplicate_articles_fail_closed():
    duplicate = XML.replace('</texto>', '<bloque titulo="Artículo 1."><version fecha_publicacion="20200101"><p>Duplicate</p></version></bloque></texto>')
    with pytest.raises(ValueError, match='Duplicate'):
        BoeFetcher.parse('test', 'ET', duplicate)


def test_empty_or_error_payload_rejected():
    with pytest.raises(ValueError): BoeFetcher.parse('test', 'ET', '<response/>')


def test_written_article_numbers_are_preserved_as_numeric_sections():
    payload = XML.replace('Artículo 1.', 'Artículo primero')
    _, sections = BoeFetcher.parse('test', 'LOLS', payload)
    assert sections[0].section_number == '1'


def test_spanish_jurisdiction_and_source_language(monkeypatch):
    from src.mcp_tools import tools
    monkeypatch.setattr(tools.db_client, 'get_statute_section', lambda **kw: {'content': 'Texto', 'section_number': '1', 'statute_short': 'ET', 'jurisdiction': 'ES', 'language': 'es'})
    result = tools.lookup_statute('ET', '1', jurisdiction='ES')
    assert result['found'] and result['language'] == 'es'
