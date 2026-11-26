"""Reporte manual de indicadores (#170).
Manual indicator reports (#170).
"""

from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import ContractModel
from app.schemas.enums import ThreatType


class IndicatorReportCreate(ContractModel):
    """ES: El Sénior reporta un número (p. ej. tras una llamada sospechosa).
    EN: The senior reports a number (e.g. after a suspicious call).
    """

    type: Literal["phone"]
    # ES: Cualquier formato español o E.164; se normaliza. EN: Normalized.
    value: str = Field(min_length=3, max_length=32)
    threat_type: Literal[
        ThreatType.SPAM,
        ThreatType.VISHING,
        ThreatType.SMISHING,
        ThreatType.BANK_FRAUD,
        ThreatType.IDENTITY_THEFT,
        ThreatType.OTHER,
    ] = ThreatType.SPAM
    # ES: Opcional solo para senior_solo (#174). EN: Optional only for senior_solo.
    device_id: UUID | None = None


class IndicatorReportRead(ContractModel):
    """ES: Nunca el número en claro: solo enmascarado.
    EN: Never the number in clear text: masked only.
    """

    type: Literal["phone"]
    public_value: str
    threat_type: ThreatType
    # ES: False si este dispositivo ya lo había reportado. EN: False if repeated.
    counted: bool
