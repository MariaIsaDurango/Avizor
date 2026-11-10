"""Tests de alertas del Tutor (necesitan PostgreSQL).
Guardian alert tests (need PostgreSQL).
"""

import uuid

import pytest

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.schemas.alert import Alert, AlertPage
from app.schemas.enums import UserRole

ALERTS = "/api/v1/alerts"
ANALYSES = "/api/v1/analyses"

PHISHING = "BBVA: su cuenta [IBAN] ha sido bloqueada. Verifique en el enlace."


def send_phishing(api_client, senior):
    """ES: Crea una alerta real pasando por la vía rápida.
    EN: Creates a real alert through the fast path.
    """
    body = {
        "device_id": str(senior.device.id),
        "channel": "sms",
        "origin": "automatic",
        "input_type": "text",
        "received_at": "2026-11-04T13:12:05Z",
        "sender": {"type": "phone", "value": "+34612345612"},
        "content": {
            "text": PHISHING,
            "urls": ["https://bbva-seguro.top/login"],
            "anonymization": {"applied": True, "ner_model_version": "ner-test"},
        },
    }
    response = api_client.post(ANALYSES, json=body, headers=senior.headers)
    assert response.json()["risk_level"] == "red"
    return response.json()["analysis_id"]


@pytest.fixture
def one_alert(api_client, consented_senior, guardian_headers):
    send_phishing(api_client, consented_senior)
    page = api_client.get(ALERTS, headers=guardian_headers).json()
    return page["items"][0]


# ---------- GET /alerts ----------


def test_list_returns_contract_alert(one_alert, consented_senior):
    alert = Alert.model_validate(one_alert)
    assert alert.senior_name == "Carmen"
    assert alert.senior_id == consented_senior.user.id
    assert alert.status == "new"
    assert alert.channel == "sms"


def test_list_never_includes_message_text(api_client, guardian_headers, one_alert):
    response = api_client.get(ALERTS, headers=guardian_headers)
    assert "[IBAN]" not in response.text
    assert "Verifique en el enlace" not in response.text


def test_empty_list(api_client, guardian_headers):
    page = AlertPage.model_validate(
        api_client.get(ALERTS, headers=guardian_headers).json()
    )
    assert page.items == []
    assert page.next_cursor is None


def test_cursor_pagination(api_client, consented_senior, guardian_headers):
    for _ in range(3):
        send_phishing(api_client, consented_senior)

    first = api_client.get(f"{ALERTS}?limit=2", headers=guardian_headers).json()
    assert len(first["items"]) == 2
    assert first["next_cursor"]

    second = api_client.get(
        f"{ALERTS}?limit=2&cursor={first['next_cursor']}", headers=guardian_headers
    ).json()
    assert len(second["items"]) == 1
    assert second["next_cursor"] is None

    ids = [a["id"] for a in first["items"] + second["items"]]
    assert len(set(ids)) == 3  # ES/EN: no duplicates


def test_filter_by_status(api_client, guardian_headers, one_alert):
    seen = api_client.get(f"{ALERTS}?status=seen", headers=guardian_headers).json()
    assert seen["items"] == []


def test_invalid_cursor_is_422(api_client, guardian_headers):
    response = api_client.get(f"{ALERTS}?cursor=basura", headers=guardian_headers)
    assert response.status_code == 422


@pytest.mark.parametrize("limit", [0, 101])
def test_limit_bounds(api_client, guardian_headers, limit):
    response = api_client.get(f"{ALERTS}?limit={limit}", headers=guardian_headers)
    assert response.status_code == 422


def test_other_guardian_sees_nothing(api_client, db_session, one_alert):
    stranger = User(
        role=UserRole.GUARDIAN,
        display_name="Otro",
        email="otro.tutor@example.com",
        password_hash=hash_password("contraseña-larga-2"),
    )
    db_session.add(stranger)
    db_session.flush()
    token = create_access_token(stranger.id, UserRole.GUARDIAN)
    page = api_client.get(ALERTS, headers={"Authorization": f"Bearer {token}"})
    assert page.json()["items"] == []


def test_senior_cannot_list_alerts(api_client, consented_senior):
    response = api_client.get(ALERTS, headers=consented_senior.headers)
    assert response.status_code == 403


# ---------- PATCH /alerts/{id} ----------


@pytest.mark.parametrize("status", ["seen", "confirmed_fraud", "false_positive"])
def test_guardian_updates_status(api_client, guardian_headers, one_alert, status):
    response = api_client.patch(
        f"{ALERTS}/{one_alert['id']}", json={"status": status}, headers=guardian_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == status


def test_cannot_set_back_to_new(api_client, guardian_headers, one_alert):
    response = api_client.patch(
        f"{ALERTS}/{one_alert['id']}", json={"status": "new"}, headers=guardian_headers
    )
    assert response.status_code == 422


def test_update_unknown_alert_is_404(api_client, guardian_headers):
    response = api_client.patch(
        f"{ALERTS}/{uuid.uuid4()}", json={"status": "seen"}, headers=guardian_headers
    )
    assert response.status_code == 404


def test_other_guardian_cannot_update(api_client, db_session, one_alert):
    stranger = User(
        role=UserRole.GUARDIAN,
        display_name="Otro",
        email="otro2.tutor@example.com",
        password_hash=hash_password("contraseña-larga-3"),
    )
    db_session.add(stranger)
    db_session.flush()
    token = create_access_token(stranger.id, UserRole.GUARDIAN)
    response = api_client.patch(
        f"{ALERTS}/{one_alert['id']}",
        json={"status": "false_positive"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
