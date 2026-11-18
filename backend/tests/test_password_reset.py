"""Tests de la recuperación de contraseña del Tutor (necesitan PostgreSQL).
Guardian password recovery tests (need PostgreSQL).

ES: Nunca se envía un correo de verdad: se captura el enlace con monkeypatch.
EN: No real email is ever sent: the link is captured with monkeypatch.
"""

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from app.api.v1 import auth as auth_routes
from app.core import email as email_module
from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.schemas.enums import UserRole
from app.services import password_reset

FORGOT = "/api/v1/auth/forgot-password"
RESET = "/api/v1/auth/reset-password"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"

# ES: Datos inventados. EN: Fake data.
EMAIL = "olvido.tutora@example.com"
OLD_PASSWORD = "contraseña-vieja-1"
NEW_PASSWORD = "contraseña-nueva-2"
GENERIC = "Si la cuenta existe, recibirás un correo para cambiar la contraseña."


@pytest.fixture
def outbox(monkeypatch):
    """ES: Guarda (destinatario, enlace) en lugar de enviar el correo.
    EN: Stores (recipient, link) instead of sending the email.
    """
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        auth_routes,
        "send_password_reset_email",
        lambda to, link: sent.append((to, link)),
    )
    return sent


@pytest.fixture
def tutor(db_session):
    user = User(
        role=UserRole.GUARDIAN,
        display_name="Lucía",
        email=EMAIL,
        password_hash=hash_password(OLD_PASSWORD),
        is_verified=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


def token_from(link: str) -> str:
    return parse_qs(urlparse(link).query)["token"][0]


def ask_link(api_client, outbox, email=EMAIL) -> str:
    response = api_client.post(FORGOT, json={"email": email})
    assert response.status_code == 202
    return token_from(outbox[-1][1])


def reset(api_client, token, password=NEW_PASSWORD):
    return api_client.post(RESET, json={"token": token, "new_password": password})


def login(api_client, password):
    return api_client.post(LOGIN, json={"email": EMAIL, "password": password})


# ---------- forgot-password ----------


def test_forgot_sends_link_to_frontend(api_client, tutor, outbox):
    response = api_client.post(FORGOT, json={"email": "  Olvido.Tutora@Example.com "})
    assert response.status_code == 202
    assert response.json()["message"] == GENERIC
    assert len(outbox) == 1
    to, link = outbox[0]
    assert to == EMAIL
    assert link.startswith("http://localhost:8000/reset-password?token=")


def test_unknown_email_gets_same_answer_and_no_email(api_client, outbox):
    response = api_client.post(FORGOT, json={"email": "nadie@example.com"})
    assert response.status_code == 202
    assert response.json()["message"] == GENERIC
    assert outbox == []


def test_senior_and_deleted_users_get_no_email(api_client, db_session, outbox):
    db_session.add(User(role=UserRole.SENIOR, display_name="Abuela"))
    db_session.add(
        User(
            role=UserRole.GUARDIAN,
            display_name="Borrada",
            email="borrada@example.com",
            password_hash=hash_password(OLD_PASSWORD),
            deleted_at=datetime.now(UTC),
        )
    )
    db_session.flush()
    response = api_client.post(FORGOT, json={"email": "borrada@example.com"})
    assert response.status_code == 202
    assert outbox == []


# ---------- reset-password ----------


def test_reset_changes_password(api_client, tutor, outbox):
    token = ask_link(api_client, outbox)
    assert reset(api_client, token).status_code == 204
    assert login(api_client, OLD_PASSWORD).status_code == 401
    assert login(api_client, NEW_PASSWORD).status_code == 200


def test_link_works_only_once(api_client, tutor, outbox):
    token = ask_link(api_client, outbox)
    assert reset(api_client, token).status_code == 204
    second = reset(api_client, token, "otra-contraseña-3")
    assert second.status_code == 400
    assert "no es válido o ha caducado" in second.json()["detail"]


def test_reset_invalidates_other_pending_links(api_client, tutor, outbox):
    first = ask_link(api_client, outbox)
    second = ask_link(api_client, outbox)
    assert reset(api_client, second).status_code == 204
    assert reset(api_client, first, "otra-contraseña-3").status_code == 400


def test_expired_link_is_rejected(api_client, tutor):
    old = datetime.now(UTC) - timedelta(minutes=16)
    token = password_reset.create_reset_token(tutor, now=old)
    assert reset(api_client, token).status_code == 400


def test_tampered_or_garbage_token_is_rejected(api_client, tutor, outbox):
    token = ask_link(api_client, outbox)
    assert reset(api_client, token[:-2] + "xx").status_code == 400
    assert reset(api_client, "no-es-un-token").status_code == 400


def test_access_token_cannot_reset_password(api_client, tutor):
    session_token = create_access_token(tutor.id, UserRole.GUARDIAN)
    assert reset(api_client, session_token).status_code == 400


def test_reset_token_cannot_be_used_as_session(api_client, tutor, outbox):
    token = ask_link(api_client, outbox)
    response = api_client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_short_password_is_rejected(api_client, tutor, outbox):
    token = ask_link(api_client, outbox)
    assert reset(api_client, token, "corta").status_code == 422
    # ES: El enlace sigue valiendo. EN: The link still works.
    assert reset(api_client, token).status_code == 204


def test_reset_also_verifies_the_email(api_client, db_session, tutor, outbox):
    tutor.is_verified = False
    db_session.flush()
    token = ask_link(api_client, outbox)
    assert reset(api_client, token).status_code == 204
    assert login(api_client, NEW_PASSWORD).status_code == 200


def test_token_does_not_contain_password_hash(api_client, tutor, outbox):
    token = ask_link(api_client, outbox)
    assert tutor.password_hash not in token
    assert "argon2" not in token


# ---------- correo / email ----------


def test_reset_email_text(monkeypatch):
    monkeypatch.setattr(email_module.settings, "MAIL_FROM", "avizor@example.com")
    link = "http://localhost:8000/reset-password?token=abc"
    message = email_module.build_password_reset_email(EMAIL, link)
    assert message["To"] == EMAIL
    assert link in message.get_content()
    assert "15 minutos" in message.get_content()


def test_send_failure_does_not_raise(monkeypatch):
    class Broken:
        def send(self, message):
            raise OSError("smtp down")

    monkeypatch.setattr(email_module, "get_email_sender", lambda: Broken())
    email_module.send_password_reset_email(EMAIL, "http://x/reset-password?token=a")
