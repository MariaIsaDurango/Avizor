"""Schema de respuesta para el Sénior vinculado al Tutor.
Senior response schema for the authenticated guardian.

GET /api/v1/senior     (guardian) → SeniorRead | 404
GET /api/v1/senior/me  (senior)   → SeniorProfileRead | 404
"""

from typing import Literal

from pydantic import AwareDatetime

from app.schemas.accessibility import AccessibilityProfile
from app.schemas.common import ContractModel


class SeniorRead(ContractModel):
    """ES: Datos del Sénior activo vinculado al Tutor autenticado.
    EN: Active senior linked to the authenticated guardian.
    """

    senior_display_name: str
    platform: Literal["android", "ios"] | None = None
    app_version: str | None = None
    last_seen_at: AwareDatetime | None = None
    paired_since: AwareDatetime
    accessibility_profile: AccessibilityProfile | None = None


class SeniorProfileRead(ContractModel):
    """ES: Lo que la app del Sénior necesita para adaptar su interfaz.
    EN: What the senior app needs to adapt its interface.
    """

    display_name: str
    accessibility_profile: AccessibilityProfile | None = None
    # ES: Teléfono del Tutor de la vinculación activa más reciente.
    # EN: Guardian phone from the most recent active pairing.
    guardian_phone: str | None = None
