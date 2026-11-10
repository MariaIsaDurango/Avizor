"""Tests de registro, login y permisos (necesitan PostgreSQL).
Sign-up, login and permission tests (need PostgreSQL).
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import GuardianToken
from app.core.errors import register_error_handlers
from app.core.security import create_access_token
from app.schemas.enums import UserRole

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"

# ES: Datos inventados, nunca reales. EN: Fake data, never real.
GUARDIAN = {
    "email": "Tutor.Prueba@Example.com",
    "password": "contraseña-larga-1",
    "display_name": "Lucía",
}


@pytest.fixture
def registered(api_client):
    response = api_client.post(REGISTER, json=GUARDIAN)
    assert response.status_code == 201
    return response.json()


def login(api_client, email=GUARDIAN["email"], password=GUARDIAN["password"]):
    return api_client.post(LOGIN, json={"email": email, "password": password})


# ---------- Registro / Sign-up ----------


def test_register_returns_user_without_password(registered):
    assert registered["role"] == "guardian"
    assert registered["email"] == "tutor.prueba@example.com"  # ES/EN: normalized
    assert "password" not in str(registered)


def test_register_duplicate_email_is_rejected(api_client, registered):
    response = api_client.post(
        REGISTER, json={**GUARDIAN, "email": "TUTOR.prueba@example.com"}
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "change",
    [{"password": "corta"}, {"email": "no-es-un-email"}, {"display_name": ""}],
)
def test_register_invalid_data(api_client, change):
    response = api_client.post(REGISTER, json={**GUARDIAN, **change})
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


# ---------- Login ----------


def test_login_returns_token(api_client, registered):
    response = login(api_client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


def test_wrong_password_and_unknown_email_look_the_same(api_client, registered):
    """ES: No revela qué emails existen. EN: Does not reveal which emails exist."""
    wrong_password = login(api_client, password="otra-contraseña-1")
    unknown_email = login(api_client, email="nadie@example.com")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]


# ---------- /me y permisos / /me and permissions ----------


def test_me_with_token(api_client, registered):
    token = login(api_client).json()["access_token"]
    response = api_client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["id"] == registered["id"]


def test_me_without_token(api_client):
    response = api_client.get(ME)
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_garbage_token(api_client):
    response = api_client.get(ME, headers={"Authorization": "Bearer abc.def.ghi"})
    assert response.status_code == 401


# ES: Ruta de prueba protegida por rol. EN: Role-protected test route.
roles_app = FastAPI()
register_error_handlers(roles_app)


@roles_app.get("/guardian-only")
def _guardian_only(token: GuardianToken):
    return {"sub": str(token.sub)}


@pytest.mark.parametrize(
    ("role", "status"),
    [(UserRole.GUARDIAN, 200), (UserRole.SENIOR, 403), (UserRole.ADMIN, 403)],
)
def test_require_role(role, status):
    token = create_access_token(uuid.uuid4(), role)
    response = TestClient(roles_app).get(
        "/guardian-only", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status
