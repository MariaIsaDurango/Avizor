"""Tests del Sénior sin Tutor (#174). Necesitan PostgreSQL.
Senior without a guardian tests (#174). They need PostgreSQL.
"""

import uuid

import pytest
from conftest import ANALYSES, LOGIN, PHISHING, REGISTER, SOLO, analysis_body
from sqlalchemy import select

from app.api.v1 import auth as auth_routes
from app.models.alert import Alert
from app.models.analysis import Analysis
from app.models.user import Device, User
from app.schemas.enums import UserRole

ME = "/api/v1/auth/me"
UNLOCKS = "/api/v1/unlocks"

# ---------- Registro / Sign-up ----------


def test_register_creates_user_and_device(api_client, db_session):
    response = api_client.post(REGISTER, json=SOLO)
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "senior_solo"
    assert "password" not in data and "password_hash" not in data
    device = db_session.get(Device, uuid.UUID(data["device_id"]))
    assert device.user_id == uuid.UUID(data["id"])
    assert device.platform == "android"


def test_register_senior_solo_needs_device(api_client):
    body = {k: v for k, v in SOLO.items() if k != "device"}
    response = api_client.post(REGISTER, json=body)
    assert response.status_code == 422


@pytest.mark.parametrize("role", ["senior", "admin"])
def test_register_rejects_other_roles(api_client, role):
    response = api_client.post(REGISTER, json={**SOLO, "role": role})
    assert response.status_code == 422


def test_guardian_register_unchanged(api_client, db_session):
    body = {k: v for k, v in SOLO.items() if k not in ("role", "device")}
    response = api_client.post(REGISTER, json=body)
    assert response.status_code == 201
    assert response.json()["role"] == "guardian"
    assert response.json()["device_id"] is None
    user_id = uuid.UUID(response.json()["id"])
    assert db_session.scalar(select(Device).where(Device.user_id == user_id)) is None


def test_unverified_senior_solo_cannot_login(api_client):
    api_client.post(REGISTER, json=SOLO)
    response = api_client.post(
        LOGIN, json={"email": SOLO["email"], "password": SOLO["password"]}
    )
    assert response.status_code == 403


def test_senior_solo_verifies_email_and_logs_in(api_client, monkeypatch):
    """ES: Mismo flujo que el Tutor: código por correo y luego login.
    EN: Same flow as the guardian: emailed code, then login.
    """
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        auth_routes, "send_verification_email", lambda to, code: sent.append((to, code))
    )
    api_client.post(REGISTER, json=SOLO)
    ((email, code),) = sent
    verified = api_client.post(
        "/api/v1/auth/verify-email", json={"email": email, "code": code}
    )
    assert verified.status_code == 204
    response = api_client.post(
        LOGIN, json={"email": SOLO["email"], "password": SOLO["password"]}
    )
    assert response.status_code == 200
    assert response.json()["device_id"]


# ---------- Login y perfil / Login and profile ----------


def test_login_returns_device_and_me_shows_profile(api_client, solo):
    response = api_client.get(ME, headers=solo["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == UserRole.SENIOR_SOLO
    assert data["display_name"] == "Carmen"
    assert data["device_id"] == str(solo["device_id"])


def test_password_change_revokes_senior_solo_token(api_client, db_session, solo):
    user = db_session.get(User, solo["user_id"])
    user.token_version += 1
    db_session.flush()
    response = api_client.get(ME, headers=solo["headers"])
    assert response.status_code == 401


# ---------- Análisis / Analysis ----------


def test_analysis_without_device_id_uses_token_device(
    api_client, db_session, consented_solo
):
    response = api_client.post(
        ANALYSES, json=analysis_body(PHISHING), headers=consented_solo["headers"]
    )
    assert response.status_code == 200
    assert response.json()["risk_level"] == "red"
    analysis = db_session.get(Analysis, uuid.UUID(response.json()["analysis_id"]))
    assert analysis.device_id == consented_solo["device_id"]


def test_red_analysis_creates_no_guardian_alert(api_client, db_session, consented_solo):
    response = api_client.post(
        ANALYSES, json=analysis_body(PHISHING), headers=consented_solo["headers"]
    )
    assert response.json()["risk_level"] == "red"
    analysis_id = uuid.UUID(response.json()["analysis_id"])
    alerts = db_session.scalars(
        select(Alert).where(Alert.analysis_id == analysis_id)
    ).all()
    assert alerts == []


def test_analysis_with_other_device_id_is_forbidden(api_client, consented_solo):
    body = analysis_body(PHISHING, device_id=uuid.uuid4())
    response = api_client.post(ANALYSES, json=body, headers=consented_solo["headers"])
    assert response.status_code == 403


def test_automatic_analysis_needs_consent(api_client, solo):
    response = api_client.post(
        ANALYSES, json=analysis_body(PHISHING), headers=solo["headers"]
    )
    assert response.status_code == 403
    assert response.json()["code"] == "CONSENT_MISSING"


def test_paired_senior_still_needs_device_id(api_client, consented_senior):
    response = api_client.post(
        ANALYSES, json=analysis_body(PHISHING), headers=consented_senior.headers
    )
    assert response.status_code == 422


def test_senior_solo_can_read_own_verdict(api_client, consented_solo):
    created = api_client.post(
        ANALYSES, json=analysis_body(PHISHING), headers=consented_solo["headers"]
    )
    analysis_id = created.json()["analysis_id"]
    response = api_client.get(
        f"{ANALYSES}/{analysis_id}/verdict", headers=consented_solo["headers"]
    )
    assert response.status_code == 200


# ---------- Sin Tutor / No guardian ----------


def test_senior_solo_cannot_request_unlock(api_client, consented_solo):
    """ES: Sin auto-desbloqueo en el MVP: un estafador podría presionarle.
    EN: No self-unlock in the MVP: a scammer could pressure them.
    """
    response = api_client.post(
        UNLOCKS,
        json={"analysis_id": str(uuid.uuid4()), "reason": "Es mi banco"},
        headers=consented_solo["headers"],
    )
    assert response.status_code == 403


def test_senior_solo_cannot_use_guardian_endpoints(api_client, solo):
    response = api_client.get("/api/v1/alerts", headers=solo["headers"])
    assert response.status_code == 403
