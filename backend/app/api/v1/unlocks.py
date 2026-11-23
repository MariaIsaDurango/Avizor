"""Endpoints de desbloqueo de falsos positivos (Contrato v1.0.0).
False-positive unlock endpoints (Contract v1.0.0).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, GuardianToken, SeniorToken, require_role
from app.core.security import TokenPayload
from app.schemas.enums import UserRole
from app.schemas.unlock import Unlock, UnlockCreate, UnlockUpdate
from app.services import unlocks as unlock_service

router = APIRouter(prefix="/unlocks", tags=["unlocks"])

SeniorOrGuardian = Annotated[
    TokenPayload, Depends(require_role(UserRole.SENIOR, UserRole.GUARDIAN))
]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_unlock(body: UnlockCreate, db: DbSession, token: SeniorToken) -> Unlock:
    """ES: El Sénior pide desbloquear un contenido bloqueado (24 h).
    EN: The senior asks to unlock blocked content (24 h).
    """
    return unlock_service.create_unlock(db, token, body)


@router.get("")
def list_pending_unlocks(db: DbSession, token: GuardianToken) -> list[Unlock]:
    """ES: Solicitudes pendientes de los Séniors vinculados (añadido MINOR).
    EN: Pending requests from paired seniors (MINOR addition).
    """
    return unlock_service.list_pending_for_guardian(db, token.sub)


@router.get("/{unlock_id}")
def get_unlock(unlock_id: uuid.UUID, db: DbSession, token: SeniorOrGuardian) -> Unlock:
    """ES: Estado de una solicitud: el Sénior la consulta mientras espera (MINOR).
    EN: Request status: the senior polls it while waiting (MINOR).
    """
    return unlock_service.get_unlock(db, token, unlock_id)


@router.patch("/{unlock_id}")
def resolve_unlock(
    unlock_id: uuid.UUID, body: UnlockUpdate, db: DbSession, token: GuardianToken
) -> Unlock:
    """ES: El Tutor aprueba o rechaza. EN: The guardian approves or rejects."""
    return unlock_service.resolve_unlock(db, token, unlock_id, body)
