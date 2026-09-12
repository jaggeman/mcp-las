import pytest
from src.db.firebase_client import FirebaseLaborLawDB, db_client
from src.mcp_tools.tools import search_labor_law

def test_stemming_swedish_words():
    assert FirebaseLaborLawDB._stem_sv("uppsägningar") == "uppsägn"
    assert FirebaseLaborLawDB._stem_sv("kollektivavtalen") == "kollektivavtal"

def test_search_labor_law_precision():
    results = search_labor_law("Vad krävs för sakliga skäl vid uppsägning?")
    assert len(results) > 0
    top = results[0]
    assert "las" in str(top).lower() or "7" in str(top)


def test_search_labor_law_supports_jurisdiction_filter(monkeypatch):
    monkeypatch.setattr(db_client, "_local_sections", {
        "se-1": {
            "id": "se-1", "statute_short": "LAS", "statute_id": "1982:80",
            "section_number": "7", "content": "sakliga skäl för uppsägning",
            "keywords": ["uppsägning"], "embedding": [], "jurisdiction": "SE",
        },
        "dk-1": {
            "id": "dk-1", "statute_short": "Funktionærloven", "statute_id": "A202400001",
            "section_number": "1", "content": "opsigelse og funktionærer",
            "keywords": ["opsigelse"], "embedding": [], "jurisdiction": "DK",
        },
    })
    monkeypatch.setattr(db_client, "_cached_statute_sections", None)
    monkeypatch.setattr(db_client, "db", None)

    results = search_labor_law("opsigelse", filters={"jurisdiction": "DK"})

    assert results
    assert all(result["jurisdiction"] == "DK" for result in results)
