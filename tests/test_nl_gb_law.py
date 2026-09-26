from datetime import date
from pathlib import Path
from unittest.mock import patch

from src.services.sync_service import SourceSyncService


NL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<toestand bwb-id="BWBRTEST" inwerkingtreding="2026-01-01">
  <wetgeving>
    <hoofdstuk><kop><nr>7</nr><titel>Arbeid</titel></kop>
      <artikel bwb-ng-variabel-deel="/Hoofdstuk7/Artikel7:1" label="Artikel 7:1">
        <kop><nr>7:1</nr><titel>Arbeidsovereenkomst</titel></kop>
        <lid><lidnr>1</lidnr><al>De werknemer verricht arbeid tegen loon.</al></lid>
        <meta-data><brondata>historische metadata</brondata></meta-data>
      </artikel>
    </hoofdstuk>
  </wetgeving>
</toestand>"""

GB_AKN = """<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
  <act><body>
    <part eId="part-1"><num>Part I</num><heading>Employment particulars</heading>
      <section eId="section-1"><num>1</num><heading>Written statement</heading>
        <subsection eId="section-1-1"><num>(1)</num><content><p>An employer shall give a worker a written statement.</p></content></subsection>
        <note><p>Editorial note must not be indexed.</p></note>
      </section>
    </part>
  </body></act>
</akomaNtoso>"""

GB_REGULATION_AKN = """<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"><act><body>
  <hcontainer name="regulation" eId="regulation-4"><num>4.</num><heading>Maximum weekly working time</heading>
    <content><p>A worker's working time shall not exceed the maximum.</p></content>
    <note>Editorial annotation must not be indexed.</note>
  </hcontainer>
</body></act></akomaNtoso>"""


def test_new_country_catalogs_are_bounded_and_official():
    from src.scrapers.official_labor_fetcher import DUTCH_LAWS, UK_LAWS

    assert len(DUTCH_LAWS) == 9
    assert len(UK_LAWS) == 10
    assert UK_LAWS[0][-1] == 145
    assert all(row[0].startswith("BWBR") for row in DUTCH_LAWS)
    assert all(row[0] in {"ukpga", "uksi"} for row in UK_LAWS)


def test_dutch_manifest_selects_latest_version_in_force_not_future_version():
    from src.scrapers.official_labor_fetcher import OfficialLaborFetcher

    manifest = """<work>
      <expression label="2025-01-01_0"><metadata><datum_inwerkingtreding>2025-01-01</datum_inwerkingtreding><einddatum>2026-12-31</einddatum></metadata><manifestation label="xml"><item label="old.xml"/></manifestation></expression>
      <expression label="2027-01-01_0"><metadata><datum_inwerkingtreding>2027-01-01</datum_inwerkingtreding></metadata><manifestation label="xml"><item label="future.xml"/></manifestation></expression>
    </work>"""

    assert OfficialLaborFetcher.select_dutch_item(manifest, today=date(2026, 9, 26)) == "2025-01-01_0/xml/old.xml"


def test_dutch_xml_parser_indexes_articles_without_metadata():
    from src.scrapers.official_labor_fetcher import OfficialLaborFetcher

    metadata, sections = OfficialLaborFetcher.parse_dutch(
        {"id": "BWBRTEST", "name": "Testwet", "path_prefix": "/Hoofdstuk7/"}, NL_XML
    )

    assert metadata["jurisdiction"] == "NL" and metadata["language"] == "nl"
    assert len(sections) == 1
    assert sections[0].section_number == "7:1"
    assert sections[0].chapter == "7"
    assert "werknemer" in sections[0].content
    assert "historische metadata" not in sections[0].content


def test_uk_akn_parser_indexes_sections_without_editorial_notes():
    from src.scrapers.official_labor_fetcher import OfficialLaborFetcher

    metadata, sections = OfficialLaborFetcher.parse_uk(
        {"id": "ukpga-1996-18", "name": "Employment Rights Act 1996", "url": "https://www.legislation.gov.uk/ukpga/1996/18"},
        GB_AKN,
    )

    assert metadata["jurisdiction"] == "GB" and metadata["language"] == "en"
    assert len(sections) == 1
    assert sections[0].section_number == "1"
    assert sections[0].chapter == "1"
    assert "written statement" in sections[0].content
    assert "Editorial note" not in sections[0].content


def test_uk_akn_parser_indexes_regulation_hcontainers():
    from src.scrapers.official_labor_fetcher import OfficialLaborFetcher

    _, sections = OfficialLaborFetcher.parse_uk(
        {"id": "uksi-1998-1833", "name": "Working Time Regulations 1998", "url": "https://www.legislation.gov.uk/uksi/1998/1833"},
        GB_REGULATION_AKN,
    )

    assert len(sections) == 1
    assert sections[0].section_number == "4"
    assert "Editorial annotation" not in sections[0].content


def test_uk_parser_can_bound_an_oversized_act_without_splitting_sections():
    from src.scrapers.official_labor_fetcher import OfficialLaborFetcher

    xml = GB_AKN.replace(
        "</part>",
        '<section eId="section-300"><num>300</num><heading>Later provision</heading><content><p>Outside the bounded catalogue.</p></content></section></part>',
    )
    _, sections = OfficialLaborFetcher.parse_uk(
        {"id": "ukpga-1996-18", "name": "Employment Rights Act 1996", "url": "https://www.legislation.gov.uk/ukpga/1996/18", "max_section": 236},
        xml,
    )

    assert [section.section_number for section in sections] == ["1"]


def test_sync_service_supports_new_official_catalogs():
    from src.scrapers.official_labor_fetcher import OfficialLaborFetcher

    class DB:
        def get_sync_state(self, source_id): return None
        def save_sync_state(self, source_id, state): return True
        def publish_statute(self, *args): return True

    with patch.object(OfficialLaborFetcher, "iter_documents", return_value=iter([
        ({"id": "NL:test", "statute_id": "test", "jurisdiction": "NL", "language": "nl"},
         [type("Section", (), {"raw_text": "Artikel 1 tekst", "model_dump": lambda self: {"id": "nl-test_s1", "statute_id": "test", "raw_text": self.raw_text}})()])
    ])):
        result = SourceSyncService(db=DB()).sync_official_statutes("NL")

    assert result["status"] == "success" and result["changed"] == 1


def test_new_countries_are_in_tools_website_and_weekly_sync():
    from src.mcp_tools.tools import SUPPORTED_JURISDICTIONS

    html = Path("public/index.html").read_text(encoding="utf-8")
    sync_script = Path("scripts/sync_sources.py").read_text(encoding="utf-8")
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert SUPPORTED_JURISDICTIONS["NL"] == "nl"
    assert SUPPORTED_JURISDICTIONS["GB"] == "en"
    assert 'data-country="NL"' in html and 'data-country="GB"' in html
    for flag in ("--dutch", "--british"):
        assert flag in sync_script and flag in ci


def test_production_monitor_has_queries_for_every_supported_country():
    from scripts.production_smoke import SMOKE_QUERIES
    from src.mcp_tools.tools import SUPPORTED_JURISDICTIONS

    assert set(SMOKE_QUERIES) == set(SUPPORTED_JURISDICTIONS)
