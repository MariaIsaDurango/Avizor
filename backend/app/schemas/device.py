"""Schemas de dispositivos del Tutor (para recibir notificaciones push).
Guardian device schemas (to receive push notifications).

POST   /api/v1/devices       (guardian) → GuardianDeviceRegister → DeviceRead
DELETE /api/v1/devices/{id}  (guardian) → 204

ES: No están en el Contrato v1.0.0: añadido MINOR (rutas nuevas).
EN: Not in Contract v1.0.0: a MINOR addition (new routes).
"""

from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import ContractModel


class GuardianDeviceRegister(ContractModel):
    platform: Literal["android", "ios"]
    app_version: str = Field(min_length=1, max_length=20)
    # ES: Token de Expo (ExponentPushToken[...]). EN: Expo token.
    push_token: str = Field(min_length=1, max_length=255)


class DeviceRead(ContractModel):
    """ES: No devuelve el push_token. EN: Does not return the push_token."""

    id: UUID
    platform: Literal["android", "ios"]
    app_version: str
