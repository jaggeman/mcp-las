import pytest
from src.services.notification_service import NotificationService

def test_notification_service_handles_unconfigured_smtp():
    service = NotificationService()
    # When SMTP credentials are not set, it should log and return False without throwing an exception
    res = service.send_key_request_notification({
        "name": "Test Testsson",
        "email": "test@example.com",
        "company": "Testbolaget AB",
        "reason": "Integration med Claude AI",
        "created_at": "2026-09-06T18:00:00Z"
    })
    assert res is False
