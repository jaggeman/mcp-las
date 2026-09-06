import pytest
from src.mcp_tools.tools import (
    lookup_statute,
    search_labor_law,
    search_case_law,
    get_cba_exception,
    compare_statute_vs_cba
)
from src.db.firebase_client import db_client

@pytest.fixture(autouse=True)
def setup_test_data():
    # Ensure test section is in db
    db_client.save_statute_section({
        "id": "1982_80_s7",
        "statute_id": "1982:80",
        "statute_short": "LAS",
        "chapter": None,
        "section_number": "7",
        "section_title": "Uppsägning från arbetsgivarens sida",
        "content": "Uppsägning från arbetsgivarens sida ska grundas på sakliga skäl.",
        "raw_text": "7 § Uppsägning från arbetsgivarens sida ska grundas på sakliga skäl.",
        "keywords": ["las", "7 §", "uppsägning", "sakliga skäl"]
    })

def test_lookup_statute():
    res = lookup_statute(law="LAS", section="7")
    assert res["found"] is True
    assert res["law"] == "LAS"
    assert res["section"] == "7"
    assert "sakliga skäl" in res["content"].lower()

def test_search_labor_law():
    res = search_labor_law(query="sakliga skäl för uppsägning")
    assert len(res) > 0
    assert any(r["section"] == "7" for r in res)

def test_search_case_law():
    res = search_case_law(query="personliga skäl uppsägning")
    assert len(res) > 0
    assert "AD 2023 nr 45" in [r["case_number"] for r in res]

def test_get_cba_exception():
    res = get_cba_exception(statute="LAS", section="11", agreement_name="Teknikavtalet")
    assert res["has_exception"] is True
    assert "12 månaders uppsägningstid" in res["rule_content"]

def test_compare_statute_vs_cba():
    res = compare_statute_vs_cba(topic="Uppsägningstid", agreement_name="Teknikavtalet")
    assert res["agreement_name"] == "Teknikavtalet"
    assert len(res["cba_rules"]) > 0

def test_calculate_vacation_pay():
    from src.mcp_tools.tools import calculate_vacation_pay
    res = calculate_vacation_pay(monthly_salary=40000, variable_salary=50000, vacation_days=25)
    assert res["with_collective_agreement"]["fixed_supplement_kr"] == 8000.0
    assert res["without_collective_agreement_statute"]["fixed_supplement_kr"] == 4300.0
    assert res["cba_advantage"]["extra_in_pocket_kr"] > 0
