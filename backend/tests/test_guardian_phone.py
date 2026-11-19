"""Tests del teléfono del Tutor en la vinculación (necesitan PostgreSQL).
Guardian phone in the pairing flow tests (need PostgreSQL).

ES: Números inventados (rango 600 000 000 de ejemplo).
EN: Fake numbers (example 600 000 000 range).
"""

import uuid

import pytest

from app.models.user import Pairing
from app.schemas.pairing import normalize_phone

PAIRINGS = "/api/v1/pairings"
REDEEM = "/api/v1/pairings/redeem"
SENIOR_ME = "/api/v1/senior/me"
DEVICE = {"platform": "android", "app_version": "0.5.0", "push_token": None}


def create(api_client, headers, phone=None):
    body = {"senior_display_name": "Carmen"}
    if phone is not None:
        body["guardian_phone"] = phone
    return api_client.post(PAIRINGS, json=body, headers=headers)


def redeem(api_client, code):
    return api_client.post(REDEEM, json={"code": code, "device": DEVICE})


# ---------- Normalización / normalization ----------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+34 600 000 000", "+34600000000"),
        ("600-000-000", "600000000"),
        ("(+34) 600.000.000", "+34600000000"),
        ("   ", None),
        (None, None),
    ],
)
def test_phone_is_normalized(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize(
    "raw", ["12345", "+34 600 abc 000", "++34600000000", "1234567890123456"]
)
def test_invalid_phone_raises(raw):
    with pytest.raises(ValueError):
        normalize_phone(raw)


# ---------- Crear código / create pairing ----------


def test_pairing_stores_normalized_phone(api_client, db_session, guardian_headers):
    response = create(api_client, guardian_headers, "+34 600 000 000")
    assert response.status_code == 201
    pairing = db_session.get(Pairing, uuid.UUID(response.json()["id"]))
    assert pairing.guardian_phone == "+34600000000"


def test_pairing_without_phone_still_works(api_client, db_session, guardian_headers):
    response = create(api_client, guardian_headers)
    assert response.status_code == 201
    pairing = db_session.get(Pairing, uuid.UUID(response.json()["id"]))
    assert pairing.guardian_phone is None


def test_invalid_phone_is_422(api_client, guardian_headers):
    response = create(api_client, guardian_headers, "llámame")
    assert response.status_code == 422


# ---------- Canjear y recuperar / redeem and fetch ----------


def test_redeem_returns_phone(api_client, guardian_headers):
    code = create(api_client, guardian_headers, "+34 600 000 000").json()["code"]
    response = redeem(api_client, code)
    assert response.status_code == 200
    assert response.json()["guardian_phone"] == "+34600000000"


def test_redeem_without_phone_returns_null(api_client, guardian_headers):
    code = create(api_client, guardian_headers).json()["code"]
    response = redeem(api_client, code)
    assert response.status_code == 200
    assert response.json()["guardian_phone"] is None


def test_senior_fetches_phone_later(api_client, guardian_headers):
    code = create(api_client, guardian_headers, "600 000 000").json()["code"]
    token = redeem(api_client, code).json()["access_token"]
    response = api_client.get(SENIOR_ME, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["guardian_phone"] == "600000000"


def test_senior_me_without_phone_is_null(api_client, paired_senior):
    response = api_client.get(SENIOR_ME, headers=paired_senior.headers)
    assert response.status_code == 200
    assert response.json()["guardian_phone"] is None
