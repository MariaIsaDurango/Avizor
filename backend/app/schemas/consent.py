"""Schema de consentimiento de monitorización.
Monitoring consent schema.

POST /api/v1/consents (senior o guardian / senior or guardian) → 201
"""

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from app.schemas.common import ContractModel
from app.schemas.enums import Channel, ConsentType


class ConsentEvidence(ContractModel):
    """ES: Documento que acredita la tutela legal.
    EN: Document proving legal guardianship.
    """

    document: Literal["court_ruling"]
    reference: str = Field(min_length=1, max_length=200)


class Consent(ContractModel):
    senior_id: UUID
    type: ConsentType
    scope: list[Channel] = Field(min_length=1)
    text_version: str = Field(min_length=1, max_length=100)
    granted_by: UUID
    evidence: ConsentEvidence | None = None
    granted_at: AwareDatetime

    @model_validator(mode="after")
    def check_evidence(self) -> "Consent":
        """ES: La tutela legal exige evidencia (CHECK de la tabla consents).
        EN: Legal guardianship requires evidence (consents table CHECK).
        """
        if self.type == ConsentType.LEGAL_GUARDIANSHIP and self.evidence is None:
            raise ValueError("evidence is required for legal_guardianship")
        return self
