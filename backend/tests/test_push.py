"""Tests de las notificaciones push al Tutor.
Guardian push notification tests.

ES: Nunca se llama a Expo de verdad: se usa un emisor falso o MockTransport.
EN: Expo is never really called: a fake sender or MockTransport is used.
"""

import json
import uuid

import httpx
import pytest

from app.models.user import Device
from app.services import push as push_service
from app.services.push import (
    EXPO_PUSH_URL,
    ExpoPushSender,
    PushMessage,
    build_notification,
    send_alert_pushes,
)

ANALYSES = "/api/v1/analyses"
TOKEN = "ExponentPushToken[guardian-phone]"
PHISHING = "BBVA: su cuenta [IBAN] ha sido bloqueada. Verifique en el enlace."


class FakeSender:
    def __init__(self, invalid=frozenset()):
        self.sent: list[PushMessage] = []
        self.invalid = set(invalid)

    def send(self, messages):
        self.sent.extend(messages)
        return self.invalid


def analysis_body(senior, text=PHISHING, urls=("https://bbva-seguro.top/login",)):
    return {
        "device_id": str(senior.device.id),
        "channel": "sms",
        "origin": "automatic",
        "input_type": "text",
        "received_at": "2026-11-04T13:12:05Z",
        "content": {
            "text": text,
            "urls": list(urls),
            "anonymization": {"applied": True, "ner_model_version": "ner-test"},
        },
    }


@pytest.fixture
def scheduled(monkeypatch):
    """ES: Guarda los ids que el endpoint manda a la tarea en segundo plano.
    EN: Records the ids the endpoint hands to the background task.
    """
    calls: list[list[uuid.UUID]] = []
    monkeypatch.setattr(push_service, "send_alert_pushes_job", calls.append)
    return calls


@pytest.fixture
def guardian_phone(db_session, guardian):
    device = Device(
        user_id=guardian.id, platform="android", app_version="0.5.0", push_token=TOKEN
    )
    db_session.add(device)
    db_session.flush()
    return device


# ---------- build_notification ----------


def test_notification_has_no_message_content():
    notification = build_notification(uuid.uuid4(), "Carmen")
    assert notification.type == "new_alert"
    assert notification.title == "Estafa bloqueada"
    assert "Carmen" in notification.body


def test_notification_fits_with_longest_name():
    # ES: display_name admite hasta 50 caracteres; el body, 120.
    # EN: display_name allows up to 50 characters; the body, 120.
    build_notification(uuid.uuid4(), "A" * 50)


# ---------- POST /analyses programa el push / schedules the push ----------


def test_red_analysis_schedules_push(api_client, consented_senior, scheduled):
    response = api_client.post(
        ANALYSES, json=analysis_body(consented_senior), headers=consented_senior.headers
    )
    assert response.json()["risk_level"] == "red"
    assert len(scheduled) == 1
    assert len(scheduled[0]) == 1


def test_green_analysis_does_not_push(api_client, consented_senior, scheduled):
    body = analysis_body(consented_senior, text="Hola, ¿comemos el domingo?", urls=())
    response = api_client.post(ANALYSES, json=body, headers=consented_senior.headers)
    assert response.json()["risk_level"] == "green"
    assert scheduled == []


# ---------- send_alert_pushes ----------


@pytest.fixture
def alert_ids(api_client, consented_senior, scheduled):
    api_client.post(
        ANALYSES, json=analysis_body(consented_senior), headers=consented_senior.headers
    )
    return scheduled[0]


def test_push_goes_to_guardian_phone(db_session, alert_ids, guardian_phone):
    sender = FakeSender()
    assert send_alert_pushes(db_session, alert_ids, sender) == 1
    message = sender.sent[0]
    assert message.token == TOKEN
    assert message.notification.alert_id == alert_ids[0]
    assert "[IBAN]" not in message.notification.model_dump_json()


def test_guardian_without_phone_gets_nothing(db_session, alert_ids):
    sender = FakeSender()
    assert send_alert_pushes(db_session, alert_ids, sender) == 0
    assert sender.sent == []


def test_invalid_token_is_removed(db_session, alert_ids, guardian_phone):
    send_alert_pushes(db_session, alert_ids, FakeSender(invalid={TOKEN}))
    db_session.refresh(guardian_phone)
    assert guardian_phone.push_token is None


def test_senior_phone_never_gets_the_push(db_session, alert_ids, consented_senior):
    consented_senior.device.push_token = "ExponentPushToken[senior-phone]"
    db_session.flush()
    sender = FakeSender()
    send_alert_pushes(db_session, alert_ids, sender)
    assert sender.sent == []


# ---------- ExpoPushSender ----------


def expo_client(tickets, captured):
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"data": tickets})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_expo_payload_and_invalid_tokens():
    captured: list[httpx.Request] = []
    tickets = [
        {"status": "ok", "id": "1"},
        {"status": "error", "details": {"error": "DeviceNotRegistered"}},
    ]
    sender = ExpoPushSender("expo-access", client=expo_client(tickets, captured))
    alert_id = uuid.uuid4()
    messages = [
        PushMessage("ExponentPushToken[a]", build_notification(alert_id, "Carmen")),
        PushMessage("ExponentPushToken[b]", build_notification(alert_id, "Carmen")),
    ]

    invalid = sender.send(messages)

    assert invalid == {"ExponentPushToken[b]"}
    request = captured[0]
    assert str(request.url) == EXPO_PUSH_URL
    assert request.headers["Authorization"] == "Bearer expo-access"
    payload = json.loads(request.content)
    assert payload[0]["to"] == "ExponentPushToken[a]"
    assert payload[0]["data"] == {
        "type": "new_alert",
        "alert_id": str(alert_id),
        "title": "Estafa bloqueada",
        "body": "Hemos bloqueado un intento de estafa en el móvil de Carmen.",
    }


def test_job_never_raises(monkeypatch):
    """ES: Si falla el envío, no rompe nada. EN: A failed send breaks nothing."""

    def boom(*_args):
        raise RuntimeError("Expo caído")

    monkeypatch.setattr(push_service, "send_alert_pushes", boom)
    push_service.send_alert_pushes_job([uuid.uuid4()])
