"""Tests de la verificación de email del Tutor (necesitan PostgreSQL).
Guardian email verification tests (need PostgreSQL).

ES: Nunca se envía un correo de verdad: se captura el código con monkeypatch.
EN: No real email is ever sent: the code is captured with monkeypatch.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.api.v1 import auth as auth_routes
from app.core import email as email_module
from app.models.user import User

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
VERIFY = "/api/v1/auth/verify-email"
RESEND = "/api/v1/auth/resend-verification"

# ES: Datos inventados. EN: Fake data.
EMAIL = "nueva.tutora@example.com"
PASSWORD = "contraseña-larga-7"


@pytest.fixture
def outbox(monkeypatch):
    """ES: Guarda (destinatario, código) en lugar de enviar el correo.
    EN: Stores (recipient, code) instead of sending the email.
    """
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        auth_routes, "send_verification_email", lambda to, code: sent.append((to, code))
    )
    return sent


@pytest.fixture
def new_user(api_client, db_session, outbox):
    body = {"email": EMAIL, "password": PASSWORD, "display_name": "Ana"}
    response = api_client.post(REGISTER, json=body)
    assert response.status_code == 201
    return db_session.get(User, uuid.UUID(response.json()["id"]))


def login(api_client):
    return api_client.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})


def verify(api_client, code, email=EMAIL):
    return api_client.post(VERIFY, json={"email": email, "code": code})


def wrong(code):
    return f"{(int(code) + 1) % 1_000_000:06d}"


# ---------- Registro / sign-up ----------


def test_register_sends_a_6_digit_code(new_user, outbox):
    assert len(outbox) == 1
    to, code = outbox[0]
    assert to == EMAIL
    assert len(code) == 6 and code.isdigit()


def test_code_is_stored_hashed(new_user, outbox):
    code = outbox[0][1]
    assert new_user.verification_code_hash != code
    assert code not in new_user.verification_code_hash
    assert new_user.is_verified is False


def test_login_before_verifying_is_forbidden(api_client, new_user):
    response = login(api_client)
    assert response.status_code == 403
    assert "Verifica tu email" in response.json()["detail"]


# ---------- Verificar / verify ----------


def test_correct_code_verifies_and_allows_login(api_client, new_user, outbox):
    assert verify(api_client, outbox[0][1]).status_code == 204
    assert new_user.is_verified is True
    assert new_user.verification_code_hash is None
    assert login(api_client).status_code == 200


def test_wrong_code_is_rejected(api_client, new_user, outbox):
    response = verify(api_client, wrong(outbox[0][1]))
    assert response.status_code == 400
    assert new_user.verification_attempts == 1


def test_too_many_attempts_invalidate_the_code(api_client, new_user, outbox):
    code = outbox[0][1]
    for _ in range(5):
        verify(api_client, wrong(code))
    assert verify(api_client, code).status_code == 400
    assert new_user.is_verified is False


def test_expired_code_is_rejected(api_client, db_session, new_user, outbox):
    new_user.verification_code_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()
    assert verify(api_client, outbox[0][1]).status_code == 400


def test_unknown_email_gets_the_same_error(api_client, new_user, outbox):
    known = verify(api_client, wrong(outbox[0][1]))
    unknown = verify(api_client, "123456", email="nadie@example.com")
    assert unknown.status_code == known.status_code == 400
    assert unknown.json()["detail"] == known.json()["detail"]


def test_code_must_be_6_digits(api_client, new_user):
    assert verify(api_client, "12ab").status_code == 422


# ---------- Reenviar / resend ----------


def test_resend_within_cooldown_sends_nothing(api_client, new_user, outbox):
    response = api_client.post(RESEND, json={"email": EMAIL})
    assert response.status_code == 202
    assert len(outbox) == 1


def test_resend_after_cooldown_replaces_the_code(
    api_client, db_session, new_user, outbox
):
    new_user.verification_code_expires_at = datetime.now(UTC) + timedelta(minutes=1)
    db_session.flush()
    api_client.post(RESEND, json={"email": EMAIL})
    assert len(outbox) == 2
    old_code, new_code = outbox[0][1], outbox[1][1]
    if old_code != new_code:
        assert verify(api_client, old_code).status_code == 400
    assert verify(api_client, new_code).status_code == 204


def test_resend_unknown_email_looks_the_same(api_client, outbox):
    response = api_client.post(RESEND, json={"email": "nadie@example.com"})
    assert response.status_code == 202
    assert outbox == []


def test_verified_user_gets_no_new_code(api_client, guardian, outbox):
    api_client.post(RESEND, json={"email": guardian.email})
    assert outbox == []


# ---------- Correo / email ----------


def test_email_only_carries_the_code():
    message = email_module.build_verification_email(EMAIL, "123456")
    assert message["To"] == EMAIL
    assert "123456" in message.get_content()
    assert "token" not in message.get_content().lower()


def test_smtp_sender_uses_tls_and_login(monkeypatch):
    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self, context):
            calls.append(("starttls",))

        def login(self, user, password):
            calls.append(("login", user))

        def send_message(self, message):
            calls.append(("send", message["To"]))

    monkeypatch.setattr(email_module.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(email_module.settings, "MAIL_USERNAME", "avizor@example.com")
    email_module.SmtpEmailSender().send(
        email_module.build_verification_email(EMAIL, "123456")
    )
    assert [c[0] for c in calls] == ["connect", "starttls", "login", "send"]


def test_failed_send_never_raises(monkeypatch):
    class BrokenSender:
        def send(self, message):
            raise OSError("Gmail caído")

    monkeypatch.setattr(email_module, "get_email_sender", lambda: BrokenSender())
    email_module.send_verification_email(EMAIL, "123456")
