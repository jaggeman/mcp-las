"""/health — vilken kod kör faktiskt i produktion?

Bakgrunden är en hel dags felsökning som inte borde ha behövts. Testsviten var
grön, GitHub Actions rapporterade lyckad deploy, och ändå svarade den publika
servern med text som rättats dagen innan. Ingenting i tjänsten kunde svara på
frågan "vilket commit kör du?", så frågan fick besvaras med arkeologi:
deployloggar, revisionslistor och git-historik.

Endpointet finns för att göra den frågan till ett anrop. Det läser inget från
Firestore — ett health-anrop ska vara billigt nog att pollas — och det lämnar
inte ut projekt-id eller sökvägar, av samma skäl som felsvaren i #30 slutade
göra det.
"""

import json
import os

import pytest

from src.server import health_check


class FakeRequest:
    def __init__(self, method="GET"):
        self.method = method
        self.headers = {}


async def _call(method="GET"):
    resp = await health_check(FakeRequest(method))
    if method == "OPTIONS":
        return resp.status_code, None
    return resp.status_code, json.loads(bytes(resp.body).decode())


@pytest.mark.asyncio
async def test_reports_the_running_commit(monkeypatch):
    monkeypatch.setenv("BUILD_SHA", "98b9878c85dc6f46871a707e5bcdec6bd8669d30")
    status, payload = await _call()
    assert status == 200
    # Hela sha:n, inte en förkortning: den ska kunna jämföras rakt av mot
    # `git rev-parse HEAD` utan att någon behöver klippa i den.
    assert payload["build_sha"] == "98b9878c85dc6f46871a707e5bcdec6bd8669d30"


@pytest.mark.asyncio
async def test_says_unknown_rather_than_lying_when_the_build_is_unstamped(monkeypatch):
    """En image byggd utanför CI har ingen sha. Då ska svaret säga det.

    Alternativet — att utelämna fältet, eller fylla det med något som ser ut
    som en sha — gör endpointet sämre än värdelöst: det är då man litar på det
    som mest.
    """
    monkeypatch.delenv("BUILD_SHA", raising=False)
    status, payload = await _call()
    assert status == 200
    assert payload["build_sha"] == "unknown"


@pytest.mark.asyncio
async def test_reports_whether_the_database_is_connected(monkeypatch):
    """Tom databas har varit sessionens genomgående problem.

    Det här skiljer inte tom från fylld — det kräver en läsning, och health
    ska vara billig — men det skiljer "ingen klient alls" från "klient finns",
    vilket är den vanligaste orsaken till att ingestionen skriver i tomma
    luften.
    """
    from src.db import firebase_client

    monkeypatch.setattr(firebase_client.db_client, "db", None)
    _, payload = await _call()
    assert payload["database_connected"] is False

    monkeypatch.setattr(firebase_client.db_client, "db", object())
    _, payload = await _call()
    assert payload["database_connected"] is True


@pytest.mark.asyncio
async def test_does_not_leak_project_id_or_paths():
    """Samma gräns som felsvaren i #30 drar.

    Endpointet är publikt och oautentiserat — det måste vara det för att kunna
    användas som uppstartskontroll — så det ska inte berätta mer om miljön än
    vilken kod som kör.
    """
    _, payload = await _call()
    body = json.dumps(payload)
    assert "paygap-prod" not in body
    assert "/app" not in body
    assert "credentials" not in body.lower()


@pytest.mark.asyncio
async def test_counts_the_registered_tools():
    """Antalet verktyg avslöjar en halvfärdig deploy som sha:n inte hinner med.

    Ett nytt verktyg som registrerats i tools.py men inte i DIRECT_TOOLS_MAP
    ger rätt sha och fel antal.
    """
    _, payload = await _call()
    from src.server import DIRECT_TOOLS_MAP

    assert payload["tool_count"] == len(DIRECT_TOOLS_MAP)
    assert payload["tool_count"] > 0


@pytest.mark.asyncio
async def test_options_preflight_is_answered():
    status, _ = await _call("OPTIONS")
    assert status == 200
