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

def test_calculate_unpaid_vacation_deduction():
    from src.mcp_tools.tools import calculate_unpaid_vacation_deduction
    # 40000 * 4.6% * 5 = 9200
    res = calculate_unpaid_vacation_deduction(monthly_salary=40000, unpaid_days=5)
    assert res["calculation"]["daily_deduction_kr"] == 1840.0
    assert res["calculation"]["total_deduction_kr"] == 9200.0
    assert res["calculation"]["remaining_monthly_salary_kr"] == 30800.0

    # Advance vacation debt
    res_adv = calculate_unpaid_vacation_deduction(monthly_salary=30000, unpaid_days=10, is_advance_vacation_debt=True)
    assert res_adv["calculation"]["total_deduction_kr"] == 13800.0
    assert "advance_vacation_rules" in res_adv
    assert res_adv["advance_vacation_rules"]["debt_amount_kr"] == 13800.0

def test_calculate_earned_vacation_days():
    from src.mcp_tools.tools import calculate_earned_vacation_days
    # Started half year (182 days out of 365) with 25 days right:
    # 25 * 182 / 365 = 12.465 -> ceil -> 13 paid days, 12 unpaid days
    res = calculate_earned_vacation_days(employment_days_in_earning_year=182, annual_vacation_right=25)
    assert res["result"]["paid_vacation_days"] == 13
    assert res["result"]["unpaid_vacation_days"] == 12

    # Full year (365 days): 25 paid, 0 unpaid
    res_full = calculate_earned_vacation_days(employment_days_in_earning_year=365, annual_vacation_right=25)
    assert res_full["result"]["paid_vacation_days"] == 25
    assert res_full["result"]["unpaid_vacation_days"] == 0

def test_get_employer_certificate_info():
    from src.mcp_tools.tools import get_employer_certificate_info
    res = get_employer_certificate_info()
    assert "arbetsgivarintyg.nu" in res["official_service_url"]
    assert "47 §" in res["legal_duty"]["section"]


