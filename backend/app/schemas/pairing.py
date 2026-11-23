"""Schemas de vinculación Tutor ↔ Sénior.
Guardian ↔ Senior pairing schemas.

POST /api/v1/pairings         (guardian) → PairingRead
POST /api/v1/pairings/redeem  (senior, sin token / no token) → PairingRedeemResponse
"""

import re
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator

from app.schemas.accessibility import AccessibilityProfile
from app.schemas.common import ContractModel

# ES: Se quitan espacios, guiones, puntos y paréntesis; queda "+" opcional y
#     de 9 a 15 dígitos (E.164 admite hasta 15).
# EN: Spaces, dashes, dots and brackets are removed; an optional "+" and
#     9 to 15 digits remain (E.164 allows up to 15).
PHONE_SEPARATORS = re.compile(r"[\s\-.()]")
PHONE_PATTERN = re.compile(r"^\+?\d{9,15}$")


def normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    phone = PHONE_SEPARATORS.sub("", value)
    if not phone:
        return None
    if not PHONE_PATTERN.fullmatch(phone):
        raise ValueError("Teléfono no válido. Ejemplo: +34 600 000 000")
    return phone


class PairingCreate(ContractModel):
    """ES: El Tutor indica el nombre del Sénior (solo nombre, sin apellidos).
    EN: The guardian sets the senior's display name (first name only).
    """

    senior_display_name: str = Field(min_length=1, max_length=50)
    # ES: Opcional; sin perfil la app usa la interfaz por defecto.
    # EN: Optional; without a profile the app uses the default interface.
    senior_accessibility_profile: AccessibilityProfile | None = None
    # ES: Opcional; el Sénior lo usa para llamar al Tutor desde la app.
    # EN: Optional; the senior uses it to call the guardian from the app.
    guardian_phone: str | None = Field(default=None, max_length=30)

    @field_validator("guardian_phone")
    @classmethod
    def check_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value)


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
    # ES: La app lo usa nada más vincularse para adaptar la interfaz.
    # EN: The app uses it right after pairing to adapt the interface.
    accessibility_profile: AccessibilityProfile | None = None
    guardian_phone: str | None = None
