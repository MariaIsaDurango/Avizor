"""Solicitudes de desbloqueo de falsos positivos.
Unlock requests for false positives.

ES: El Sénior pide desbloquear algo que se bloqueó por precaución; mientras
    espera ve un mensaje fijo (pending_guardian). Un Tutor vinculado aprueba o
    rechaza. Caduca a las 24 h. Si hay varios Tutores, decide el primero.
EN: The senior asks to unlock something blocked as a precaution; while waiting
    they see a fixed message (pending_guardian). A paired guardian approves or
    rejects. Expires after 24 h. With several guardians, the first one decides.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import TokenPayload
from app.models.alert import Unlock
from app.models.analysis import Analysis
from app.models.user import Device, Pairing
from app.schemas.enums import Action, ErrorCode, UnlockStatus, UserRole
from app.schemas.unlock import Unlock as UnlockSchema
from app.schemas.unlock import UnlockCreate, UnlockUpdate
from app.services.identity import is_paired, senior_id_from_device

UNLOCK_TTL = timedelta(hours=24)


def _not_found() -> ApiError:
    # ES: 404 también sin permiso: no revela que existe.
    # EN: 404 also without permission: does not reveal it exists.
    return ApiError(404, ErrorCode.NOT_FOUND, "Solicitud no encontrada.")


def _senior_of_analysis(db: Session, analysis_id: uuid.UUID) -> uuid.UUID | None:
    return db.scalar(
        select(Device.user_id)
        .join(Analysis, Analysis.device_id == Device.id)
        .where(Analysis.id == analysis_id)
    )


def _expire_if_needed(db: Session, unlock: Unlock, now: datetime) -> None:
    """ES: Caducidad perezosa: se marca al leerla (además del trabajo horario).
    EN: Lazy expiry: marked when read (in addition to the hourly job).
    """
    if unlock.status == UnlockStatus.PENDING_GUARDIAN and unlock.expires_at <= now:
        unlock.status = UnlockStatus.EXPIRED
        db.commit()


def _to_schema(unlock: Unlock) -> UnlockSchema:
    return UnlockSchema.model_validate(unlock, from_attributes=True)


def create_unlock(db: Session, token: TokenPayload, body: UnlockCreate) -> UnlockSchema:
    now = datetime.now(UTC)
    senior_id = senior_id_from_device(db, token.sub)
    analysis = db.get(Analysis, body.analysis_id)
    if analysis is None or _senior_of_analysis(db, analysis.id) != senior_id:
        raise ApiError(404, ErrorCode.NOT_FOUND, "Análisis no encontrado.")
    if analysis.action == Action.ALLOW:
        raise ApiError(
            422, ErrorCode.VALIDATION_ERROR, "Este contenido no está bloqueado."
        )

    # ES: Idempotente: si ya hay una pendiente, se devuelve la misma.
    # EN: Idempotent: if one is already pending, the same one is returned.
    pending = db.scalar(
        select(Unlock).where(
            Unlock.analysis_id == analysis.id,
            Unlock.status == UnlockStatus.PENDING_GUARDIAN,
            Unlock.expires_at > now,
        )
    )
    if pending:
        return _to_schema(pending)

    unlock = Unlock(
        analysis_id=analysis.id,
        status=UnlockStatus.PENDING_GUARDIAN,
        requested_at=now,
        expires_at=now + UNLOCK_TTL,
    )
    db.add(unlock)
    db.commit()
    return _to_schema(unlock)


def _can_see(db: Session, token: TokenPayload, unlock: Unlock) -> bool:
    senior_id = _senior_of_analysis(db, unlock.analysis_id)
    if token.role == UserRole.SENIOR:
        return senior_id_from_device(db, token.sub) == senior_id
    if token.role == UserRole.GUARDIAN:
        return senior_id is not None and is_paired(db, token.sub, senior_id)
    return False


def get_unlock(db: Session, token: TokenPayload, unlock_id: uuid.UUID) -> UnlockSchema:
    unlock = db.get(Unlock, unlock_id)
    if unlock is None or not _can_see(db, token, unlock):
        raise _not_found()
    _expire_if_needed(db, unlock, datetime.now(UTC))
    return _to_schema(unlock)


def list_pending_for_guardian(
    db: Session, guardian_id: uuid.UUID
) -> list[UnlockSchema]:
    now = datetime.now(UTC)
    rows = db.scalars(
        select(Unlock)
        .join(Analysis, Analysis.id == Unlock.analysis_id)
        .join(Device, Device.id == Analysis.device_id)
        .join(Pairing, Pairing.senior_id == Device.user_id)
        .where(
            Pairing.guardian_id == guardian_id,
            Pairing.active.is_(True),
            Unlock.status == UnlockStatus.PENDING_GUARDIAN,
            Unlock.expires_at > now,
        )
        .order_by(Unlock.requested_at.desc())
    ).all()
    return [_to_schema(unlock) for unlock in rows]


def resolve_unlock(
    db: Session, token: TokenPayload, unlock_id: uuid.UUID, body: UnlockUpdate
) -> UnlockSchema:
    now = datetime.now(UTC)
    # ES: FOR UPDATE: si dos Tutores responden a la vez, solo cuenta el primero.
    # EN: FOR UPDATE: if two guardians answer at once, only the first counts.
    unlock = db.scalar(select(Unlock).where(Unlock.id == unlock_id).with_for_update())
    if unlock is None or not _can_see(db, token, unlock):
        raise _not_found()

    _expire_if_needed(db, unlock, now)
    if unlock.status != UnlockStatus.PENDING_GUARDIAN:
        raise ApiError(
            409,
            ErrorCode.VALIDATION_ERROR,
            "Esta solicitud ya no está pendiente.",
        )

    unlock.status = body.status
    unlock.resolved_by = token.sub
    unlock.resolved_at = now
    db.commit()
    return _to_schema(unlock)
