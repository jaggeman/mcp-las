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
