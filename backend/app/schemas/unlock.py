"""Schemas de solicitudes de desbloqueo (falsos positivos).
Unlock request schemas (false positives).

POST  /api/v1/unlocks       (senior)   → UnlockCreate → Unlock (pending_guardian)
PATCH /api/v1/unlocks/{id}  (guardian) → UnlockUpdate → Unlock
"""

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime

from app.schemas.common import ContractModel
from app.schemas.enums import UnlockStatus


class UnlockCreate(ContractModel):
    analysis_id: UUID


class UnlockUpdate(ContractModel):
    """ES: El Tutor solo aprueba o rechaza; 'expired' lo pone el sistema (24 h).
    EN: The guardian only approves or rejects; 'expired' is set by the system (24 h).
    """

    status: Literal[UnlockStatus.APPROVED, UnlockStatus.REJECTED]


class Unlock(ContractModel):
    id: UUID
    analysis_id: UUID
    status: UnlockStatus
    requested_at: AwareDatetime
    expires_at: AwareDatetime
    resolved_by: UUID | None = None
    resolved_at: AwareDatetime | None = None
