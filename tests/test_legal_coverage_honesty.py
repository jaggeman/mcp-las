# -*- coding: utf-8 -*-
"""get_legal_coverage måste svara om vad databasen faktiskt innehåller.

Upptäckt genom att fråga den levande servern: verktyget svarade
`"DK": {"statutes": true, ...}` medan `lookup_statute` och `search_labor_law`
för DK gav "ej funnen" respektive tom träfflista. Skraper-infrastrukturen för
Danmark (Retsinformation) och Finland (Finlex) finns i repot, men ingen
fullständig ingestion har någonsin körts mot paygap-prod — det finns inte
ens ett motsvarande "ingest_danish_statutes.py" till skillnad från Sveriges
`scripts/ingest_statutes.py`.

Det är samma felklass som "17 kollektivavtal" (#18) och den falskt
rapporterande ingestionen (#32): ett påstående om täckning som inte
matchar vad som faktiskt går att fråga.
"""

import pytest

from src.mcp_tools.tools import get_legal_coverage
from src.db.firebase_client import db_client


@pytest.fixture(autouse=True)
def _clean_cache():
    """Varje test styr sitt eget innehåll i statute_sections."""
    db_client._cached_statute_sections = None
    db_client._local_sections = {}
    yield
    db_client._cached_statute_sections = None
    db_client._local_sections = {}


def _seed(jurisdiction, doc_id="x1"):
    db_client._local_sections[doc_id] = {
        "id": doc_id, "statute_id": "TEST", "statute_short": "TEST",
        "section_number": "1", "content": "text", "jurisdiction": jurisdiction,
    }
    db_client._cached_statute_sections = None


def test_a_jurisdiction_with_no_ingested_sections_reports_statutes_false():
    """Inget seedat alls -> ingen jurisdiktion får påstå att den har lagtext."""
    coverage = get_legal_coverage()
    assert coverage["jurisdictions"]["SE"]["statutes"] is False
    assert coverage["jurisdictions"]["DK"]["statutes"] is False
    assert coverage["jurisdictions"]["FI"]["statutes"] is False


def test_a_jurisdiction_with_ingested_sections_reports_statutes_true():
    _seed("SE")
    coverage = get_legal_coverage()
    assert coverage["jurisdictions"]["SE"]["statutes"] is True
    # DK och FI ska inte smittas av att SE har data.
    assert coverage["jurisdictions"]["DK"]["statutes"] is False
    assert coverage["jurisdictions"]["FI"]["statutes"] is False


def test_section_counts_are_reported_per_jurisdiction():
    """Ett booleskt ja/nej döljer skillnaden mellan 1 och 492 paragrafer."""
    _seed("SE", "s1")
    db_client._local_sections["s2"] = {
        "id": "s2", "statute_id": "TEST2", "statute_short": "TEST2",
        "section_number": "1", "content": "text", "jurisdiction": "SE",
    }
    db_client._cached_statute_sections = None
    coverage = get_legal_coverage()
    assert coverage["jurisdictions"]["SE"]["section_count"] == 2
    assert coverage["jurisdictions"]["DK"]["section_count"] == 0


def test_sections_without_a_stored_jurisdiction_default_to_SE():
    """Äldre poster ingesterades innan jurisdiction-fältet fanns.

    Samma standardval som redan gäller i get_statute_section — annars
    skulle den här ärliggörelsen räkna bort data som redan finns.
    """
    db_client._local_sections["legacy"] = {
        "id": "legacy", "statute_id": "1982:80", "statute_short": "LAS",
        "section_number": "7", "content": "text",
        # inget "jurisdiction"-fält alls
    }
    db_client._cached_statute_sections = None
    coverage = get_legal_coverage()
    assert coverage["jurisdictions"]["SE"]["statutes"] is True
    assert coverage["jurisdictions"]["SE"]["section_count"] == 1
