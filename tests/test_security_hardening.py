"""Regression tests for bearer secrets, request retention and transport auth."""

import hmac
import inspect
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def test_api_key_lookup_uses_only_a_peppered_document_id(monkeypatch):
    from src.config import settings
    from src.db import auth_service as module

    requested = []
    key = "las_live_" + "A" * 43
    pepper = "P" * 64
    digest = hmac.digest(pepper.encode(), key.encode(), "sha256").hex()
    document = SimpleNamespace(
        id=digest,
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
    monkeypatch.setattr(settings, "API_KEY_PEPPER", pepper)

    assert module.AuthService().validate_key(key)["name"] == "Test"
    assert requested == [("api_keys", digest)]
    assert key not in repr(requested)


def test_api_key_lookup_accepts_a_peppered_v2_migration(monkeypatch):
    from src.config import settings
    from src.db import auth_service as module

    key = "las_live_" + "B" * 43
    pepper = "P" * 64
    current_id = hmac.digest(pepper.encode(), key.encode(), "sha256").hex()
    old_id = "2c4aab101d78a8e17258829e0e07d42d46217899ccc5b5be0fc0c5d3542d7695"
    migrated_id = hmac.digest(pepper.encode(), old_id.encode("ascii"), "sha256").hex()
    requested = []

    def document(document_id):
        requested.append(document_id)
        exists = document_id == migrated_id
        return SimpleNamespace(
            id=document_id,
            get=lambda: SimpleNamespace(
                id=document_id,
                exists=exists,
                to_dict=lambda: {"name": "Migrated", "is_active": True, "key_digest": migrated_id},
            ),
        )

    database = SimpleNamespace(collection=lambda _: SimpleNamespace(document=document))
    monkeypatch.setattr(module.db_client, "db", database)
    monkeypatch.setattr(settings, "MASTER_ADMIN_KEY", None)
    monkeypatch.setattr(settings, "API_KEY_PEPPER", pepper)

    assert module.AuthService().validate_key(key)["name"] == "Migrated"
    assert requested == [current_id, migrated_id]


def test_new_keys_have_256_bits_and_are_stored_without_the_secret(monkeypatch):
    from src.config import settings
    from scripts.manage_keys import build_key_record, generate_api_key

    pepper = "P" * 64
    monkeypatch.setattr(settings, "API_KEY_PEPPER", pepper)
    key = generate_api_key()
    document_id, record = build_key_record(key, "Test")
    expected = hmac.digest(pepper.encode(), key.encode(), "sha256").hex()

    assert key.startswith("las_live_")
    assert len(key.removeprefix("las_live_")) >= 43
    assert document_id == expected
    assert record["key_version"] == 4
    assert key not in repr(record)
    assert "key" not in record


def test_deactivate_key_supports_migrated_v2_records(monkeypatch):
    from src.config import settings
    from scripts import manage_keys
    from src.services.api_key_digest import migrated_v2_key_id

    pepper = "P" * 64
    api_key = "las_live_" + "C" * 43
    monkeypatch.setattr(settings, "API_KEY_PEPPER", pepper)
    migrated_id = migrated_v2_key_id(api_key)
    updated = []

    def document(document_id):
        return SimpleNamespace(
            get=lambda: SimpleNamespace(exists=document_id == migrated_id),
            update=lambda value: updated.append((document_id, value)),
        )

    monkeypatch.setattr(
        manage_keys.db_client,
        "db",
        SimpleNamespace(collection=lambda _: SimpleNamespace(document=document)),
    )

    manage_keys.deactivate_key(api_key)
    assert len(updated) == 1
    document_id, values = updated[0]
    assert document_id == migrated_id
    assert values["is_active"] is False
    assert values["deactivated_at"].tzinfo is not None
    assert 89 <= (values["expires_at"] - datetime.now(timezone.utc)).days <= 90


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
        return {
            "name": "Test", "email": "test@example.invalid", "company": "AB",
            "reason": "Test", "legal_accept": True,
        }

    request = SimpleNamespace(method="POST", client=SimpleNamespace(host="192.0.2.1"), json=body)
    response = await server.handle_key_request(request)

    assert response.status_code == 200
    expiry = captured[0]["expires_at"]
    assert expiry.tzinfo is not None
    assert 89 <= (expiry - datetime.now(timezone.utc)).days <= 90
    assert captured[0]["terms_version"] == "2026-09-26"
    assert captured[0]["legal_accepted_at"].tzinfo is not None


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
