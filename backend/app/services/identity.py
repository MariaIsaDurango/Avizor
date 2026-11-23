"""Quién es quién: dispositivo → Sénior y vínculo Tutor ↔ Sénior.
Who is who: device → senior and guardian ↔ senior link.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.user import Device, Pairing, User
from app.schemas.enums import ErrorCode, UserRole


def senior_id_from_device(db: Session, device_id: uuid.UUID) -> uuid.UUID:
    """ES: El token del Sénior lleva el id del dispositivo; devuelve su usuario.
    EN: The senior token carries the device id; returns its user.
    """
    senior_id = db.scalar(
        select(Device.user_id)
        .join(User, User.id == Device.user_id)
        .where(
            Device.id == device_id,
            User.role == UserRole.SENIOR,
            User.deleted_at.is_(None),
        )
    )
    if senior_id is None:
        raise ApiError(401, ErrorCode.UNAUTHENTICATED, "Dispositivo no reconocido.")
    return senior_id


def is_paired(db: Session, guardian_id: uuid.UUID, senior_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(Pairing.id).where(
                Pairing.guardian_id == guardian_id,
                Pairing.senior_id == senior_id,
                Pairing.active.is_(True),
                Pairing.redeemed_at.is_not(None),
            )
        )
        is not None
    )
