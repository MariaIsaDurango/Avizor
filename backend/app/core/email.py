"""Envío de correos (verificación de email del Tutor).
Email sending (guardian email verification).

ES: Con MAIL_PROVIDER=log (desarrollo y CI) no sale nada a internet: el código
    se escribe en la terminal. Con "smtp" se envía por Gmail.
EN: With MAIL_PROVIDER=log (development and CI) nothing goes to the internet:
    the code is written to the terminal. With "smtp" it is sent through Gmail.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol

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


def get_email_sender() -> EmailSender:
    if settings.MAIL_PROVIDER == "smtp":
        return SmtpEmailSender()
    return LogEmailSender()


def build_verification_email(to: str, code: str) -> EmailMessage:
    """ES: Texto fijo; solo lleva el código, nunca el token de sesión.
    EN: Fixed text; it only carries the code, never the session token.
    """
    message = EmailMessage()
    message["From"] = settings.MAIL_FROM or settings.MAIL_USERNAME or "avizor"
    message["To"] = to
    message["Subject"] = "Avizor: tu código de verificación"
    message.set_content(
        f"Hola,\n\n"
        f"Tu código para verificar tu cuenta de Avizor es: {code}\n\n"
        f"Caduca en {settings.EMAIL_CODE_EXPIRE_MINUTES} minutos.\n"
        f"Si no has creado una cuenta en Avizor, ignora este correo.\n\n"
        f"Equipo Avizor"
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
