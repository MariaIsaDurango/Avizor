"""Tests del endpoint GET /api/v1/senior (necesitan PostgreSQL).
Tests for GET /api/v1/senior endpoint (need PostgreSQL).
"""

from app.core.security import create_access_token
from app.schemas.enums import UserRole

SENIOR = "/api/v1/senior"


# ---------- Autenticación / Authentication ----------


def test_sin_token_devuelve_401(api_client):
    response = api_client.get(SENIOR)
    assert response.status_code == 401


def test_token_senior_devuelve_403(api_client, paired_senior):
    response = api_client.get(SENIOR, headers=paired_senior.headers)
    assert response.status_code == 403


# ---------- Sin vinculación / No pairing ----------


def test_tutor_sin_vinculo_devuelve_404(api_client, guardian_headers):
    response = api_client.get(SENIOR, headers=guardian_headers)
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


# ---------- Con vinculación / With pairing ----------


def test_tutor_vinculado_devuelve_datos_senior(api_client, guardian_headers, paired_senior):
    response = api_client.get(SENIOR, headers=guardian_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["senior_display_name"] == paired_senior.user.display_name
    assert body["platform"] == paired_senior.device.platform
    assert "paired_since" in body


def test_otro_tutor_no_ve_al_senior(api_client, db_session, paired_senior):
    from app.core.security import hash_password
    from app.models.user import User

    other = User(
        role=UserRole.GUARDIAN,
        display_name="Otro Tutor",
        email="otro@example.com",
        password_hash=hash_password("contraseña-larga-2"),
    )
    db_session.add(other)
    db_session.flush()

    token = create_access_token(other.id, UserRole.GUARDIAN)
    response = api_client.get(SENIOR, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404
