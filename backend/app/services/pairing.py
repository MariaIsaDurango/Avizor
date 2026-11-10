"""Lógica de vinculación Tutor ↔ Sénior.
Guardian ↔ Senior pairing logic.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError
from app.core.security import create_access_token
from app.models.user import Device, Pairing, User
from app.schemas.enums import ErrorCode, UserRole
from app.schemas.pairing import (
    PairingCreate,
    PairingRead,
    PairingRedeem,
    PairingRedeemResponse,
)

MAX_CODE_ATTEMPTS = 10


def _new_code() -> str:
    """ES: 6 dígitos con generador criptográfico (no random).
    EN: 6 digits from a cryptographic generator (not random).
    """
    return f"{secrets.randbelow(1_000_000):06d}"


def _code_in_use(db: Session, code: str, now: datetime) -> bool:
    return (
        db.scalar(
            select(Pairing.id).where(
                Pairing.code == code,
                Pairing.active.is_(True),
                Pairing.redeemed_at.is_(None),
                Pairing.expires_at > now,
            )
        )
        is not None
    )


def create_pairing(
    db: Session, guardian_id: uuid.UUID, body: PairingCreate
) -> PairingRead:
    now = datetime.now(UTC)
    for _ in range(MAX_CODE_ATTEMPTS):
        code = _new_code()
        if not _code_in_use(db, code, now):
            break
    else:
        raise ApiError(500, ErrorCode.INTERNAL_ERROR, "No se pudo generar el código.")

    pairing = Pairing(
        guardian_id=guardian_id,
        code=code,
        senior_display_name=body.senior_display_name,
        expires_at=now + timedelta(minutes=settings.PAIRING_CODE_EXPIRE_MINUTES),
    )
    db.add(pairing)
    db.commit()
    return PairingRead.model_validate(pairing, from_attributes=True)


def redeem_pairing(db: Session, body: PairingRedeem) -> PairingRedeemResponse:
    now = datetime.now(UTC)
    # ES: FOR UPDATE bloquea la fila: dos móviles no pueden canjear el mismo código.
    # EN: FOR UPDATE locks the row: two phones cannot redeem the same code.
    pairing = db.scalar(
        select(Pairing)
        .where(
            Pairing.code == body.code,
            Pairing.active.is_(True),
            Pairing.redeemed_at.is_(None),
        )
        .order_by(Pairing.expires_at.desc())
        .with_for_update()
    )
    if pairing is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "El código no es válido.")
    if pairing.expires_at <= now:
        raise ApiError(
            410, ErrorCode.PAIRING_EXPIRED, "Pide a tu familiar un código nuevo."
        )

    senior = User(role=UserRole.SENIOR, display_name=pairing.senior_display_name)
    db.add(senior)
    db.flush()  # ES: genera senior.id / EN: generates senior.id

    device = Device(
        user_id=senior.id,
        platform=body.device.platform,
        app_version=body.device.app_version,
        push_token=body.device.push_token,
        last_seen_at=now,
    )
    db.add(device)
    db.flush()

    pairing.senior_id = senior.id
    pairing.redeemed_at = now
    db.commit()

    # ES: El token del Sénior identifica al dispositivo (sub = device.id).
    # EN: The senior token identifies the device (sub = device.id).
    token = create_access_token(
        device.id,
        UserRole.SENIOR,
        expires_minutes=settings.DEVICE_TOKEN_EXPIRE_DAYS * 24 * 60,
    )
    return PairingRedeemResponse(
        access_token=token, device_id=device.id, senior_id=senior.id
    )
