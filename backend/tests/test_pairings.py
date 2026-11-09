"""Tests de vinculación Tutor ↔ Sénior (necesitan PostgreSQL).
Guardian ↔ Senior pairing tests (need PostgreSQL).
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.security import create_access_token, decode_access_token
from app.models.user import Device, Pairing, User
from app.schemas.enums import UserRole

PAIRINGS = "/api/v1/pairings"
REDEEM = "/api/v1/pairings/redeem"
DEVICE = {"platform": "android", "app_version": "0.4.0", "push_token": None}


@pytest.fixture
def pairing(api_client, guardian_headers):
    response = api_client.post(
        PAIRINGS, json={"senior_display_name": "Carmen"}, headers=guardian_headers
    )
    assert response.status_code == 201
    return response.json()


def redeem(api_client, code):
    return api_client.post(REDEEM, json={"code": code, "device": DEVICE})


# ---------- Crear código / Create code ----------


def test_create_pairing_returns_six_digit_code(pairing):
    assert len(pairing["code"]) == 6
    assert pairing["code"].isdigit()


def test_code_expires_in_about_ten_minutes(pairing):
    expires_at = datetime.fromisoformat(pairing["expires_at"])
    remaining = expires_at - datetime.now(UTC)
    assert timedelta(minutes=9) < remaining <= timedelta(minutes=10)


def test_create_pairing_requires_token(api_client):
    response = api_client.post(PAIRINGS, json={"senior_display_name": "Carmen"})
    assert response.status_code == 401


def test_senior_cannot_create_pairing(api_client):
    token = create_access_token(uuid.uuid4(), UserRole.SENIOR)
    response = api_client.post(
        PAIRINGS,
        json={"senior_display_name": "Carmen"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


# ---------- Canjear código / Redeem code ----------


def test_redeem_creates_senior_device_and_token(api_client, db_session, pairing):
    response = redeem(api_client, pairing["code"])
    assert response.status_code == 200
    body = response.json()

    payload = decode_access_token(body["access_token"])
    assert payload.role == UserRole.SENIOR
    assert str(payload.sub) == body["device_id"]

    senior = db_session.get(User, uuid.UUID(body["senior_id"]))
    assert senior.display_name == "Carmen"
    assert senior.role == UserRole.SENIOR
    assert senior.email is None  # ES: sin email ni contraseña / EN: no email/password

    device = db_session.get(Device, uuid.UUID(body["device_id"]))
    assert device.user_id == senior.id

    stored = db_session.get(Pairing, uuid.UUID(pairing["id"]))
    assert stored.senior_id == senior.id
    assert stored.redeemed_at is not None


def test_code_can_only_be_redeemed_once(api_client, pairing):
    assert redeem(api_client, pairing["code"]).status_code == 200
    second = redeem(api_client, pairing["code"])
    assert second.status_code == 404
    assert second.json()["code"] == "NOT_FOUND"


def test_expired_code(api_client, db_session, pairing):
    stored = db_session.get(Pairing, uuid.UUID(pairing["id"]))
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()

    response = redeem(api_client, pairing["code"])
    assert response.status_code == 410
    assert response.json()["code"] == "PAIRING_EXPIRED"


def test_unknown_code(api_client):
    response = redeem(api_client, "000000")
    assert response.status_code == 404


@pytest.mark.parametrize("code", ["12345", "abcdef", "1234567"])
def test_malformed_code_is_validation_error(api_client, code):
    response = redeem(api_client, code)
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
