from pathlib import Path

import pytest

from src.mcp_tools.tools import (
    calculate_redundancy_turnorder_and_exceptions,
    generate_turordningslista_excel,
    get_hr_document_template,
)


def test_turnorder_tool_returns_complete_redundancy_workflow():
    result = calculate_redundancy_turnorder_and_exceptions(
        total_employees_in_unit=40,
        redundancy_count=8,
    )

    phases = result["redundancy_process_guide"]
    assert list(phases) == [
        "1_planera_forandringen",
        "2_riskbedom_arbetsmiljon",
        "3_varsla_arbetsformedlingen",
        "4_forhandla_mbl",
        "5_utred_omplacering",
        "6_faststall_turordning",
        "7_fatta_beslut_och_lamna_besked",
        "8_omstallning_och_foretradesratt",
    ]
    assert phases["2_riskbedom_arbetsmiljon"]["must_be_written"] is True
    assert "innan förändringen genomförs" in phases["2_riskbedom_arbetsmiljon"]["timing"]
    assert phases["3_varsla_arbetsformedlingen"]["threshold"] == "Minst 5 berörda i samma län"
    assert phases["4_forhandla_mbl"]["decision_gate"] == "Fatta inte beslut innan förhandlingsskyldigheten är fullgjord"
    assert "lediga arbeten" in phases["5_utred_omplacering"]["actions"][0]
    assert phases["6_faststall_turordning"]["template_types"] == ["turordningslista_excel"]

    notice = result["arbetsformedlingen_notice_guide"]
    assert notice["permanent_employees"] == {
        "5–25": "Minst 2 månader",
        "26–100": "Minst 4 månader",
        "fler än 100": "Minst 6 månader",
    }
    assert notice["fixed_term_ended_early"] == "Minst 6 veckor"
    assert notice["person_list_deadline"] == "Senast 1 månad före den första sista anställningsdagen"
    assert notice["rolling_ninety_day_rule"] == "Minst 20 uppsägningar sammanlagt under 90 dagar"


def test_turnorder_is_scoped_to_legal_employer_and_does_not_assume_a_cba():
    result = calculate_redundancy_turnorder_and_exceptions(
        legal_employer_name="Exempelbolaget AB",
        organization_number="556000-0000",
        total_employees_in_unit=12,
        redundancy_count=2,
    )

    assert result["employer_scope"] == {
        "legal_employer_name": "Exempelbolaget AB",
        "organization_number": "556000-0000",
        "statutory_scope": "Samma juridiska eller fysiska arbetsgivare som är part i anställningsavtalet",
        "group_companies_included_by_default": False,
    }
    alternatives = result["exemption_rules"]["cba_exemption_alternatives"]
    assert all(option["is_applicable"] is False for option in alternatives.values())
    assert "22 § LAS" in result["exemption_rules"]["recommendation_summary"]


def test_exempt_employee_is_removed_before_preliminary_layoff_cutoff():
    employees = [
        {"name": "A", "seniority_days": 500, "age": 50},
        {"name": "B", "seniority_days": 400, "age": 45},
        {"name": "C", "seniority_days": 300, "age": 40},
        {"name": "D", "seniority_days": 200, "age": 35},
        {"name": "E", "seniority_days": 100, "age": 30, "is_exempt": True},
    ]

    result = calculate_redundancy_turnorder_and_exceptions(
        redundancy_count=2,
        employees_list=employees,
    )
    statuses = {row["name"]: row["status_code"] for row in result["sorted_turordningslista"]}
    assert statuses["E"] == "EXEMPT"
    assert {name for name, status in statuses.items() if status == "PRELIMINARY_AT_RISK"} == {"C", "D"}
    assert result["decision_status"] == "preliminary_seniority_order_only"


def test_cba_exemptions_require_identified_and_confirmed_agreement_rules():
    unconfirmed = calculate_redundancy_turnorder_and_exceptions(
        total_employees_in_unit=100,
        redundancy_count=20,
        has_collective_bargaining_agreement=True,
        collective_agreement_name="Unionen tjänstemannaavtal",
    )
    assert not any(
        option["is_applicable"]
        for option in unconfirmed["exemption_rules"]["cba_exemption_alternatives"].values()
    )

    confirmed = calculate_redundancy_turnorder_and_exceptions(
        total_employees_in_unit=100,
        redundancy_count=20,
        has_collective_bargaining_agreement=True,
        collective_agreement_name="Unionen tjänstemannaavtal",
        collective_agreement_rules_confirmed=True,
    )
    assert confirmed["exemption_rules"]["cba_exemption_alternatives"]["alternativ_1"]["is_applicable"] is True


def test_redundancy_specific_templates_cover_the_process_documents():
    cases = {
        "riskbedomning_organisationsforandring": (
            "SKRIFTLIG RISKBEDÖMNING",
            ("sannolikhet", "konsekvens", "åtgärd", "AFS 2023:1"),
        ),
        "mbl_forhandlingsframstallan_arbetsbrist": (
            "FÖRHANDLINGSFRAMSTÄLLAN",
            ("11–15 §§ MBL", "skälen till de planerade uppsägningarna", "Arbetsförmedlingen"),
        ),
        "forhandlingsprotokoll_arbetsbrist": (
            "FÖRHANDLINGSPROTOKOLL",
            ("justeras", "oense", "förhandlingen avslutades"),
        ),
        "varsel_arbetsformedlingen": (
            "UNDERLAG INFÖR VARSELANMÄLAN",
            ("5–25", "26–100", "fler än 100", "officiella e-tjänst"),
        ),
        "arbetsbrist_processchecklista": (
            "PROCESSCHECKLISTA VID ARBETSBRIST",
            ("Riskbedömning", "MBL-förhandling", "Omplaceringsutredning", "Turordning"),
        ),
    }

    for template_type, (heading, required_texts) in cases.items():
        result = get_hr_document_template(
            template_type=template_type,
            company_name="Exempelbolaget AB",
            workplace_location="Stockholm",
            union_name="Unionenklubben",
        )
        text = result["document_template_text"]
        assert heading in text
        assert "Exempelbolaget AB" in text
        for required in required_texts:
            assert required.lower() in text.lower()
        assert result["official_source_urls"]
        assert all(url.startswith("https://") for url in result["official_source_urls"])


def test_redundancy_templates_distinguish_legal_employer_vacancies_and_mbl_gates():
    investigation = get_hr_document_template(
        template_type="omplaceringsutredning",
        company_name="Exempelbolaget AB",
        organization_number="556000-0000",
    )["document_template_text"]
    for phrase in (
        "Legal arbetsgivare",
        "556000-0000",
        "samma legala arbetsgivare",
        "pågående rekrytering",
        "rimlig upplärningstid",
        "andra koncernbolag ingår inte automatiskt",
    ):
        assert phrase.lower() in investigation.lower()

    mbl = get_hr_document_template(
        template_type="mbl_forhandlingsframstallan_arbetsbrist",
        company_name="Exempelbolaget AB",
        organization_number="556000-0000",
    )["document_template_text"]
    assert "samtliga berörda arbetstagarorganisationer" in mbl
    assert "central förhandling" in mbl
    assert "materiellt ändras" in mbl

    offer = get_hr_document_template(
        template_type="omplaceringserbjudande",
        company_name="Exempelbolaget AB",
    )["document_template_text"]
    assert "arbetsgivaren bedömer" in offer.lower()
    assert "tackar nej" in offer.lower()
    assert "7 a–7 b §§ LAS" in offer


def test_unknown_template_type_fails_closed():
    with pytest.raises(ValueError, match="Okänd template_type"):
        get_hr_document_template("riskbedomning_organisationsforandrin")


def test_excel_turnorder_is_preliminary_and_excludes_exempt_people_from_cutoff():
    employees = [
        {"name": "A", "start_date": "2015-01-01", "birth_date": "1975-01-01"},
        {"name": "B", "start_date": "2016-01-01", "birth_date": "1980-01-01"},
        {"name": "C", "start_date": "2017-01-01", "birth_date": "1985-01-01"},
        {"name": "D", "start_date": "2018-01-01", "birth_date": "1990-01-01"},
        {"name": "E", "start_date": "2019-01-01", "birth_date": "1995-01-01", "is_exempt": True},
    ]

    result = generate_turordningslista_excel(
        company_name="Exempelbolaget AB",
        organization_number="556000-0000",
        employees=employees,
        redundancy_count=2,
        as_of_date="2026-01-01",
    )

    assert result["success"] is True
    assert result["decision_status"] == "preliminary_seniority_order_only"
    assert result["markdown_table"].count("Preliminär risk för uppsägning") == 2
    assert "556000-0000" in result["markdown_table"]
    assert "Inget verifierat kollektivavtal" in result["markdown_table"]


def test_website_explains_redundancy_workflow_and_available_templates():
    html = Path("public/index.html").read_text(encoding="utf-8")
    app = Path("public/app.js").read_text(encoding="utf-8")
    combined = html + app

    assert 'id="arbetsbrist-process"' in html
    for phrase in (
        "Arbetsbrist och turordning – steg för steg",
        "Riskbedömning före förändringen",
        "Varsel till Arbetsförmedlingen",
        "MBL-förhandling före beslut",
        "Omplaceringsutredning",
        "Turordning och uppsägningsbesked",
        "riskbedomning_organisationsforandring",
        "mbl_forhandlingsframstallan_arbetsbrist",
        "forhandlingsprotokoll_arbetsbrist",
        "varsel_arbetsformedlingen",
        "arbetsbrist_processchecklista",
        "Legal arbetsgivare och öppna roller",
        "andra koncernbolag ingår inte automatiskt",
        "20 uppsägningar under 90 dagar",
        "23 § LAS",
    ):
        assert phrase in combined

