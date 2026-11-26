"""Endpoints de datos del Sénior (Contrato v1.0.0 — MINOR).
Senior data endpoints (Contract v1.0.0 — MINOR).

GET    /api/v1/senior                (guardian) → SeniorRead | 404
PATCH  /api/v1/senior/accessibility  (guardian) → AccessibilityProfile | 404
DELETE /api/v1/senior                (guardian) → 204 | 404
GET    /api/v1/senior/me             (senior)   → SeniorProfileRead | 404
POST   /api/v1/senior/logout         (senior)   → 200
"""

import logging
import uuid

from fastapi import APIRouter, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DbSession, GuardianToken, SeniorToken
from app.core.errors import ApiError
from app.models.user import Device, Pairing, User
from app.schemas.accessibility import AccessibilityProfile
from app.schemas.enums import ErrorCode
from app.schemas.senior import PhoneUpdate, SeniorProfileRead, SeniorRead
from app.services import push as push_service
from app.services.account import retire_senior_if_unpaired

logger = logging.getLogger(__name__)

router = APIRouter(tags=["senior"])
NO_SENIOR = "No tienes un Sénior vinculado."


def _active_pairing(
    db: Session, guardian_id: uuid.UUID, lock: bool = False
) -> Pairing | None:
    """ES: Vinculación canjeada y activa más reciente del Tutor.
    EN: The guardian's most recent redeemed, active pairing.
    """
    query = (
        select(Pairing)
        .where(
            Pairing.guardian_id == guardian_id,
            Pairing.senior_id.is_not(None),
            Pairing.active.is_(True),
        )
        .order_by(Pairing.redeemed_at.desc())
        .limit(1)
    )
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


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
        raise ApiError(404, ErrorCode.NOT_FOUND, NO_SENIOR)

    pairing, device, senior = row
    guardian_phone = pairing.guardian_phone
    if guardian_phone is None:
        guardian = db.get(User, token.sub)
        if guardian:
            guardian_phone = guardian.phone
    return SeniorRead(
        senior_display_name=pairing.senior_display_name,
        platform=device.platform if device else None,
        app_version=device.app_version if device else None,
        last_seen_at=device.last_seen_at if device else None,
        paired_since=pairing.redeemed_at,
        accessibility_profile=senior.accessibility_profile,
        guardian_phone=guardian_phone,
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
    row = db.execute(
        select(Pairing.guardian_phone, User.phone)
        .join(User, User.id == Pairing.guardian_id)
        .where(Pairing.senior_id == senior.id, Pairing.active.is_(True))
        .order_by(Pairing.redeemed_at.desc())
        .limit(1)
    ).first()
    pairing_phone, guardian_user_phone = row if row else (None, None)
    guardian_phone = pairing_phone or guardian_user_phone
    return SeniorProfileRead(
        display_name=senior.display_name,
        accessibility_profile=senior.accessibility_profile,
        guardian_phone=guardian_phone,
    )


@router.patch("/senior/accessibility")
def update_accessibility(
    body: AccessibilityProfile, db: DbSession, token: GuardianToken
) -> AccessibilityProfile:
    """ES: El Tutor cambia el perfil de accesibilidad de su Sénior. La app lo
    recoge la próxima vez que llame a GET /senior/me.
    EN: The guardian changes their senior's accessibility profile. The app
    picks it up the next time it calls GET /senior/me.
    """
    pairing = _active_pairing(db, token.sub)
    senior = db.get(User, pairing.senior_id) if pairing else None
    if senior is None or senior.deleted_at is not None:
        raise ApiError(404, ErrorCode.NOT_FOUND, NO_SENIOR)
    senior.accessibility_profile = body.model_dump()
    db.commit()
    return body


@router.patch("/senior/phone")
def update_phone(body: PhoneUpdate, db: DbSession, token: GuardianToken) -> PhoneUpdate:
    """ES: El Tutor actualiza su teléfono de contacto en la vinculación activa.
    EN: Guardian updates their contact phone in the active pairing.
    """
    pairing = _active_pairing(db, token.sub, lock=True)
    if pairing is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, NO_SENIOR)
    pairing.guardian_phone = body.guardian_phone
    db.commit()
    return body


@router.delete("/senior", status_code=status.HTTP_204_NO_CONTENT)
def unlink_senior(db: DbSession, token: GuardianToken):
    """ES: Desvincula al Sénior. Si no le queda ningún otro Tutor, se da de baja
    al Sénior (deleted_at) y se borra el push_token de sus móviles: su token
    deja de valer (401 "Dispositivo no reconocido") y no recibe más avisos.
    Sus análisis se borran con la retención normal.
    EN: Unlinks the senior. If no other guardian remains, the senior is
    deactivated (deleted_at) and their phones' push_token is cleared: the
    token stops working (401 "Device not recognised") and no more
    notifications are sent. Their analyses are removed by normal retention.
    """
    pairing = _active_pairing(db, token.sub, lock=True)
    if pairing is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, NO_SENIOR)
    pairing.active = False
    db.flush()
    retire_senior_if_unpaired(db, pairing.senior_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/senior/logout", status_code=status.HTTP_204_NO_CONTENT)
def notify_senior_logout(db: DbSession, token: SeniorToken):
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
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    try:
        push_service.send_logout_push(
            db, senior.id, senior.display_name, push_service.get_sender()
        )
    except Exception:
        logger.exception("Logout push failed for senior %s", senior.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
