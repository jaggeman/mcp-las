from pathlib import Path

from src.mcp_tools.tools import (
    calculate_redundancy_turnorder_and_exceptions,
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
    ):
        assert phrase in combined

