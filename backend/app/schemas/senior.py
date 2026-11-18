"""Schema de respuesta para el Sénior vinculado al Tutor.
Senior response schema for the authenticated guardian.

GET /api/v1/senior  (guardian) → SeniorOut | 404
"""

from typing import Literal

from pydantic import AwareDatetime

from app.schemas.common import ContractModel


class SeniorOut(ContractModel):
    """ES: Datos del Sénior activo vinculado al Tutor autenticado.
    EN: Active senior linked to the authenticated guardian.
    """

    senior_display_name: str
    platform: Literal["android", "ios"] | None = None
    app_version: str | None = None
    last_seen_at: AwareDatetime | None = None
    paired_since: AwareDatetime
