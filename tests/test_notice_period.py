"""Uppsägningstid enligt LAS 11 §.

Trappan i andra stycket är en RÄTTIGHET för arbetstagaren när arbetsgivaren
säger upp. Den gäller inte åt andra hållet: säger arbetstagaren upp sig själv
är det en månad enligt första stycket, oavsett anställningstid. Det är den
vanligaste felkällan i den här beräkningen, och den har ett eget test.
"""

import json
import re

import pytest

from src.mcp_tools.tools import calculate_notice_period


# LAS 11 § andra stycket, ordagrant: minst två men kortare än fyra år ger två
# månader, minst fyra men kortare än sex ger tre, och så vidare.
@pytest.mark.parametrize("ar,forvantat", [
    (0, 1), (0.5, 1), (1.99, 1),          # under två år: grundregeln
    (2, 2), (3.99, 2),                     # minst två, kortare än fyra
    (4, 3), (5.99, 3),                     # minst fyra, kortare än sex
    (6, 4), (7.99, 4),                     # minst sex, kortare än åtta
    (8, 5), (9.99, 5),                     # minst åtta, kortare än tio
    (10, 6), (25, 6), (40, 6),             # minst tio år
])
def test_trappan_enligt_las_11_andra_stycket(ar, forvantat):
    res = calculate_notice_period(employment_years=ar)
    assert res["result"]["notice_period_months"] == forvantat


@pytest.mark.parametrize("ar", [0, 2, 5, 10, 30])
def test_egen_uppsagning_ar_alltid_en_manad(ar):
    """Trappan gäller inte när arbetstagaren själv säger upp sig."""
    res = calculate_notice_period(employment_years=ar, terminated_by="employee")
    assert res["result"]["notice_period_months"] == 1, (
        "förlängd uppsägningstid är arbetstagarens rättighet vid arbetsgivarens "
        "uppsägning, inte en skyldighet vid egen uppsägning"
    )


def test_svenska_parametervarden_fungerar():
    """Verktyget anropas av svensktalande agenter — acceptera båda formerna."""
    a = calculate_notice_period(employment_years=10, terminated_by="arbetsgivare")
    b = calculate_notice_period(employment_years=10, terminated_by="arbetstagare")
    assert a["result"]["notice_period_months"] == 6
    assert b["result"]["notice_period_months"] == 1


def test_kollektivavtalets_avvikelse_lyfts_fram():
    """LAS 11 § är semidispositiv — avtalet kan ge mer, och det ska synas."""
    res = calculate_notice_period(employment_years=12, agreement_name="Teknikavtalet")
    avvikelser = res["collective_agreement_deviations"]
    assert avvikelser, "Teknikavtalet har en LAS 11 §-regel som inte hittades"
    assert "12 månader" in avvikelser[0]["rule_content"]


def test_utan_avtal_pastas_ingen_avvikelse():
    res = calculate_notice_period(employment_years=12)
    assert res["collective_agreement_deviations"] == []


def test_ogiltig_indata_avvisas():
    assert "error" in calculate_notice_period(employment_years=-1)
    assert "error" in calculate_notice_period(employment_years=5, terminated_by="katten")


def test_las_3_och_semidispositiviteten_namns():
    """Ett svar som inte nämner dem inbjuder till fel i skarpt läge."""
    text = json.dumps(calculate_notice_period(employment_years=5), ensure_ascii=False)
    assert "3 §" in text, "anställningstiden beräknas enligt LAS 3 §"
    assert "2 §" in text, "semidispositiviteten måste framgå"


def test_inga_platshallare_i_texten():
    """Samma vakt som turordningsverktyget fick efter "(None st totalt)"."""
    trasiga = re.compile(r"\b(None|null|nan|undefined)\b")

    def strangar(nod):
        if isinstance(nod, str):
            yield nod
        elif isinstance(nod, dict):
            for v in nod.values():
                yield from strangar(v)
        elif isinstance(nod, (list, tuple)):
            for v in nod:
                yield from strangar(v)

    for kwargs in [{}, {"agreement_name": "Teknikavtalet"}, {"age": 70},
                   {"terminated_by": "employee"}]:
        svar = calculate_notice_period(employment_years=7, **kwargs)
        for text in strangar(svar):
            assert not trasiga.search(text), f"platshållare läckte med {kwargs}: {text!r}"


def test_hog_alder_ger_en_varning_men_ingen_gissning():
    """Verktyget tillämpar inte LAS 33 §§ — det säger det i stället."""
    res = calculate_notice_period(employment_years=20, age=70)
    noteringar = " ".join(res["notes"])
    assert "33" in noteringar
    assert "tillämpar dem inte" in noteringar


@pytest.mark.asyncio
async def test_verktyget_nas_via_api_endpointet():
    """Den rena funktionen kan vara rätt medan registreringen är fel."""
    from src.db.auth_service import auth_service
    from src.server import execute_tool_direct_rest

    class FakeRequest:
        method = "POST"
        headers = {"X-API-Key": "test"}
        path_params = {"tool_name": "calculate_notice_period"}

        async def json(self):
            return {"employment_years": 10}

    original = auth_service.validate_key
    auth_service.validate_key = lambda k: {"name": "Test"}
    try:
        resp = await execute_tool_direct_rest(FakeRequest())
    finally:
        auth_service.validate_key = original

    payload = json.loads(bytes(resp.body).decode())
    assert resp.status_code == 200
    assert payload["result"]["result"]["notice_period_months"] == 6
