"""Registro de los móviles del Tutor para las notificaciones push.
Registration of the guardian's phones for push notifications.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.user import Device
from app.schemas.device import GuardianDeviceRegister
from app.schemas.enums import ErrorCode


def register_guardian_device(
    db: Session, guardian_id: uuid.UUID, body: GuardianDeviceRegister
) -> Device:
    # ES: Si el móvil se usó con otra cuenta, el token pasa a esta
    #     (así la otra cuenta deja de recibir avisos en este móvil).
    # EN: If the phone was used with another account, the token moves here
    #     (so the other account stops getting alerts on this phone).
    db.execute(
        update(Device)
        .where(Device.push_token == body.push_token, Device.user_id != guardian_id)
        .values(push_token=None)
    )
    # ES: Mismo token = mismo móvil: se actualiza, no se duplica.
    # EN: Same token = same phone: updated, not duplicated.
    device = db.scalar(
        select(Device).where(
            Device.user_id == guardian_id, Device.push_token == body.push_token
        )
    )
    if device is None:
        device = Device(user_id=guardian_id, push_token=body.push_token)
        db.add(device)
    device.platform = body.platform
    device.app_version = body.app_version
    device.last_seen_at = datetime.now(UTC)
    db.commit()
    return device


def delete_guardian_device(
    db: Session, guardian_id: uuid.UUID, device_id: uuid.UUID
) -> None:
    """ES: Al cerrar sesión: ese móvil deja de recibir avisos.
    EN: On logout: that phone stops receiving alerts.
    """
    device = db.scalar(
        select(Device).where(Device.id == device_id, Device.user_id == guardian_id)
    )
    # ES: 404 también si es de otro usuario. EN: 404 also if it belongs to another.
    if device is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "Dispositivo no encontrado.")
    db.delete(device)
    db.commit()
