from src.chunking.danish_law_chunker import DanishLawChunker
from src.scrapers.retsinformation_fetcher import RetsinformationFetcher


SAMPLE_DANISH_LAW = """
Funktionærlov

Kapitel 1
Anvendelsesområde

§ 1. Loven gælder for funktionærer.
Stk. 2. Loven gælder også ved arbejde under arbejdsgiverens instruktion.

Opsigelse

§ 2. Opsigelsesvarslet skal gives skriftligt.

Ikrafttrædelse
§ 20. Denne lov træder i kraft.
"""


def test_danish_chunker_parses_chapters_sections_and_stykket():
    sections = DanishLawChunker.chunk_statute_text(
        statute_id="funktionaerloven",
        statute_short="Funktionærloven",
        full_text=SAMPLE_DANISH_LAW,
    )

    assert [section.section_number for section in sections] == ["1", "2"]
    assert sections[0].chapter == "1"
    assert "funktionærer" in sections[0].content
    assert sections[0].id.startswith("dk-funktionaerloven")


def test_retsinformation_xml_parser_extracts_metadata_and_text():
    xml = """
    <document>
      <title>Funktionærlov</title>
      <date>2024-01-01</date>
      <body>Kapitel 1\n§ 1. Loven gælder for funktionærer.</body>
    </document>
    """

    metadata, text = RetsinformationFetcher.parse_document_xml(
        document_id="A202400001",
        href="https://www.retsinformation.dk/eli/accn/A202400001/xml",
        xml=xml,
    )

    assert metadata["jurisdiction"] == "DK"
    assert metadata["language"] == "da"
    assert metadata["title"] == "Funktionærlov"
    assert "§ 1" in text
