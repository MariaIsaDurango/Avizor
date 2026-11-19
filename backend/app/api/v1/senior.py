"""Endpoints de datos del Sénior (Contrato v1.0.0 — MINOR).
Senior data endpoints (Contract v1.0.0 — MINOR).

GET  /api/v1/senior        (guardian) → SeniorRead | 404
GET  /api/v1/senior/me     (senior)   → SeniorProfileRead | 404
POST /api/v1/senior/logout (senior)   → 200
"""

import logging

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession, GuardianToken, SeniorToken
from app.core.errors import ApiError
from app.models.user import Device, Pairing, User
from app.schemas.enums import ErrorCode
from app.schemas.senior import SeniorProfileRead, SeniorRead
from app.services import push as push_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["senior"])


@router.get("/senior")
def get_senior(db: DbSession, token: GuardianToken) -> SeniorRead:
    """ES: Devuelve los datos del Sénior activo vinculado al Tutor autenticado.
    404 si aún no hay vinculación activa.

    EN: Returns the active senior linked to the authenticated guardian.
    404 if there is no active pairing yet.
    """
    row = db.execute(
        select(Pairing, Device, User)
        .join(User, User.id == Pairing.senior_id)
        .outerjoin(Device, Device.user_id == Pairing.senior_id)
        .where(
            Pairing.guardian_id == token.sub,
            Pairing.senior_id.is_not(None),
            Pairing.active.is_(True),
        )
        .order_by(Pairing.redeemed_at.desc(), Device.last_seen_at.desc().nulls_last())
        .limit(1)
    ).first()

    if row is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "No tienes un Sénior vinculado.")

    pairing, device, senior = row
    return SeniorRead(
        senior_display_name=pairing.senior_display_name,
        platform=device.platform if device else None,
        app_version=device.app_version if device else None,
        last_seen_at=device.last_seen_at if device else None,
        paired_since=pairing.redeemed_at,
        accessibility_profile=senior.accessibility_profile,
    )


@router.get("/senior/me")
def get_my_profile(db: DbSession, token: SeniorToken) -> SeniorProfileRead:
    """ES: La app del Sénior recupera su perfil (p. ej. al reiniciar sesión).
    El token del Sénior identifica al dispositivo (sub = device.id).
    EN: The senior app fetches its own profile (e.g. after restarting).
    The senior token identifies the device (sub = device.id).
    """
    senior = db.scalar(
        select(User)
        .join(Device, Device.user_id == User.id)
        .where(Device.id == token.sub, User.deleted_at.is_(None))
    )
    if senior is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "Dispositivo no encontrado.")
    guardian_phone = db.scalar(
        select(Pairing.guardian_phone)
        .where(Pairing.senior_id == senior.id, Pairing.active.is_(True))
        .order_by(Pairing.redeemed_at.desc())
        .limit(1)
    )
    return SeniorProfileRead(
        display_name=senior.display_name,
        accessibility_profile=senior.accessibility_profile,
        guardian_phone=guardian_phone,
    )


@router.post("/senior/logout", status_code=200)
def notify_senior_logout(db: DbSession, token: SeniorToken) -> None:
    """ES: El Sénior avisa al Tutor de que ha cerrado sesión. No bloquea el logout
    aunque el push falle — el dispositivo limpia su token independientemente.
    EN: The senior notifies the guardian that they have logged out. Does not block
    logout if the push fails — the device clears its token regardless.
    """
    senior = db.scalar(
        select(User)
        .join(Device, Device.user_id == User.id)
        .where(Device.id == token.sub, User.deleted_at.is_(None))
    )
    if senior is None:
        return
    try:
        push_service.send_logout_push(
            db, senior.id, senior.display_name, push_service.get_sender()
        )
    except Exception:
        logger.exception("Logout push failed for senior %s", senior.id)
