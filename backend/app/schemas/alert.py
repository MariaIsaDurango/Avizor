"""Schemas de alertas y notificaciones push (backend → Tutor).
Alert and push notification schemas (backend → Guardian).

GET   /api/v1/alerts       (guardian) → AlertPage
PATCH /api/v1/alerts/{id}  (guardian) → AlertUpdate → Alert
"""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, HttpUrl

from app.schemas.common import ContractModel
from app.schemas.enums import (
    AlertStatus,
    Channel,
    IndicatorType,
    RagSource,
    RiskLevel,
    ThreatType,
)


class IndicatorEvidence(ContractModel):
    """ES: Indicador técnico (dominio, URL, teléfono ENMASCARADO...).
    EN: Technical indicator (domain, URL, MASKED phone...).
    """

    type: IndicatorType
    value: str = Field(min_length=1, max_length=255)
    reason: str = Field(min_length=1, max_length=300)


class OfficialNoticeEvidence(ContractModel):
    """ES: Aviso oficial recuperado del RAG. Nunca inventado por el LLM.
    EN: Official notice retrieved from the RAG. Never invented by the LLM.
    """

    type: Literal["official_notice"]
    source: RagSource
    url: HttpUrl


# ES: Pydantic elige el modelo según el campo "type".
# EN: Pydantic picks the model based on the "type" field.
Evidence = Annotated[
    IndicatorEvidence | OfficialNoticeEvidence,
    Field(union_mode="left_to_right"),
]


class Alert(ContractModel):
    """ES: Solo se crean alertas para risk_level = red.
    EN: Alerts are only created for risk_level = red.
    """

    id: UUID
    analysis_id: UUID
    senior_id: UUID
    senior_name: str = Field(min_length=1, max_length=50)
    risk_level: Literal[RiskLevel.RED]
    threat_type: ThreatType
    channel: Channel
    summary: str = Field(min_length=1, max_length=300)
    explanation: str = Field(min_length=1, max_length=1000)
    evidence: list[Evidence] = Field(default_factory=list)
    status: AlertStatus
    created_at: AwareDatetime


class AlertUpdate(ContractModel):
    """ES: El Tutor no puede volver a poner una alerta como 'new'.
    EN: The guardian cannot set an alert back to 'new'.
    """

    status: Literal[
        AlertStatus.SEEN, AlertStatus.CONFIRMED_FRAUD, AlertStatus.FALSE_POSITIVE
    ]


class AlertPage(ContractModel):
    """ES: Paginación por cursor. EN: Cursor pagination."""

    items: list[Alert]
    next_cursor: str | None = None


class PushNotification(ContractModel):
    """ES: El push NO lleva contenido del mensaje: solo aviso e id.
    EN: The push has NO message content: only a notice and the id.
    """

    type: Literal["new_alert"] = "new_alert"
    alert_id: UUID
    title: str = Field(min_length=1, max_length=50)
    body: str = Field(min_length=1, max_length=120)
