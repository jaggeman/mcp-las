"""Skydd för /api/request-key — det enda publika endpointet som skriver utan nyckel.

Fälten går både till Firestore och in i ett mejl till administratören. Utan
escaping renderas inskickad markup i mottagarens e-postklient; utan tak kan en
loop fylla databasen och mejlbomba samma mottagare.
"""

import json
from types import SimpleNamespace

import pytest

from src.db.auth_service import auth_service
from src.server import handle_key_request
from src.services.notification_service import notification_service


class FakeRequest:
    def __init__(self, body, ip="203.0.113.7", method="POST"):
        self.method = method
        self.headers = {"x-forwarded-for": ip}
        self.client = SimpleNamespace(host=ip)
        self._body = body

    async def json(self):
        return self._body


async def _post(body, ip="203.0.113.7"):
    resp = await handle_key_request(FakeRequest(body, ip=ip))
    return resp.status_code, json.loads(bytes(resp.body).decode())


def _giltig(**extra):
    bas = {"name": "Anna Andersson", "email": "anna@example.se",
           "company": "Exempel AB", "reason": "Vill testa", "legal_accept": True}
    bas.update(extra)
    return bas


@pytest.mark.asyncio
async def test_villkor_maste_accepteras_explicit():
    status, payload = await _post(_giltig(legal_accept=False), ip="198.51.100.17")
    assert status == 400
    assert "villkor" in payload["message"].lower()


@pytest.fixture(autouse=True)
def _tyst_notis(monkeypatch):
    monkeypatch.setattr(notification_service, "send_key_request_notification", lambda r: True)


def test_inskickad_markup_escapas_i_den_riktiga_mejl_htmlen(monkeypatch):
    """Fångar mejlet som faktiskt byggs, inte en omskrivning av escapingen."""
    import smtplib
    import src.services.notification_service as ns

    skickat = {}

    class FejkSMTP:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, *a, **kw): pass
        def login(self, *a, **kw): pass
        def sendmail(self, avsandare, mottagare, meddelande):
            skickat["raw"] = meddelande

    monkeypatch.setattr(smtplib, "SMTP", FejkSMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FejkSMTP)
    tjanst = ns.NotificationService()
    monkeypatch.setattr(tjanst, "smtp_user", "avsandare@example.se")
    monkeypatch.setattr(tjanst, "smtp_pass", "hemlis")

    tjanst.send_key_request_notification({
        "name": '<script>alert(1)</script>',
        "email": 'ond" onmouseover="alert(2)',
        "company": "Exempel AB",
        "reason": '<img src=x onerror="alert(3)">',
        "created_at": "2026-09-14",
    })

    raw = skickat.get("raw", "")
    assert raw, "inget mejl byggdes"

    # Delarna granskas var för sig: bara HTML-delen renderas som markup.
    import email as emaillib
    msg = emaillib.message_from_string(raw)
    delar = {}
    for del_ in msg.walk():
        nyttolast = del_.get_payload(decode=True)
        if nyttolast:
            delar[del_.get_content_type()] = nyttolast.decode("utf-8", "replace")

    html_del = delar["text/html"]
    # Inget av det inskickade får överleva som körbar markup i HTML-delen
    assert "<script>" not in html_del
    assert "<img src=x" not in html_del
    # Citattecknet måste vara escapat, annars bryter det sig ur href="mailto:..."
    assert 'onmouseover="' not in html_del
    assert "&quot; onmouseover=&quot;" in html_del
    # ...men innehållet ska fortfarande vara läsbart för mottagaren
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_del

    # Klartextdelen ska däremot ha råvärdena - den renderas inte som markup,
    # och escapade entiteter där vore bara svårlästa.
    text_del = delar["text/plain"]
    assert "<script>alert(1)</script>" in text_del


@pytest.mark.asyncio
async def test_for_langt_falt_avvisas():
    status, payload = await _post(_giltig(reason="x" * 5000), ip="198.51.100.1")
    assert status == 400
    assert "reason" in payload["message"]


@pytest.mark.asyncio
async def test_rate_limit_stoppar_en_loop():
    ip = "198.51.100.42"
    auth_service.check_rate_limit(f"key-request:{ip}", max_requests=5, window_seconds=600)
    koder = [(await _post(_giltig(), ip=ip))[0] for _ in range(8)]
    assert 429 in koder, f"ingen begränsning slog till: {koder}"


@pytest.mark.asyncio
async def test_rate_limit_ar_per_ip_inte_global():
    """En avsändare får inte kunna stänga formuläret för alla andra."""
    for _ in range(8):
        await _post(_giltig(), ip="198.51.100.99")
    status, _ = await _post(_giltig(), ip="203.0.113.200")
    assert status == 200, "en annan IP ska inte påverkas av grannens gräns"


@pytest.mark.asyncio
async def test_internt_fel_avslojar_inget():
    class Trasig(FakeRequest):
        async def json(self):
            raise RuntimeError("Firestore projects/paygap-prod nekade /srv/key.json")

    resp = await handle_key_request(Trasig(None, ip="203.0.113.55"))
    payload = json.loads(bytes(resp.body).decode())
    assert resp.status_code == 500
    text = json.dumps(payload)
    assert "paygap-prod" not in text and "/srv/key.json" not in text
