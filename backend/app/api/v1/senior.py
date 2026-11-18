"""Endpoints de datos del Sénior (Contrato v1.0.0 — MINOR).
Senior data endpoints (Contract v1.0.0 — MINOR).

GET /api/v1/senior     (guardian) → SeniorRead | 404
GET /api/v1/senior/me  (senior)   → SeniorProfileRead | 404
"""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession, GuardianToken, SeniorToken
from app.core.errors import ApiError
from app.models.user import Device, Pairing, User
from app.schemas.enums import ErrorCode
from app.schemas.senior import SeniorProfileRead, SeniorRead

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
    return SeniorProfileRead(
        display_name=senior.display_name,
        accessibility_profile=senior.accessibility_profile,
    )
