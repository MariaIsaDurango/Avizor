"""Endpoint de consentimientos (Contrato v1.0.0).
Consents endpoint (Contract v1.0.0).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, DeviceToken, require_role
from app.core.security import TokenPayload
from app.schemas.consent import Consent, ConsentRead
from app.schemas.enums import UserRole
from app.services import consent as consent_service

router = APIRouter(prefix="/consents", tags=["consents"])

SeniorOrGuardian = Annotated[
    TokenPayload,
    Depends(require_role(UserRole.SENIOR, UserRole.SENIOR_SOLO, UserRole.GUARDIAN)),
]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_consent(
    body: Consent, db: DbSession, token: SeniorOrGuardian
) -> ConsentRead:
    """ES: Registra el consentimiento del Sénior o la tutela legal del Tutor.
    EN: Records the senior's consent or the guardian's legal guardianship.
    """
    return consent_service.create_consent(db, token, body)


@router.post("/me/revoke")
def revoke_my_consents(db: DbSession, token: DeviceToken) -> list[ConsentRead]:
    """ES: Retira el consentimiento activo del Sénior sin su id (#184). Va antes
    de /{consent_id}/revoke para que "me" no se lea como un id.
    EN: Withdraws the senior's active consent without its id (#184). Declared
    before /{consent_id}/revoke so "me" is not read as an id.
    """
    return consent_service.revoke_my_consents(db, token)


@router.post("/{consent_id}/revoke")
def revoke_consent(
    consent_id: uuid.UUID, db: DbSession, token: SeniorOrGuardian
) -> ConsentRead:
    """ES: Retira un consentimiento (RGPD). Añadido MINOR al contrato.
    EN: Withdraws a consent (GDPR). MINOR addition to the contract.
    """
    return consent_service.revoke_consent(db, token, consent_id)
