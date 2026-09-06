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

def test_get_rehabilitation_plan_info():
    from src.mcp_tools.tools import get_rehabilitation_plan_info
    res = get_rehabilitation_plan_info()
    assert "FK 7459" in res["template_pdf"]["form_number"]
    assert "30 kap. 6 §" in res["legal_duty"]["statute"]
    assert "dag 30" in res["legal_duty"]["deadline"]

def test_get_discrimination_act_guide():
    from src.mcp_tools.tools import get_discrimination_act_guide
    res = get_discrimination_act_guide()
    assert len(res["grounds_of_discrimination"]) == 7
    assert "Aktiva åtgärder" in res["employer_obligations_active_measures"]["legal_basis"]
    assert "lönekartläggning" in res["employer_obligations_active_measures"]["equal_pay_audit"].lower()

def test_check_bank_days_and_deadlines():
    from src.mcp_tools.tools import check_bank_days_and_deadlines
    # April 2026: 25th is Saturday -> payout on Friday 24th
    res_apr = check_bank_days_and_deadlines(check_salary_payout_for_month=4, year=2026)
    assert res_apr["salary_payout_analysis"]["actual_payout_date"] == "2026-04-24"
    assert res_apr["salary_payout_analysis"]["is_shifted_earlier"] is True

    # December 2026: 25th is Christmas Day, 24th is Christmas Eve -> payout on Wednesday 23rd
    res_dec = check_bank_days_and_deadlines(check_salary_payout_for_month=12, year=2026)
    assert res_dec["salary_payout_analysis"]["actual_payout_date"] == "2026-12-23"

    # Specific date check: 2026-05-01 is a holiday (Första maj)
    res_may1 = check_bank_days_and_deadlines(date_str="2026-05-01")
    assert res_may1["date_checked"]["is_bank_day"] is False
    assert res_may1["date_checked"]["holiday_name"] == "Första maj"

def test_calculate_redundancy_turnorder_and_exceptions():
    from src.mcp_tools.tools import calculate_redundancy_turnorder_and_exceptions
    
    # 1. Test calculation with total 100 employees, 20 redundancies (Alternative 4 / 15% rule -> 3, max 10% cap -> 10)
    res = calculate_redundancy_turnorder_and_exceptions(
        total_employees_in_unit=100,
        redundancy_count=20,
        has_collective_bargaining_agreement=True,
        single_operating_unit_only=False
    )
    assert res["exemption_rules"]["las_statutory_exemption"]["max_exemptions"] == 3
    assert res["exemption_rules"]["cba_exemption_alternatives"]["alternativ_1"]["allowed_exemptions"] == 3
    assert res["exemption_rules"]["cba_exemption_alternatives"]["alternativ_4_procentregel"]["allowed_exemptions"] == 3

    # 2. Test sorting employees list
    employees = [
        {"name": "Alice", "seniority_days": 1500, "age": 40, "has_qualifications": True},
        {"name": "Bob", "seniority_days": 300, "age": 28, "has_qualifications": True},
        {"name": "Charlie", "seniority_days": 300, "age": 35, "has_qualifications": True}, # older than Bob -> prioritized
        {"name": "Diana", "seniority_days": 800, "age": 30, "is_exempt": True} # exempt
    ]
    res_sort = calculate_redundancy_turnorder_and_exceptions(
        redundancy_count=1,
        employees_list=employees
    )
    sorted_list = res_sort["sorted_turordningslista"]
    assert sorted_list[0]["name"] == "Alice"
    assert sorted_list[1]["name"] == "Diana"
    assert sorted_list[2]["name"] == "Charlie"  # Same seniority as Bob but older (35 > 28)
    assert sorted_list[3]["name"] == "Bob"
    assert "Risk för uppsägning" in sorted_list[3]["protection_status"]

def test_generate_turordningslista_excel():
    from src.mcp_tools.tools import generate_turordningslista_excel, GENERATED_EXCEL_FILES
    
    res = generate_turordningslista_excel(
        company_name="Nordic Tech AB",
        redundancy_count=2,
        employees=[
            {"name": "Karin", "title": "Lead Dev", "driftsenhet": "Sthlm", "start_date": "2018-01-01", "birth_date": "1985-02-10", "has_qualifications": True, "is_exempt": True},
            {"name": "Olof", "title": "Dev", "driftsenhet": "Sthlm", "start_date": "2020-05-01", "birth_date": "1990-08-15", "has_qualifications": True, "is_exempt": False},
            {"name": "Elin", "title": "Junior Dev", "driftsenhet": "Sthlm", "start_date": "2023-01-10", "birth_date": "1996-12-01", "has_qualifications": True, "is_exempt": False}
        ]
    )
    
    assert res["success"] is True
    assert "download_url" in res
    assert res["file_name"].startswith("Turordningslista_Nordic_Tech_AB")
    assert len(res["file_base64"]) > 500
    assert res["file_id"] in GENERATED_EXCEL_FILES
    assert "EMP-001" in res["markdown_table"]
    assert "Karin" in res["markdown_table"]

def test_get_hr_document_template():
    from src.mcp_tools.tools import get_hr_document_template
    
    # 1. Omplaceringsutredning
    res_utredning = get_hr_document_template(
        template_type="omplaceringsutredning",
        company_name="Region Stockholm",
        employee_name="Anna Svensson",
        personal_identity_number="19850512-1234",
        job_title="Sjuksköterska",
        reason_type="arbetsbrist"
    )
    assert "7 § andra stycket" in res_utredning["legal_basis"]
    assert "Anna Svensson" in res_utredning["document_template_text"]
    assert "Region Stockholm" in res_utredning["document_template_text"]
    assert len(res_utredning["statutory_required_elements"]) > 3

    # 2. Omplaceringserbjudande
    res_offer = get_hr_document_template(
        template_type="omplaceringserbjudande",
        employee_name="Erik Johansson",
        offered_position_title="Verksamhetsutvecklare"
    )
    assert "OMPLACERINGSERBJUDANDE" in res_offer["document_template_text"]
    assert "Tackar JA" in res_offer["document_template_text"]
    assert "Tackar NEJ" in res_offer["document_template_text"]
    assert "Erik Johansson" in res_offer["document_template_text"]

    # 3. Varsel personliga skäl
    res_varsel = get_hr_document_template(
        template_type="varsel_personliga_skal",
        employee_name="Johan Berg",
        union_name="Vision Avdelning 45"
    )
    assert "30 §" in res_varsel["legal_basis"]
    assert "EN VECKA" in res_varsel["document_template_text"]
    assert "Vision Avdelning 45" in res_varsel["document_template_text"]

    # 4. Anställningsbevis (6 c § LAS)
    res_anstallning = get_hr_document_template(
        template_type="anstallningsbevis",
        company_name="Svenska AB",
        employee_name="Maria Karlsson",
        job_title="Systemarkitekt"
    )
    assert "6 c §" in res_anstallning["legal_basis"]
    assert "ANSTÄLLNINGSBEVIS" in res_anstallning["document_template_text"]
    assert "Provanställning" in res_anstallning["document_template_text"]
    assert "Svenska AB" in res_anstallning["document_template_text"]

    # 5. Anmälan om företrädesrätt
    res_anmalan = get_hr_document_template(
        template_type="anmalan_foretradesratt",
        company_name="Svenska AB",
        employee_name="Sara Nilsson"
    )
    assert "25–27 §§" in res_anmalan["legal_basis"]
    assert "ANMÄLAN OM ANSPRÅK PÅ FÖRETRÄDESRÄTT" in res_anmalan["document_template_text"]
    assert "Sara Nilsson" in res_anmalan["document_template_text"]

    # 6. Begäran om förhandling 32 § LAS
    res_forhandling = get_hr_document_template(
        template_type="begaran_forhandling_32_las",
        company_name="Svenska AB",
        union_name="Unionen Klubben"
    )
    assert "32 §" in res_forhandling["legal_basis"]
    assert "FÖRHANDLING ENLIGT 32 §" in res_forhandling["document_template_text"]

    # 7. Underrättelse tidsbegränsad 28 § LAS
    res_tidsbegr = get_hr_document_template(
        template_type="underrattelse_tidsbegransad_28_las",
        company_name="Svenska AB",
        employee_name="Lars Olofsson"
    )
    assert "28 §" in res_tidsbegr["legal_basis"]
    assert "Lars Olofsson" in res_tidsbegr["document_template_text"]

    # 8. Uppsägningsbesked arbetsbrist (2 sidor med 10 § delgivningsregler)
    res_uppsagn = get_hr_document_template(
        template_type="uppsagningsbesked_arbetsbrist",
        company_name="Svenska AB",
        employee_name="Olof Lind"
    )
    assert "8–10 §§" in res_uppsagn["legal_basis"]
    assert "UPPSÄGNINGSBESKED PÅ GRUND AV ARBETSBRIST" in res_uppsagn["document_template_text"]
    assert "TALAN OM OGILTIGHET" in res_uppsagn["document_template_text"]
    assert "TALAN OM SKADESTÅND" in res_uppsagn["document_template_text"]
    assert "10 § LAS" in res_uppsagn["document_template_text"]

    # 9. Varsel om avskedande (Arbetsgivarverket / 30 §)
    res_avsked_varsel = get_hr_document_template(
        template_type="arbetsgivarverket_avskedande_varsel",
        company_name="Skatteverket",
        employee_name="Nils Nilsson",
        union_name="ST Inom Skatteverket"
    )
    assert "30 §" in res_avsked_varsel["legal_basis"]
    assert "VARSEL OM AVSKEDANDE" in res_avsked_varsel["document_template_text"]
    assert "Nils Nilsson" in res_avsked_varsel["document_template_text"]

    # 10. Besked om avskedande (Arbetsgivarverket / 18–19 §§)
    res_avsked_beslut = get_hr_document_template(
        template_type="arbetsgivarverket_avskedande_beslut",
        company_name="Trafikverket",
        employee_name="Per Persson"
    )
    assert "18–19 §§" in res_avsked_beslut["legal_basis"]
    assert "BESKED OM AVSKEDANDE" in res_avsked_beslut["document_template_text"]

    # 11. 69-årsregeln (32 a § LAS)
    res_69 = get_hr_document_template(
        template_type="arbetsgivarverket_69_ar_upphorande",
        company_name="Länsstyrelsen",
        employee_name="Gunilla Andersson"
    )
    assert "32 a" in res_69["legal_basis"]
    assert "69 ÅR" in res_69["document_template_text"]

    # 12. URA Utlandsstationering
    res_ura = get_hr_document_template(
        template_type="arbetsgivarverket_ura_kontrakt",
        company_name="Sida",
        employee_name="Carl Bildt"
    )
    assert "URA" in res_ura["legal_basis"]
    assert "UTLANDSKONTRAKT" in res_ura["document_template_text"]

def test_calculate_travel_deduction_and_mileage():
    from src.mcp_tools.tools import calculate_travel_deduction_and_mileage
    
    # 1. Egen bil 2026 (25 kr/mil, 15 000 kr självrisk, 2h tidsvinst)
    res_car_2026 = calculate_travel_deduction_and_mileage(
        transport_mode="egen_bil",
        distance_km_one_way=30.0,
        work_days_per_year=210,
        public_transit_time_minutes_roundtrip=180,
        car_time_minutes_roundtrip=50,
        tax_year=2026
    )
    assert res_car_2026["conditions_met"] is True
    assert res_car_2026["rate_per_mil_sek"] == 25.0
    assert res_car_2026["total_travel_cost_sek"] == 31500.0
    assert res_car_2026["threshold_deductible_floor_sek"] == 15000.0
    assert res_car_2026["deductible_amount_sek"] == 16500.0
    assert res_car_2026["estimated_tax_savings_sek"] == 5280.0

    # 2. Förmånsbil Elbil 2025 (9.50 kr/mil, 11 000 kr självrisk)
    res_el_2025 = calculate_travel_deduction_and_mileage(
        transport_mode="formansbil_el",
        distance_km_one_way=40.0,
        work_days_per_year=210,
        public_transit_time_minutes_roundtrip=200,
        car_time_minutes_roundtrip=60,
        tax_year=2025
    )
    assert res_el_2025["rate_per_mil_sek"] == 9.50
    assert res_el_2025["threshold_deductible_floor_sek"] == 11000.0
    assert res_el_2025["deductible_amount_sek"] == 4960.0

    # 3. Cykel schablon 350 kr
    res_bike = calculate_travel_deduction_and_mileage(
        transport_mode="cykel",
        tax_year=2026
    )
    assert res_bike["total_travel_cost_sek"] == 350.0
    assert res_bike["deductible_amount_sek"] == 0.0

def test_get_base_amounts_and_indices():
    from src.mcp_tools.tools import get_base_amounts_and_indices
    
    # 2026
    res_2026 = get_base_amounts_and_indices(year=2026)
    assert res_2026["data"]["prisbasbelopp"] == 59200
    assert res_2026["data"]["forhojt_prisbasbelopp"] == 60500
    assert res_2026["data"]["inkomstbasbelopp"] == 83400
    assert res_2026["data"]["inkomstindex"] == 228.08
    assert res_2026["data"]["sgi_tak"] == 592000
    assert res_2026["data"]["max_pgi_manad"] == 56050

    # Compare all years
    res_all = get_base_amounts_and_indices(compare_all_years=True)
    assert len(res_all["historik"]) >= 5
    assert res_all["senaste_ar"] == 2026

def test_expanded_ad_case_law():
    from src.mcp_tools.tools import search_case_law
    
    # Sökning efter LAS 18 § grov misskötsamhet / avskedande
    cases_avsked = search_case_law(query="avskedande illojalitet konkurrens", limit=5)
    assert len(cases_avsked) > 0
    assert any("AD 2022 nr 12" in c["case_number"] or "AD 2003 nr 24" in c["case_number"] for c in cases_avsked)

    # Sökning efter 29/29-principen / arbetsvägran
    cases_29 = search_case_law(query="29/29-principen arbetsskyldighet arbetsvägran", limit=5)
    assert len(cases_29) > 0
    assert any("AD 1994 nr 101" in c["case_number"] or "AD 2021 nr 41" in c["case_number"] for c in cases_29)









