"""Endpoints de vinculación Tutor ↔ Sénior (Contrato v1.0.0).
Guardian ↔ Senior pairing endpoints (Contract v1.0.0).
"""

from fastapi import APIRouter, status

from app.api.deps import DbSession, GuardianToken
from app.schemas.pairing import (
    PairingCreate,
    PairingRead,
    PairingRedeem,
    PairingRedeemResponse,
)
from app.services import pairing as pairing_service

router = APIRouter(prefix="/pairings", tags=["pairings"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_pairing(
    body: PairingCreate, db: DbSession, token: GuardianToken
) -> PairingRead:
    """ES: El Tutor crea un código de 6 dígitos (caduca en 10 min).
    EN: The guardian creates a 6-digit code (expires in 10 min).
    """
    return pairing_service.create_pairing(db, token.sub, body)


@router.post("/redeem")
def redeem_pairing(body: PairingRedeem, db: DbSession) -> PairingRedeemResponse:
    """ES: El móvil del Sénior canjea el código (sin token).
    EN: The senior's phone redeems the code (no token).
    """
    return pairing_service.redeem_pairing(db, body)
