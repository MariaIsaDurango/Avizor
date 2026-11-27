"""Tests del perfil de accesibilidad del Sénior (necesitan PostgreSQL).
Senior accessibility profile tests (need PostgreSQL).
"""

import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.models.user import Pairing, User
from app.schemas.accessibility import AccessibilityProfile

PAIRINGS = "/api/v1/pairings"
REDEEM = "/api/v1/pairings/redeem"
DEVICE = {"platform": "android", "app_version": "0.4.0", "push_token": None}
PROFILE = {
    "color_blindness": False,
    "low_vision": True,
    "blindness": False,
    "hearing_impairment": True,
}


def create(api_client, headers, profile=None):
    body = {"senior_display_name": "Carmen"}
    if profile is not None:
        body["senior_accessibility_profile"] = profile
    return api_client.post(PAIRINGS, json=body, headers=headers)


def redeem(api_client, code):
    return api_client.post(REDEEM, json={"code": code, "device": DEVICE})


# ---------- Schema ----------


def test_profile_defaults_to_all_false():
    assert AccessibilityProfile().model_dump() == {
        "color_blindness": False,
        "low_vision": False,
        "blindness": False,
        "hearing_impairment": False,
    }


def test_profile_rejects_unknown_fields():
    # ES: Son datos de salud: no se guarda nada que no se pidió.
    # EN: Health data: nothing that was not requested is stored.
    with pytest.raises(ValidationError):
        AccessibilityProfile(low_vision=True, diagnosis="glaucoma")


# ---------- Crear código / create pairing ----------


def test_pairing_stores_profile(api_client, db_session, guardian_headers):
    response = create(api_client, guardian_headers, PROFILE)
    assert response.status_code == 201
    pairing = db_session.get(Pairing, uuid.UUID(response.json()["id"]))
    assert pairing.senior_accessibility_profile == PROFILE


def test_partial_profile_is_completed_with_false(
    api_client, db_session, guardian_headers
):
    response = create(api_client, guardian_headers, {"blindness": True})
    assert response.status_code == 201
    pairing = db_session.get(Pairing, uuid.UUID(response.json()["id"]))
    assert pairing.senior_accessibility_profile == {
        "color_blindness": False,
        "low_vision": False,
        "blindness": True,
        "hearing_impairment": False,
    }


def test_pairing_without_profile_still_works(api_client, db_session, guardian_headers):
    response = create(api_client, guardian_headers)
    assert response.status_code == 201
    pairing = db_session.get(Pairing, uuid.UUID(response.json()["id"]))
    assert pairing.senior_accessibility_profile is None


@pytest.mark.parametrize(
    "profile",
    [{"low_vision": "mucho"}, {"diagnosis": "glaucoma"}, ["low_vision"]],
)
def test_invalid_profile_is_rejected(api_client, guardian_headers, profile):
    response = create(api_client, guardian_headers, profile)
    assert response.status_code == 422


# ---------- Canjear código / redeem ----------


def test_redeem_copies_profile_to_senior(api_client, db_session, guardian_headers):
    code = create(api_client, guardian_headers, PROFILE).json()["code"]
    response = redeem(api_client, code)
    assert response.status_code == 200
    body = response.json()
    assert body["accessibility_profile"] == PROFILE
    senior = db_session.get(User, uuid.UUID(body["senior_id"]))
    assert senior.accessibility_profile == PROFILE


def test_redeem_without_profile_returns_null(api_client, db_session, guardian_headers):
    code = create(api_client, guardian_headers).json()["code"]
    response = redeem(api_client, code)
    assert response.status_code == 200
    assert response.json()["accessibility_profile"] is None
    senior = db_session.get(User, uuid.UUID(response.json()["senior_id"]))
    assert senior.accessibility_profile is None


# ---------- Recuperar el perfil / fetch the profile ----------

SENIOR = "/api/v1/senior"
SENIOR_ME = "/api/v1/senior/me"


def test_guardian_sees_senior_profile(
    api_client, db_session, guardian_headers, paired_senior
):
    paired_senior.user.accessibility_profile = PROFILE
    db_session.flush()
    response = api_client.get(SENIOR, headers=guardian_headers)
    assert response.status_code == 200
    assert response.json()["accessibility_profile"] == PROFILE


def test_senior_fetches_own_profile(api_client, db_session, paired_senior):
    paired_senior.user.accessibility_profile = PROFILE
    db_session.flush()
    response = api_client.get(SENIOR_ME, headers=paired_senior.headers)
    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Carmen"
    assert body["accessibility_profile"] == PROFILE


def test_senior_without_profile_gets_null(api_client, paired_senior):
    response = api_client.get(SENIOR_ME, headers=paired_senior.headers)
    assert response.status_code == 200
    assert response.json()["accessibility_profile"] is None


def test_senior_me_requires_senior_token(api_client, guardian_headers):
    assert api_client.get(SENIOR_ME).status_code == 401
    assert api_client.get(SENIOR_ME, headers=guardian_headers).status_code == 403


def test_profile_survives_after_redeem(api_client, guardian_headers):
    # ES: Flujo completo: crear, canjear y recuperar más tarde.
    # EN: Full flow: create, redeem and fetch later.
    code = create(api_client, guardian_headers, PROFILE).json()["code"]
    token = redeem(api_client, code).json()["access_token"]
    response = api_client.get(SENIOR_ME, headers={"Authorization": f"Bearer {token}"})
    assert response.json()["accessibility_profile"] == PROFILE

def test_senior_profile_uses_account_phone_when_pairing_phone_is_missing(
    api_client, db_session, guardian, paired_senior
):

    guardian.phone = "+34600000001"

    pairing = db_session.scalar(
        select(Pairing).where(Pairing.guardian_id == guardian.id)
    )
    pairing.guardian_phone = None
    db_session.flush()

    response = api_client.get(SENIOR_ME, headers=paired_senior.headers)

    assert response.status_code == 200
    assert response.json()["guardian_phone"] == "+34600000001"
