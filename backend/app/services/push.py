"""Notificaciones push al Tutor cuando se crea una alerta red.
Push notifications to the guardian when a red alert is created.

ES: El push NO lleva contenido del mensaje (contrato): solo un aviso fijo y el
    alert_id. La app Tutor descarga el detalle con GET /alerts/{id}.
    Se envía a través del servicio push de Expo (usa FCM/APNs por debajo).
EN: The push has NO message content (contract): only a fixed notice and the
    alert_id. The guardian app downloads the detail with GET /alerts/{id}.
    Sent through Expo's push service (uses FCM/APNs underneath).
"""

import logging
import uuid
from typing import NamedTuple, Protocol

import httpx
from sqlalchemy import select, update
from sqlalchemy.orm import Session, aliased

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.alert import Alert
from app.models.analysis import Analysis
from app.models.user import Device, Pairing, User
from app.schemas.alert import LogoutNotification, PushNotification

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
# ES: Expo acepta hasta 100 mensajes por petición. EN: Expo accepts up to 100.
EXPO_BATCH_SIZE = 100
PUSH_TITLE = "Estafa bloqueada"


class PushMessage(NamedTuple):
    token: str
    notification: PushNotification | LogoutNotification


class PushSender(Protocol):
    def send(self, messages: list[PushMessage]) -> set[str]:
        """ES: Devuelve los tokens que ya no son válidos.
        EN: Returns the tokens that are no longer valid.
        """
        ...


class LogPushSender:
    """ES: Desarrollo y tests: no sale nada a internet.
    EN: Development and tests: nothing goes to the internet.
    """

    def send(self, messages: list[PushMessage]) -> set[str]:
        for message in messages:
            logger.info(
                "Push (log only) — type: %s", type(message.notification).__name__
            )
        return set()


class ExpoPushSender:
    def __init__(
        self, access_token: str | None = None, client: httpx.Client | None = None
    ) -> None:
        self.access_token = access_token
        self.client = client or httpx.Client(timeout=10)

    def send(self, messages: list[PushMessage]) -> set[str]:
        headers = {"Accept": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        invalid: set[str] = set()
        for start in range(0, len(messages), EXPO_BATCH_SIZE):
            batch = messages[start : start + EXPO_BATCH_SIZE]
            payload = [
                {
                    "to": message.token,
                    "title": message.notification.title,
                    "body": message.notification.body,
                    "data": message.notification.model_dump(mode="json"),
                    "sound": "default",
                    "priority": "high",
                }
                for message in batch
            ]
            response = self.client.post(EXPO_PUSH_URL, json=payload, headers=headers)
            response.raise_for_status()
            tickets = response.json().get("data", [])
            # ES: Expo devuelve un ticket por mensaje, en el mismo orden.
            # EN: Expo returns one ticket per message, in the same order.
            for message, ticket in zip(batch, tickets, strict=False):
                error = ticket.get("details", {}).get("error")
                if ticket.get("status") == "error" and error == "DeviceNotRegistered":
                    invalid.add(message.token)
        return invalid


def get_sender() -> PushSender:
    if settings.PUSH_PROVIDER == "expo":
        return ExpoPushSender(settings.EXPO_ACCESS_TOKEN)
    return LogPushSender()


def build_notification(alert_id: uuid.UUID, senior_name: str) -> PushNotification:
    """ES: Texto fijo; solo el nombre del Sénior, nunca el mensaje.
    EN: Fixed text; only the senior's name, never the message.
    """
    return PushNotification(
        alert_id=alert_id,
        title=PUSH_TITLE,
        body=f"Hemos bloqueado un intento de estafa en el móvil de {senior_name}.",
    )


def send_alert_pushes(
    db: Session, alert_ids: list[uuid.UUID], sender: PushSender
) -> int:
    """ES: Un push por cada móvil de cada Tutor. Devuelve cuántos se enviaron.
    EN: One push per phone of each guardian. Returns how many were sent.
    """
    senior_device = aliased(Device)
    senior = aliased(User)
    guardian_device = aliased(Device)
    rows = db.execute(
        select(Alert.id, senior.display_name, guardian_device.push_token)
        .join(Analysis, Analysis.id == Alert.analysis_id)
        .join(senior_device, senior_device.id == Analysis.device_id)
        .join(senior, senior.id == senior_device.user_id)
        .join(guardian_device, guardian_device.user_id == Alert.guardian_id)
        .where(Alert.id.in_(alert_ids), guardian_device.push_token.is_not(None))
    ).all()
    messages = [
        PushMessage(row.push_token, build_notification(row.id, row.display_name))
        for row in rows
    ]
    if not messages:
        return 0

    invalid = sender.send(messages)
    if invalid:
        # ES: App desinstalada: se borra el token para no reintentar.
        # EN: App uninstalled: the token is removed so it is not retried.
        db.execute(
            update(Device).where(Device.push_token.in_(invalid)).values(push_token=None)
        )
        db.commit()
    return len(messages)


def send_logout_push(
    db: Session, senior_id: uuid.UUID, senior_name: str, sender: PushSender
) -> int:
    """ES: Push a todos los dispositivos del Tutor cuando el Sénior cierra sesión.
    EN: Push to all guardian devices when the senior logs out.
    """
    tokens = db.scalars(
        select(Device.push_token)
        .join(Pairing, Pairing.guardian_id == Device.user_id)
        .where(
            Pairing.senior_id == senior_id,
            Pairing.active.is_(True),
            Device.push_token.is_not(None),
        )
        .distinct()
    ).all()
    if not tokens:
        return 0
    notification = LogoutNotification(
        body=f"{senior_name} ha cerrado sesión en Avizor."
    )
    messages = [PushMessage(token, notification) for token in tokens]
    invalid = sender.send(messages)
    if invalid:
        db.execute(
            update(Device).where(Device.push_token.in_(invalid)).values(push_token=None)
        )
        db.commit()
    return len(messages)


def send_alert_pushes_job(alert_ids: list[uuid.UUID]) -> None:
    """ES: Tarea en segundo plano, después de responder al Sénior.
    Si falla, se registra en el log: la alerta ya está guardada.
    EN: Background task, after replying to the senior.
    If it fails, it is logged: the alert is already stored.
    """
    try:
        with SessionLocal() as db:
            sent = send_alert_pushes(db, alert_ids, get_sender())
        logger.info("Push sent: %s message(s)", sent)
    except Exception:
        logger.exception("Push sending failed")
