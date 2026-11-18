"""Endpoint de datos del Sénior vinculado al Tutor (Contrato v1.0.0 — MINOR).
Senior data endpoint for the authenticated guardian (Contract v1.0.0 — MINOR).
"""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession, GuardianToken
from app.core.errors import ApiError
from app.models.user import Device, Pairing
from app.schemas.enums import ErrorCode
from app.schemas.senior import SeniorOut

router = APIRouter(tags=["senior"])


@router.get("/senior")
def get_senior(db: DbSession, token: GuardianToken) -> SeniorOut:
    """ES: Devuelve los datos del Sénior activo vinculado al Tutor autenticado.
    404 si aún no hay vinculación activa.

    EN: Returns the active senior linked to the authenticated guardian.
    404 if there is no active pairing yet.
    """
    row = db.execute(
        select(Pairing, Device)
        .outerjoin(Device, Device.user_id == Pairing.senior_id)
        .where(
            Pairing.guardian_id == token.sub,
            Pairing.senior_id.is_not(None),
            Pairing.active.is_(True),
        )
        .limit(1)
    ).first()

    if row is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "No tienes un Sénior vinculado.")

    pairing, device = row
    return SeniorOut(
        senior_display_name=pairing.senior_display_name,
        platform=device.platform if device else None,
        app_version=device.app_version if device else None,
        last_seen_at=device.last_seen_at if device else None,
        paired_since=pairing.redeemed_at,
    )
