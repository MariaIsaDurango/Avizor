"""Schemas de vinculación Tutor ↔ Sénior.
Guardian ↔ Senior pairing schemas.

POST /api/v1/pairings         (guardian) → PairingRead
POST /api/v1/pairings/redeem  (senior, sin token / no token) → PairingRedeemResponse
"""

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field

from app.schemas.common import ContractModel


class PairingCreate(ContractModel):
    """ES: El Tutor indica el nombre del Sénior (solo nombre, sin apellidos).
    EN: The guardian sets the senior's display name (first name only).
    """

    senior_display_name: str = Field(min_length=1, max_length=50)


class PairingRead(ContractModel):
    """ES: Código de 6 dígitos que caduca a los 10 minutos.
    EN: 6-digit code that expires after 10 minutes.
    """

    id: UUID
    code: str = Field(pattern=r"^\d{6}$")
    expires_at: AwareDatetime


class DeviceInfo(ContractModel):
    """ES: Datos del móvil del Sénior al canjear el código.
    EN: Senior's phone data sent when redeeming the code.
    """

    platform: Literal["android", "ios"]
    app_version: str = Field(min_length=1, max_length=20)
    push_token: str | None = None


class PairingRedeem(ContractModel):
    code: str = Field(pattern=r"^\d{6}$")
    device: DeviceInfo


class PairingRedeemResponse(ContractModel):
    """ES: Token JWT del dispositivo (rol senior).
    EN: Device JWT token (senior role).
    """

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    device_id: UUID
    senior_id: UUID
