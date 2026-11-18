"""Envío de correos (verificación de email y recuperación de contraseña).
Email sending (email verification and password recovery).

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


def build_password_reset_email(to: str, link: str) -> EmailMessage:
    """ES: Texto fijo; el enlace es de un solo uso y caduca.
    EN: Fixed text; the link is single-use and expires.
    """
    message = EmailMessage()
    message["From"] = settings.MAIL_FROM or settings.MAIL_USERNAME or "avizor"
    message["To"] = to
    message["Subject"] = "Avizor: cambia tu contraseña"
    message.set_content(
        f"Hola,\n\n"
        f"Hemos recibido una solicitud para cambiar la contraseña de tu cuenta "
        f"de Avizor. Abre este enlace para elegir una nueva:\n\n"
        f"{link}\n\n"
        f"El enlace caduca en {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutos "
        f"y solo se puede usar una vez.\n"
        f"Si no lo has pedido tú, ignora este correo: tu contraseña no cambia.\n\n"
        f"Equipo Avizor"
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
