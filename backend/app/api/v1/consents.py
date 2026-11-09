"""Endpoint de consentimientos (Contrato v1.0.0).
Consents endpoint (Contract v1.0.0).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, require_role
from app.core.security import TokenPayload
from app.schemas.consent import Consent, ConsentRead
from app.schemas.enums import UserRole
from app.services import consent as consent_service

router = APIRouter(prefix="/consents", tags=["consents"])

SeniorOrGuardian = Annotated[
    TokenPayload, Depends(require_role(UserRole.SENIOR, UserRole.GUARDIAN))
]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_consent(
    body: Consent, db: DbSession, token: SeniorOrGuardian
) -> ConsentRead:
    """ES: Registra el consentimiento del Sénior o la tutela legal del Tutor.
    EN: Records the senior's consent or the guardian's legal guardianship.
    """
    return consent_service.create_consent(db, token, body)


@router.post("/{consent_id}/revoke")
def revoke_consent(
    consent_id: uuid.UUID, db: DbSession, token: SeniorOrGuardian
) -> ConsentRead:
    """ES: Retira un consentimiento (RGPD). Añadido MINOR al contrato.
    EN: Withdraws a consent (GDPR). MINOR addition to the contract.
    """
    return consent_service.revoke_consent(db, token, consent_id)
