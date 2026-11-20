"""Envío de correos (verificación de email y recuperación de contraseña).
Email sending (email verification and password recovery).

ES: Con MAIL_PROVIDER=log (desarrollo y CI) no sale nada a internet: el código
    se escribe en la terminal. Con "smtp" se envía por Gmail (local). Con
    "brevo" se envía por la API HTTPS de Brevo (Railway).
EN: With MAIL_PROVIDER=log (development and CI) nothing goes to the internet:
    the code is written to the terminal. With "smtp" it is sent through Gmail
    (local). With "brevo" it is sent through Brevo's HTTPS API (Railway).
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import parseaddr
from typing import Protocol

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class LogEmailSender:
    """ES: Solo para desarrollo. EN: Development only."""

    def send(self, message: EmailMessage) -> None:
        logger.warning(
            "Email (log only) to %s: %s\n%s",
            message["To"],
            message["Subject"],
            message.get_content(),
        )


class SmtpEmailSender:
    def send(self, message: EmailMessage) -> None:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT, timeout=10) as smtp:
            # ES: STARTTLS: la conexión va cifrada. EN: STARTTLS: encrypted connection.
            smtp.starttls(context=context)
            smtp.login(settings.MAIL_USERNAME or "", settings.MAIL_PASSWORD or "")
            smtp.send_message(message)


class BrevoEmailSender:
    """ES: Envía por la API HTTPS de Brevo (POST /v3/smtp/email). El remitente
    (MAIL_FROM) tiene que estar verificado en Brevo. La clave nunca se escribe
    en el log.
    EN: Sends through Brevo's HTTPS API (POST /v3/smtp/email). The sender
    (MAIL_FROM) must be verified in Brevo. The key is never logged.
    """

    URL = "https://api.brevo.com/v3/smtp/email"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=10)

    def send(self, message: EmailMessage) -> None:
        api_key = settings.BREVO_API_KEY.get_secret_value()
        if not api_key:
            raise RuntimeError("BREVO_API_KEY is not configured")
        name, address = parseaddr(str(message["From"]))
        response = self.client.post(
            self.URL,
            headers={"api-key": api_key, "accept": "application/json"},
            json={
                "sender": {"name": name or "Avizor", "email": address},
                "to": [{"email": str(message["To"])}],
                "subject": str(message["Subject"]),
                "textContent": message.get_content(),
            },
        )
        if response.status_code >= 400:
            # ES: Solo el código y el mensaje de Brevo, nunca la clave ni el correo.
            # EN: Only Brevo's status and message, never the key or the email.
            raise RuntimeError(
                f"Brevo error {response.status_code}: {response.text[:200]}"
            )


def get_email_sender() -> EmailSender:
    if settings.MAIL_PROVIDER == "smtp":
        return SmtpEmailSender()
    if settings.MAIL_PROVIDER == "brevo":
        return BrevoEmailSender()
    return LogEmailSender()


def build_verification_email(to: str, code: str) -> EmailMessage:
    """ES: Texto fijo; solo lleva el código, nunca el token de sesión.
    EN: Fixed text; it only carries the code, never the session token.
    """
    message = EmailMessage()
    message["From"] = settings.MAIL_FROM or settings.MAIL_USERNAME or "avizor"
    message["To"] = to
    message["Subject"] = "Avizor: tu código de verificación"
    # ES: Texto amable con pasos claros. Nunca lleva enlaces ni datos de sesión.
    # EN: Friendly text with clear steps. It never carries links or session data.
    message.set_content(
        "Hola:\n\n"
        "Gracias por unirte a Avizor. Ya casi está: solo falta confirmar que "
        "este correo es tuyo.\n\n"
        "Tu código de verificación es:\n\n"
        f"        {code}\n\n"
        "Cómo usarlo:\n"
        '  1. Vuelve a la pantalla "Verifica tu email" de Avizor, en la app '
        "o en la web.\n"
        "  2. Escribe los 6 números del código.\n"
        '  3. Pulsa "Verificar". Después podrás iniciar sesión y vincular el '
        "móvil de tu familiar.\n\n"
        f"El código caduca en {settings.EMAIL_CODE_EXPIRE_MINUTES} minutos. Si "
        'caduca, pulsa "Reenviar" en esa misma pantalla y te enviaremos uno '
        "nuevo.\n\n"
        "Por tu seguridad: Avizor nunca te pedirá este código por teléfono, SMS "
        "ni WhatsApp. No se lo des a nadie.\n\n"
        "Si no has creado una cuenta en Avizor, puedes ignorar este correo.\n\n"
        "Un saludo,\n"
        "El equipo de Avizor"
    )
    return message


def send_verification_email(to: str, code: str) -> None:
    """ES: Tarea en segundo plano: si falla, se registra en el log y el usuario
    puede pedir otro código.
    EN: Background task: if it fails, it is logged and the user can request
    another code.
    """
    try:
        get_email_sender().send(build_verification_email(to, code))
    except Exception:
        logger.exception("Verification email could not be sent")


def build_password_reset_email(to: str, link: str) -> EmailMessage:
    """ES: Texto fijo; el enlace es de un solo uso y caduca.
    EN: Fixed text; the link is single-use and expires.
    """
    message = EmailMessage()
    message["From"] = settings.MAIL_FROM or settings.MAIL_USERNAME or "avizor"
    message["To"] = to
    message["Subject"] = "Avizor: cambia tu contraseña"
    # ES: Texto corto; avisa de que se cierran las sesiones (token_version).
    # EN: Short text; warns that sessions are closed (token_version).
    message.set_content(
        "Hola:\n\n"
        "Para cambiar tu contraseña de Avizor, abre este enlace:\n"
        f"{link}\n\n"
        'Escribe la nueva contraseña y pulsa "Guardar contraseña". Al '
        "guardarla, se cerrará la sesión en todos tus dispositivos.\n\n"
        f"El enlace caduca en {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutos "
        'y solo funciona una vez. Si caduca, pide otro en "¿Olvidaste tu '
        'contraseña?".\n\n'
        "Si no lo has pedido tú, ignora este correo: tu contraseña no cambia.\n\n"
        "El equipo de Avizor"
    )
    return message


def send_password_reset_email(to: str, link: str) -> None:
    """ES: Tarea en segundo plano; si falla, se registra y se puede pedir otro.
    EN: Background task; if it fails, it is logged and another can be requested.
    """
    try:
        get_email_sender().send(build_password_reset_email(to, link))
    except Exception:
        logger.exception("Password reset email could not be sent")
