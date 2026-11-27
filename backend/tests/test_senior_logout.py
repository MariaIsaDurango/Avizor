"""Tests del endpoint POST /api/v1/senior/logout (necesitan PostgreSQL).
Tests for POST /api/v1/senior/logout endpoint (need PostgreSQL).
"""

from datetime import UTC

import pytest

from app.models.user import Device
from app.services import push as push_service
from app.services.push import PushMessage

LOGOUT = "/api/v1/senior/logout"
TOKEN = "ExponentPushToken[guardian-phone]"


class FakeSender:
    def __init__(self, raises=False):
        self.sent: list[PushMessage] = []
        self.raises = raises

    def send(self, messages):
        if self.raises:
            raise RuntimeError("sender boom")
        self.sent.extend(messages)
        return set()


@pytest.fixture
def guardian_with_push(db_session, guardian):
    device = Device(
        user_id=guardian.id, platform="android", app_version="0.5.0", push_token=TOKEN
    )
    db_session.add(device)
    db_session.flush()
    return device


# ---------- Autenticación / Authentication ----------


def test_sin_token_devuelve_401(api_client):
    response = api_client.post(LOGOUT)
    assert response.status_code == 401


def test_token_tutor_devuelve_403(api_client, guardian_headers):
    response = api_client.post(LOGOUT, headers=guardian_headers)
    assert response.status_code == 403


# ---------- Envío de push / Push delivery ----------


def test_logout_con_push_token_envia_mensaje(
    api_client, paired_senior, guardian_with_push, monkeypatch
):
    sender = FakeSender()
    monkeypatch.setattr(push_service, "get_sender", lambda: sender)

    response = api_client.post(LOGOUT, headers=paired_senior.headers)

    assert response.status_code == 204
    assert len(sender.sent) == 1
    msg = sender.sent[0]
    assert msg.token == TOKEN
    assert paired_senior.user.display_name in msg.notification.body
    assert msg.notification.type == "senior_logout"


def test_logout_sin_push_token_devuelve_204(api_client, paired_senior, monkeypatch):
    sender = FakeSender()
    monkeypatch.setattr(push_service, "get_sender", lambda: sender)

    response = api_client.post(LOGOUT, headers=paired_senior.headers)

    assert response.status_code == 204
    assert sender.sent == []


def test_logout_sender_error_devuelve_204(
    api_client, paired_senior, guardian_with_push, monkeypatch
):
    monkeypatch.setattr(push_service, "get_sender", lambda: FakeSender(raises=True))

    response = api_client.post(LOGOUT, headers=paired_senior.headers)

    assert response.status_code == 204


# ---------- Rate limiting / Cooldown ----------


def test_segundo_logout_en_cooldown_no_envia(
    api_client, paired_senior, guardian_with_push, monkeypatch
):
    monkeypatch.setattr(push_service, "_logout_push_last_sent", {})
    sender = FakeSender()
    monkeypatch.setattr(push_service, "get_sender", lambda: sender)

    api_client.post(LOGOUT, headers=paired_senior.headers)
    api_client.post(LOGOUT, headers=paired_senior.headers)

    assert len(sender.sent) == 1


def test_logout_deleted_senior_returns_204_without_sending_push(
    api_client, db_session, paired_senior, monkeypatch
):
    from datetime import datetime

    paired_senior.user.deleted_at = datetime.now(UTC)
    db_session.flush()

    monkeypatch.setattr(
        push_service,
        "get_sender",
        lambda: pytest.fail("No debería intentar enviar una notificación"),
    )

    response = api_client.post(LOGOUT, headers=paired_senior.headers)

    assert response.status_code == 204
