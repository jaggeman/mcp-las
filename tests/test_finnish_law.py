from src.chunking.finnish_law_chunker import FinnishLawChunker
from src.scrapers.finlex_fetcher import FinlexFetcher
import html
import json


SAMPLE_AKOMA_NTOSO = """
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
  <meta>
    <identification source="#finlex">
      <FRBRWork><FRBRname value="Työsopimuslaki"/></FRBRWork>
      <FRBRdate date="2024-01-01" name="issued"/>
    </identification>
  </meta>
  <body>
    <chapter><num>1 luku</num><heading>Yleiset säännökset</heading>
      <section><num>1 §</num><heading>Lain tarkoitus</heading><content><p>Tässä laissa säädetään työsopimuksesta.</p></content></section>
      <section><num>2 §</num><content><p>Työntekijä sitoutuu tekemään työtä.</p></content></section>
    </chapter>
  </body>
</akomaNtoso>
"""


def test_finnish_chunker_parses_akomantoso_sections_and_chapter():
    sections = FinnishLawChunker.chunk_xml(
        statute_id="55/2001",
        statute_short="Työsopimuslaki",
        xml=SAMPLE_AKOMA_NTOSO,
    )

    assert [section.section_number for section in sections] == ["1", "2"]
    assert sections[0].chapter == "1"
    assert sections[0].section_title == "Lain tarkoitus"
    assert "työsopimuksesta" in sections[0].content
    assert sections[0].id.startswith("fi-55-2001")


def test_finlex_parser_extracts_metadata_and_xml_text():
    metadata, sections = FinlexFetcher.parse_document(
        document_id="akn/fi/act/statute/2001/55",
        document_url="https://www.finlex.fi/fi/laki/ajantasa/2001/20010055",
        xml=SAMPLE_AKOMA_NTOSO,
        title="Työsopimuslaki",
    )

    assert metadata["jurisdiction"] == "FI"
    assert metadata["language"] == "fi"
    assert metadata["title"] == "Työsopimuslaki"
    assert metadata["source"] == "Finlex"
    assert len(sections) == 2


def test_finlex_fetcher_builds_paginated_list_request(monkeypatch):
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [{"akn_uri": "https://example.test/akn/fi/act/statute/2001/55/fin@"}]}

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr("src.scrapers.finlex_fetcher.requests.get", fake_get)

    documents = FinlexFetcher.harvest_statutes(start_year=2024, end_year=2024, page=2, limit=5)

    assert documents == [{"akn_uri": "https://example.test/akn/fi/act/statute/2001/55/fin@"}]
    assert calls[0][0].endswith("/akn/fi/act/statute/list")
    assert calls[0][1]["params"]["page"] == 2
    assert calls[0][1]["params"]["limit"] == 5
    assert calls[0][1]["params"]["langAndVersion"] == "fin@"
    assert calls[0][1]["params"]["startYear"] == 2024
    assert calls[0][1]["params"]["endYear"] == 2024
    assert "User-Agent" in calls[0][1]["headers"]


def _flight_script(*lines):
    payload = "\n".join(lines) + "\n"
    return f"<script>self.__next_f.push({html.escape(json.dumps([1, payload]))})</script>"


def test_finlex_current_page_parser_reads_consolidated_finnish_sections():
    page = "".join([
        _flight_script(
            '1:["$","h3",null,{"id":"chp_1","children":[["$","span",null,{"className":"highlightable","children":"1 luku"}],["$","span",null,{"className":"highlightable","children":"Yleiset säännökset"}]]}]',
            '2:["$","h4",null,{"id":"chp_1__sec_4","children":[["$","span",null,{"className":"highlightable","children":"4 §"}],["$","span",null,{"className":"highlightable","children":"Koeaika"}]]}]',
            '3:["$","section",null,{"className":"subsection","children":["$L10",false]}]',
            '4:["$","h3",null,{"id":"chp_2","children":[["$","span",null,{"className":"highlightable","children":"2 luku"}],["$","span",null,{"className":"highlightable","children":"Työnantajan velvollisuudet"}]]}]',
            '5:["$","h4",null,{"id":"chp_2__sec_1","children":[["$","span",null,{"className":"highlightable","children":"1 §"}],["$","span",null,{"className":"highlightable","children":"Yleisvelvoite"}]]}]',
            '6:["$","section",null,{"className":"subsection","children":["$L11",false]}]',
        ),
        _flight_script(
            '10:["$","p",null,{"children":[["$","span",null,{"className":"highlightable","children":"Koeaika saa olla enintään kuusi kuukautta."}]]}]',
            '11:["$","p",null,{"children":[["$","span",null,{"className":"highlightable","children":"Työnantajan on edistettävä suhteitaan työntekijöihin."}]]}]',
            # The page also contains a Swedish document view. It must not be mixed in.
            '12:["$","h3",null,{"id":"chp_1","children":[["$","span",null,{"className":"highlightable","children":"1 kap."}]]}]',
        ),
    ])

    sections = FinlexFetcher.parse_current_page(
        statute_id="55/2001", statute_short="Työsopimuslaki", html=page,
    )

    assert [(row.chapter, row.section_number) for row in sections] == [("1", "4"), ("2", "1")]
    assert sections[0].section_title == "Koeaika"
    assert "kuusi kuukautta" in sections[0].content
    assert "kap." not in " ".join(row.content for row in sections)


def test_finnish_catalog_uses_current_consolidated_finlex_pages():
    documents = FinlexFetcher.catalog_documents()

    assert documents
    assert all(document["url"].startswith("https://data.finlex.fi/fi/lainsaadanto/")
               for document in documents)
    assert all(document["format"] == "finlex-current-html" for document in documents)


def test_finlex_current_page_parser_supports_laws_without_chapters():
    page = _flight_script(
        '1:["$","h3",null,{"id":"sec_1","children":[["$","span",null,{"className":"highlightable","children":"1 §"}],["$","span",null,{"className":"highlightable","children":"Lain tarkoitus"}]]}]',
        '2:["$","section",null,{"className":"subsection","children":["$L10",false]}]',
        '10:["$","p",null,{"children":[["$","span",null,{"className":"highlightable","children":"Tämä on ajantasainen säännös."}]]}]',
    )

    sections = FinlexFetcher.parse_current_page("609/1986", "Tasa-arvolaki", page)

    assert len(sections) == 1
    assert sections[0].chapter is None
    assert sections[0].section_number == "1"
