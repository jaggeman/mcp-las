from threading import RLock

import pytest

from src.db.firebase_client import FirebaseLaborLawDB
from src.mcp_tools.tools import (
    calculate_redundancy_turnorder_and_exceptions,
    generate_turordningslista_excel,
)


def employee(**changes):
    row = {
        "name": "Anna Andersson", "title": "Utvecklare",
        "driftsenhet": "Stockholm", "avtalsomrade": "Tjänstemän",
        "start_date": "2020-01-01", "birth_date": "1990-01-01",
        "has_qualifications": True, "is_exempt": False,
    }
    row.update(changes)
    return row


@pytest.mark.parametrize("field,value", [
    ("start_date", "inte-ett-datum"),
    ("birth_date", "2025-99-99"),
    ("start_date", "2099-01-01"),
    ("birth_date", "2099-01-01"),
])
def test_excel_rejects_invalid_or_future_employee_dates(field, value):
    result = generate_turordningslista_excel(employees=[employee(**{field: value})])
    assert result["success"] is False
    assert field in result["error"]


def test_excel_rejects_invalid_as_of_date():
    result = generate_turordningslista_excel(
        employees=[employee()], as_of_date="2026-99-99")
    assert result["success"] is False
    assert "as_of_date" in result["error"]


@pytest.mark.parametrize("count", [-1, 2, "1", True])
def test_excel_rejects_invalid_redundancy_count(count):
    result = generate_turordningslista_excel(
        employees=[employee()], redundancy_count=count)
    assert result["success"] is False
    assert "redundancy_count" in result["error"]


@pytest.mark.parametrize("field", ["has_qualifications", "is_exempt"])
def test_excel_rejects_string_booleans(field):
    result = generate_turordningslista_excel(
        employees=[employee(**{field: "false"})])
    assert result["success"] is False
    assert field in result["error"]


def test_excel_enforces_three_or_four_exemptions():
    four = [employee(name=f"Person {n}", is_exempt=True) for n in range(4)]
    assert generate_turordningslista_excel(employees=four)["success"] is False
    assert generate_turordningslista_excel(
        employees=four, single_operating_unit=True)["success"] is True
    assert generate_turordningslista_excel(
        employees=four, single_operating_unit=True, cba_name=None)["success"] is False
    five = four + [employee(name="Person 5", is_exempt=True)]
    assert generate_turordningslista_excel(
        employees=five, single_operating_unit=True)["success"] is False


def test_excel_breaks_equal_seniority_by_exact_birth_date():
    result = generate_turordningslista_excel(employees=[
        employee(name="Yngre", birth_date="1990-12-31"),
        employee(name="Äldre", birth_date="1990-01-01"),
    ])
    rows = [line for line in result["markdown_table"].splitlines()
            if line.startswith("| `EMP-")]
    assert "Äldre" in rows[0]


def test_excel_rejects_illegal_xml_control_characters():
    result = generate_turordningslista_excel(
        employees=[employee(name="Anna\x00Andersson")])
    assert result["success"] is False
    assert "kontrolltecken" in result["error"]


def test_markdown_cells_cannot_create_rows_or_columns():
    result = generate_turordningslista_excel(employees=[employee(
        name="Anna | ny kolumn\n| falsk rad", title="**chef**")])
    assert result["success"] is True
    assert len(result["markdown_table"].splitlines()) == 6
    data_line = result["markdown_table"].splitlines()[-1]
    assert "\\|" in data_line and "<br>" in data_line
    assert "\\*\\*chef\\*\\*" in data_line


@pytest.mark.parametrize("kwargs", [
    {"total_employees_in_unit": -1, "redundancy_count": 0},
    {"total_employees_in_unit": 2, "redundancy_count": 3},
    {"total_employees_in_unit": 2, "redundancy_count": "1"},
    {"contract_areas_count": 0},
])
def test_redundancy_calculator_rejects_impossible_counts(kwargs):
    with pytest.raises(ValueError):
        calculate_redundancy_turnorder_and_exceptions(**kwargs)


def test_redundancy_calculator_disables_cba_options_without_cba():
    result = calculate_redundancy_turnorder_and_exceptions(
        total_employees_in_unit=20, redundancy_count=3,
        has_collective_bargaining_agreement=False)
    alternatives = result["exemption_rules"]["cba_exemption_alternatives"]
    assert all(option["is_applicable"] is False for option in alternatives.values())


def test_rate_limit_message_reports_the_actual_key_quota(monkeypatch):
    from src import server
    monkeypatch.setattr(server.auth_service, "validate_key", lambda _: {"is_active": True})
    monkeypatch.setattr(server.auth_service, "check_rate_limit", lambda *args, **kwargs: False)
    assert "300" in server._check_rate_limit("valid-key")["error"]
    assert "60" in server._check_rate_limit()["error"]


def _search_db(rows):
    db = FirebaseLaborLawDB.__new__(FirebaseLaborLawDB)
    db.db = None
    db._local_sections = {row["id"]: row for row in rows}
    db._cached_statute_sections = None
    db._cached_statute_sections_by_country = {}
    db._country_cache_at = {}
    db._statute_cache_lock = RLock()
    return db


def _section(id_, statute, section, content, chapter=None):
    return {
        "id": id_, "statute_short": statute, "statute_id": id_.split(":")[0],
        "section_number": section, "chapter": chapter, "section_title": "",
        "content": content, "raw_text": content, "keywords": [],
        "embedding": [], "jurisdiction": "SE", "language": "sv",
    }


@pytest.mark.parametrize("question,expected,rows", [
    ("Vad är skillnaden mellan uppsägning och avskedande?", ("LAS", None, "18"), [
        _section("1982-80:18", "LAS", "18", "Avskedande får ske om arbetstagaren grovt åsidosatt sina åligganden."),
        _section("2008-567:8", "Diskrimineringslagen", "8", "Ett avgörande om uppsägning eller avskedande." , "6"),
    ]),
    ("Vilka är diskrimineringsgrunderna?", ("Diskrimineringslagen", "1", "5"), [
        _section("2008-567:5", "Diskrimineringslagen", "5", "Diskrimineringsgrunder är kön, könsöverskridande identitet, etnisk tillhörighet, religion, funktionsnedsättning, sexuell läggning och ålder.", "1"),
        _section("2008-567:2", "Diskrimineringslagen", "2", "Förbud mot diskriminering med undantag.", "2"),
    ]),
    ("Har man rätt till rast under arbetsdagen?", ("Arbetstidslagen", None, "15"), [
        _section("1982-673:15", "Arbetstidslagen", "15", "Arbetstagarna ska ha raster under arbetsdagen."),
        _section("1982-673:17", "Arbetstidslagen", "17", "Arbetsgivaren ska ordna arbetet så att arbetstagarna kan ta pauser."),
    ]),
    ("Hur många semesterdagar har jag rätt till per år?", ("Semesterlagen", None, "4"), [
        _section("1977-480:4", "Semesterlagen", "4", "En arbetstagare har rätt till tjugofem semesterdagar varje semesterår."),
        _section("1977-480:19", "Semesterlagen", "19", "En arbetstagare får spara betalda semesterdagar."),
    ]),
])
def test_common_questions_rank_the_governing_section_first(question, expected, rows):
    result = _search_db(rows).search_statute_sections(
        question, filters={"jurisdiction": "SE"}, limit=2)
    assert (result[0]["statute"], result[0]["chapter"], result[0]["section"]) == expected
