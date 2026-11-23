"""Schemas de respuesta del análisis (backend → Sénior).
Analysis response schemas (backend → Senior).

ES: El Verdict NO lleva texto libre: la app solo muestra la block_template.
    La salida del LLM se valida contra este schema; si falla, se usa la vía rápida.
EN: The Verdict has NO free text: the app only shows the block_template.
    LLM output is validated against this schema; if it fails, the fast path wins.
"""

from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from app.schemas.common import ContractModel
from app.schemas.enums import (
    Action,
    BlockTemplate,
    RiskLevel,
    ThreatType,
    VerdictPhase,
)

# ES: Acciones permitidas por nivel de riesgo (semáforo).
# EN: Allowed actions per risk level (traffic light).
ALLOWED_ACTIONS = {
    RiskLevel.GREEN: {Action.ALLOW},
    RiskLevel.AMBER: {Action.SILENT_BLOCK, Action.ALLOW},
    RiskLevel.RED: {Action.BLOCK_AND_ALERT},
}


class Verdict(ContractModel):
    analysis_id: UUID
    phase: VerdictPhase
    risk_level: RiskLevel
    threat_type: ThreatType
    action: Action
    block_template: BlockTemplate | None = None
    confidence: float = Field(ge=0, le=1)
    final: bool
    retry_after_ms: int | None = Field(default=None, ge=0)
    issued_at: AwareDatetime

    @model_validator(mode="after")
    def check_consistency(self) -> "Verdict":
        if self.action not in ALLOWED_ACTIONS[self.risk_level]:
            raise ValueError(f"action {self.action} not allowed for {self.risk_level}")
        if self.risk_level == RiskLevel.RED and self.threat_type == ThreatType.NONE:
            raise ValueError("red verdict needs a threat_type")
        if self.action != Action.ALLOW and self.block_template is None:
            raise ValueError("blocking actions need a block_template")
        return self


class AnalysisAccepted(ContractModel):
    """ES: Respuesta 202 del reenvío manual: consultar GET /analyses/{id}/verdict.
    EN: 202 response for manual forwards: poll GET /analyses/{id}/verdict.
    """

    analysis_id: UUID
    retry_after_ms: int = Field(ge=0)
