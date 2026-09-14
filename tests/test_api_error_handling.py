"""Felhantering i det publika verktygs-endpointet /api/tools/{tool_name}.

Anroparens misstag gav tidigare 500 med det rå Python-felet i svaret. Det är
fel på två sätt: statuskoden pekar ut servern för något anroparen gjort, och
`str(e)` går ut till en publik API-konsument. Samma except fångar fel från
Firestore, embedder och nätverkslager, vars texter kan innehålla projekt-id
och sökvägar.
"""

import json

import pytest

from src.db.auth_service import auth_service
from src.server import execute_tool_direct_rest


class FakeRequest:
    """Minimal Starlette-lik request — routen läser bara dessa fyra saker."""

    def __init__(self, tool_name, body, method="POST"):
        self.method = method
        self.path_params = {"tool_name": tool_name}
        self.headers = {"X-API-Key": "test-key"}
        self._body = body

    async def json(self):
        return self._body


@pytest.fixture(autouse=True)
def _authenticated(monkeypatch):
    """Endpointet kräver giltig nyckel; auth är inte det som testas här."""
    monkeypatch.setattr(auth_service, "validate_key", lambda k: {"name": "Test"})
    monkeypatch.setattr(auth_service, "log_access", lambda *a, **kw: None)


async def _call(tool_name, body):
    resp = await execute_tool_direct_rest(FakeRequest(tool_name, body))
    return resp.status_code, json.loads(bytes(resp.body).decode())


@pytest.mark.asyncio
async def test_unknown_parameter_is_a_client_error_not_a_server_error():
    status, payload = await _call("calculate_vacation_pay", {"manadslon": 30000})
    assert status == 400, "ett stavfel hos anroparen är inte ett serverfel"
    assert "manadslon" in payload["error"]
    # Svaret ska vara användbart: vilka parametrar finns?
    assert "monthly_salary" in payload["valid_parameters"]


@pytest.mark.asyncio
async def test_wrong_type_gives_400_without_leaking_the_python_error():
    status, payload = await _call("calculate_vacation_pay", {"monthly_salary": "trettiotusen"})
    assert status == 400
    # Det råa felet lyder "'<=' not supported between instances of 'str' and
    # 'int'" — obegripligt för anroparen och en läcka. Det får inte gå ut.
    assert "not supported between instances" not in json.dumps(payload)
    assert "monthly_salary" in payload["valid_parameters"]


@pytest.mark.asyncio
async def test_internal_failure_reports_nothing_about_internals():
    """Ett genuint serverfel ska ge 500 utan att avslöja vad som gick fel."""
    import src.server as server

    trasigt = lambda **kw: (_ for _ in ()).throw(
        RuntimeError("Firestore projects/paygap-prod saknar behörighet /srv/key.json")
    )
    original = server.DIRECT_TOOLS_MAP.get("calculate_vacation_pay")
    server.DIRECT_TOOLS_MAP["calculate_vacation_pay"] = trasigt
    try:
        status, payload = await _call("calculate_vacation_pay", {})
    finally:
        server.DIRECT_TOOLS_MAP["calculate_vacation_pay"] = original

    assert status == 500
    text = json.dumps(payload)
    assert "paygap-prod" not in text
    assert "/srv/key.json" not in text


@pytest.mark.asyncio
async def test_valid_call_still_works():
    status, payload = await _call("calculate_vacation_pay", {"monthly_salary": 30000})
    assert status == 200
    assert payload["success"] is True
    # Semesterlagen 16 b §: 0,43 % per dag -> 30000 * 0.0043 * 25
    assert payload["result"]["without_collective_agreement_statute"]["fixed_supplement_kr"] == 3225
