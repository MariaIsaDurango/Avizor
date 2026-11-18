"""Tests del perfil de accesibilidad del Sénior (necesitan PostgreSQL).
Senior accessibility profile tests (need PostgreSQL).
"""

import uuid

import pytest
from pydantic import ValidationError

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
