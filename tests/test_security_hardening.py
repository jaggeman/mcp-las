"""Regression tests for bearer secrets, request retention and transport auth."""

import hashlib
import inspect
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def test_api_key_lookup_uses_only_a_sha256_document_id(monkeypatch):
    from src.config import settings
    from src.db import auth_service as module

    requested = []
    key = "las_live_" + "A" * 43
    digest = hashlib.sha256(key.encode()).hexdigest()
    document = SimpleNamespace(
        exists=True,
        to_dict=lambda: {"name": "Test", "is_active": True, "key_digest": digest},
    )
    database = SimpleNamespace(
        collection=lambda name: SimpleNamespace(
            document=lambda document_id: requested.append((name, document_id)) or SimpleNamespace(get=lambda: document)
        )
    )
    monkeypatch.setattr(module.db_client, "db", database)
    monkeypatch.setattr(settings, "MASTER_ADMIN_KEY", None)

    assert module.AuthService().validate_key(key)["name"] == "Test"
    assert requested == [("api_keys", digest)]
    assert key not in repr(requested)


def test_new_keys_have_256_bits_and_are_stored_without_the_secret():
    from scripts.manage_keys import build_key_record, generate_api_key

    key = generate_api_key()
    document_id, record = build_key_record(key, "Test")

    assert key.startswith("las_live_")
    assert len(key.removeprefix("las_live_")) >= 43
    assert document_id == hashlib.sha256(key.encode()).hexdigest()
    assert key not in repr(record)
    assert "key" not in record


@pytest.mark.asyncio
async def test_request_key_records_receive_a_ninety_day_expiry(monkeypatch):
    from src import server

    captured = []
    reference = SimpleNamespace(set=captured.append)
    database = SimpleNamespace(collection=lambda _: SimpleNamespace(document=lambda: reference))
    monkeypatch.setattr(server.db_client, "db", database)
    monkeypatch.setattr(server.auth_service, "check_rate_limit", lambda *args, **kwargs: True)
    monkeypatch.setattr(server.notification_service, "send_key_request_notification", lambda _: True)

    async def body():
        return {"name": "Test", "email": "test@example.invalid", "company": "AB", "reason": "Test"}

    request = SimpleNamespace(method="POST", client=SimpleNamespace(host="192.0.2.1"), json=body)
    response = await server.handle_key_request(request)

    assert response.status_code == 200
    expiry = captured[0]["expires_at"]
    assert expiry.tzinfo is not None
    assert 89 <= (expiry - datetime.now(timezone.utc)).days <= 90


def test_notification_logs_never_contain_applicant_email(monkeypatch):
    from src.services.notification_service import NotificationService

    warning = Mock()
    monkeypatch.setattr("src.services.notification_service.logger.warning", warning)
    service = NotificationService()
    service.smtp_user = ""
    service.smtp_pass = ""

    service.send_key_request_notification({
        "name": "Test", "email": "private@example.invalid", "company": "AB", "reason": "Test"
    })

    assert "private@example.invalid" not in repr(warning.call_args)


def test_mcp_tools_do_not_expose_api_keys_as_model_arguments():
    from src import server

    for name in server.DIRECT_TOOLS_MAP:
        function = getattr(server, name)
        assert "api_key" not in inspect.signature(function).parameters, name


@pytest.mark.asyncio
async def test_header_key_is_available_during_asgi_request():
    from src.services.request_context import current_api_key
    from src.services.request_limits import RequestSizeLimit

    observed = []

    async def app(scope, receive, send):
        observed.append(current_api_key())

    middleware = RequestSizeLimit(app)
    scope = {
        "type": "http", "method": "GET", "path": "/",
        "headers": [(b"x-api-key", b"transport-secret")],
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        pass

    await middleware(scope, receive, send)
    assert observed == ["transport-secret"]
    assert current_api_key() is None
