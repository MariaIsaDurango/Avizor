"""Tests de registro, login y permisos (necesitan PostgreSQL).
Sign-up, login and permission tests (need PostgreSQL).
"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.api.deps import GuardianToken
from app.api.v1.auth import _active_guardian
from app.core.errors import ApiError, register_error_handlers
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.models.user import User
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
def registered(api_client, db_session):
    """ES: Cuenta ya verificada; la verificación se prueba en
    test_email_verification.py.
    EN: Already verified account; verification is tested in
    test_email_verification.py.
    """
    response = api_client.post(REGISTER, json=GUARDIAN)
    assert response.status_code == 201
    user = db_session.get(User, uuid.UUID(response.json()["id"]))
    user.is_verified = True
    db_session.flush()
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
def test_require_role(db_session, role, status):
    # ES: Tutor y admin deben existir en la BD (se comprueba token_version).
    # EN: Guardians and admins must exist in the DB (token_version is checked).
    subject = uuid.uuid4()
    if role != UserRole.SENIOR:
        user = User(role=role, display_name="Rol", email=f"{role.value}@example.com")
        db_session.add(user)
        db_session.flush()
        subject = user.id
    token = create_access_token(subject, role)
    roles_app.dependency_overrides[get_db] = lambda: db_session
    try:
        response = TestClient(roles_app).get(
            "/guardian-only", headers={"Authorization": f"Bearer {token}"}
        )
    finally:
        roles_app.dependency_overrides.clear()
    assert response.status_code == status


# ---------- Casos defensivos de autenticación ----------


def test_register_integrity_error_returns_409(api_client, db_session, monkeypatch):
    def raise_integrity_error():
        raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    monkeypatch.setattr(db_session, "commit", raise_integrity_error)

    response = api_client.post(
        REGISTER,
        json={**GUARDIAN, "email": "concurrent@example.com"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_senior_solo_without_device_cannot_login(api_client, db_session):
    user = User(
        role=UserRole.SENIOR_SOLO,
        display_name="Senior sin dispositivo",
        email="senior.solo@example.com",
        password_hash=hash_password("contraseña-larga-1"),
        is_verified=True,
    )
    db_session.add(user)
    db_session.flush()

    response = login(
        api_client,
        email="senior.solo@example.com",
        password="contraseña-larga-1",
    )

    assert response.status_code == 401


@pytest.mark.parametrize("deleted", [False, True])
def test_me_rejects_missing_or_deleted_user(
    api_client, db_session, registered, deleted
):
    if deleted:
        user_id = uuid.UUID(registered["id"])
        user = db_session.get(User, user_id)
        user.deleted_at = datetime.now(UTC)
        db_session.flush()
    else:
        user_id = uuid.uuid4()

    token = create_access_token(user_id, UserRole.SENIOR)

    response = api_client.get(
        ME,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


# ---------- Rate limiting ----------


def test_login_rate_limit_returns_429(api_client, registered, monkeypatch):
    import app.core.config as cfg

    monkeypatch.setattr(cfg.settings, "APP_ENV", "production")
    for _ in range(10):
        login(api_client)
    response = login(api_client)
    assert response.status_code == 429
    assert response.json()["code"] == "RATE_LIMITED"


@pytest.mark.parametrize("deleted", [False, True])
def test_active_guardian_rejects_missing_or_deleted_user(db_session, deleted):
    if deleted:
        user = User(
            role=UserRole.GUARDIAN,
            display_name="Tutor eliminado",
            email="deleted.guardian@example.com",
        )
        db_session.add(user)
        db_session.flush()
        user_id = user.id
        user.deleted_at = datetime.now(UTC)
        db_session.flush()
    else:
        user_id = uuid.uuid4()

    with pytest.raises(ApiError):
        _active_guardian(db_session, user_id)
