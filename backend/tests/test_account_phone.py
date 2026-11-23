"""Tests del teléfono en la cuenta del Tutor (necesitan PostgreSQL).
Guardian account phone tests (need PostgreSQL).
"""

import uuid

from sqlalchemy import select

from app.models.user import Pairing

ME = "/api/v1/auth/me"
PAIRINGS = "/api/v1/pairings"
DEVICE = {"platform": "android", "app_version": "0.5.0", "push_token": None}


# ---------- GET /auth/me ----------


def test_get_me_includes_phone(api_client, guardian_headers):
    response = api_client.get(ME, headers=guardian_headers)
    assert response.status_code == 200
    assert "phone" in response.json()
    assert response.json()["phone"] is None


# ---------- PATCH /auth/me — teléfono ----------


def test_patch_me_saves_phone(api_client, guardian, guardian_headers, db_session):
    response = api_client.patch(
        ME,
        json={"display_name": guardian.display_name, "phone": "+34 600 000 001"},
        headers=guardian_headers,
    )
    assert response.status_code == 200
    assert response.json()["phone"] == "+34600000001"
    db_session.refresh(guardian)
    assert guardian.phone == "+34600000001"


def test_patch_me_clears_phone(api_client, guardian, guardian_headers, db_session):
    guardian.phone = "+34600000001"
    db_session.flush()
    response = api_client.patch(
        ME,
        json={"display_name": guardian.display_name, "phone": None},
        headers=guardian_headers,
    )
    assert response.status_code == 200
    assert response.json()["phone"] is None


def test_patch_me_invalid_phone_is_422(api_client, guardian_headers, guardian):
    response = api_client.patch(
        ME,
        json={"display_name": guardian.display_name, "phone": "llámame"},
        headers=guardian_headers,
    )
    assert response.status_code == 422


# ---------- Propagación a vinculaciones activas ----------


def test_patch_me_phone_updates_active_pairing(
    api_client, db_session, guardian, guardian_headers, paired_senior
):
    api_client.patch(
        ME,
        json={"display_name": guardian.display_name, "phone": "+34600000002"},
        headers=guardian_headers,
    )
    pairing = db_session.scalar(
        select(Pairing).where(Pairing.guardian_id == guardian.id, Pairing.active.is_(True))
    )
    assert pairing.guardian_phone == "+34600000002"


# ---------- Copia al crear pairing ----------


def test_pairing_copies_phone_from_account(
    api_client, db_session, guardian, guardian_headers
):
    guardian.phone = "+34600000003"
    db_session.flush()
    response = api_client.post(
        PAIRINGS,
        json={"senior_display_name": "Abuela"},
        headers=guardian_headers,
    )
    assert response.status_code == 201
    pairing = db_session.get(Pairing, uuid.UUID(response.json()["id"]))
    assert pairing.guardian_phone == "+34600000003"


def test_pairing_explicit_phone_overrides_account(
    api_client, db_session, guardian, guardian_headers
):
    guardian.phone = "+34600000003"
    db_session.flush()
    response = api_client.post(
        PAIRINGS,
        json={"senior_display_name": "Abuela", "guardian_phone": "+34600000099"},
        headers=guardian_headers,
    )
    assert response.status_code == 201
    pairing = db_session.get(Pairing, uuid.UUID(response.json()["id"]))
    assert pairing.guardian_phone == "+34600000099"
