"""Quién es quién: dispositivo → Sénior y vínculo Tutor ↔ Sénior.
Who is who: device → senior and guardian ↔ senior link.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import TokenPayload
from app.models.user import Device, Pairing, User
from app.schemas.enums import ErrorCode, UserRole

# ES: Roles cuyo token lleva el id del dispositivo (sub = device_id).
# EN: Roles whose token carries the device id (sub = device_id).
DEVICE_ROLES = (UserRole.SENIOR, UserRole.SENIOR_SOLO)


def senior_id_from_device(db: Session, device_id: uuid.UUID) -> uuid.UUID:
    """ES: El token del Sénior lleva el id del dispositivo; devuelve su usuario.
    EN: The senior token carries the device id; returns its user.
    """
    senior_id = db.scalar(
        select(Device.user_id)
        .join(User, User.id == Device.user_id)
        .where(
            Device.id == device_id,
            User.role.in_(DEVICE_ROLES),
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


def request_device_id(token: TokenPayload, device_id: uuid.UUID | None) -> uuid.UUID:
    """ES: Dispositivo de la petición. senior_solo puede omitirlo (se usa el de su
    token); el Sénior vinculado debe enviarlo y coincidir con su token.
    EN: Request device. senior_solo may omit it (its token's device is used); a
    paired senior must send it and it must match the token.
    """
    if device_id is None:
        if token.role == UserRole.SENIOR_SOLO:
            return token.sub
        raise ApiError(422, ErrorCode.VALIDATION_ERROR, "Falta device_id.")
    if device_id != token.sub:
        raise ApiError(403, ErrorCode.FORBIDDEN, "El dispositivo no coincide.")
    return device_id
