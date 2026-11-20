"""Tests del envío por Brevo (sin red: httpx.MockTransport).
Brevo sending tests (no network: httpx.MockTransport).
"""

import json

import httpx
import pytest
from pydantic import SecretStr

from app.core import email as email_module

# ES: Datos inventados. EN: Fake data.
KEY = "xkeysib-prueba-no-real"
TO = "tutora.prueba@example.com"


@pytest.fixture
def brevo_settings(monkeypatch):
    monkeypatch.setattr(email_module.settings, "BREVO_API_KEY", SecretStr(KEY))
    monkeypatch.setattr(email_module.settings, "MAIL_FROM", "avizor@example.com")


def sender_with(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return email_module.BrevoEmailSender(client=client)


def test_sends_expected_request(brevo_settings):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["key"] = request.headers["api-key"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(201, json={"messageId": "<id@brevo>"})

    message = email_module.build_verification_email(TO, "123456")
    sender_with(handler).send(message)

    assert seen["url"] == "https://api.brevo.com/v3/smtp/email"
    assert seen["key"] == KEY
    body = seen["body"]
    assert body["sender"] == {"name": "Avizor", "email": "avizor@example.com"}
    assert body["to"] == [{"email": TO}]
    assert body["subject"] == "Avizor: tu código de verificación"
    assert "123456" in body["textContent"]


def test_sender_name_from_mail_from(monkeypatch, brevo_settings):
    monkeypatch.setattr(email_module.settings, "MAIL_FROM", "Equipo Avizor <a@b.com>")
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(201, json={})

    sender_with(handler).send(email_module.build_verification_email(TO, "111111"))
    assert seen["body"]["sender"] == {"name": "Equipo Avizor", "email": "a@b.com"}


def test_error_response_raises_without_key(brevo_settings):
    def handler(request):
        return httpx.Response(401, json={"code": "unauthorized"})

    with pytest.raises(RuntimeError) as error:
        sender_with(handler).send(email_module.build_verification_email(TO, "1"))
    assert "401" in str(error.value)
    assert KEY not in str(error.value)


def test_missing_key_raises(monkeypatch):
    monkeypatch.setattr(email_module.settings, "BREVO_API_KEY", SecretStr(""))
    calls = []
    sender = sender_with(lambda request: calls.append(request))
    with pytest.raises(RuntimeError, match="BREVO_API_KEY"):
        sender.send(email_module.build_verification_email(TO, "1"))
    assert calls == []


def test_provider_selection(monkeypatch):
    monkeypatch.setattr(email_module.settings, "MAIL_PROVIDER", "brevo")
    assert isinstance(email_module.get_email_sender(), email_module.BrevoEmailSender)
    monkeypatch.setattr(email_module.settings, "MAIL_PROVIDER", "log")
    assert isinstance(email_module.get_email_sender(), email_module.LogEmailSender)


def test_brevo_failure_does_not_break_registration_flow(monkeypatch, brevo_settings):
    # ES: Si Brevo falla, send_verification_email lo registra y no lanza.
    # EN: If Brevo fails, send_verification_email logs it and does not raise.
    def handler(request):
        return httpx.Response(500, text="down")

    monkeypatch.setattr(email_module, "get_email_sender", lambda: sender_with(handler))
    email_module.send_verification_email(TO, "123456")
    email_module.send_password_reset_email(TO, "http://x/reset-password?token=a")


# ---------- Textos / texts ----------


def test_verification_text_explains_steps_and_warns():
    text = email_module.build_verification_email(TO, "772427").get_content()
    assert "772427" in text
    assert "Verifica tu email" in text
    assert "Reenviar" in text
    assert "nunca te pedirá este código" in text
    assert "http" not in text


def test_reset_text_explains_steps_and_sessions():
    link = "https://avizor.example/reset-password?token=abc"
    text = email_module.build_password_reset_email(TO, link).get_content()
    assert link in text
    assert "Guardar contraseña" in text
    assert "se cerrará la sesión" in text
    assert "¿Olvidaste tu contraseña?" in text
