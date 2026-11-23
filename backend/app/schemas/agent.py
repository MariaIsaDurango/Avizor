"""Contrato entre el backend y el agente con RAG (reenvío manual).
Contract between the backend and the RAG agent (manual forward).

ES: El agente (LangGraph/CrewAI, issue #43) recibe solo texto anonimizado y
    devuelve un AgentOutput. Si su salida no valida contra este schema, el
    backend aplica la decisión de la vía rápida (contrato, prompt injection).
EN: The agent (LangGraph/CrewAI, issue #43) only receives anonymized text and
    returns an AgentOutput. If its output does not validate against this
    schema, the backend applies the fast path decision (contract, prompt
    injection).
"""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.alert import Evidence
from app.schemas.enums import BlockTemplate, RiskLevel, ThreatType


class AgentInput(BaseModel):
    """ES: Datos NO confiables: van siempre en un campo delimitado del prompt,
    nunca concatenados a las instrucciones.
    EN: UNTRUSTED data: always placed in a delimited prompt field, never
    concatenated to the instructions.
    """

    text: str = Field(max_length=30_000)
    urls: list[str] = Field(default_factory=list, max_length=10)
    # ES: Pista de la vía rápida para el agente. EN: Fast path hint for the agent.
    fast_risk_level: RiskLevel
    fast_threat_type: ThreatType


class AgentOutput(BaseModel):
    """ES: El agente elige códigos del enum; la acción la decide el backend.
    EN: The agent picks enum codes; the action is decided by the backend.
    """

    # ES: Campos extra = salida no válida. EN: Extra fields = invalid output.
    model_config = ConfigDict(extra="forbid")

    risk_level: RiskLevel
    threat_type: ThreatType
    block_template: BlockTemplate
    confidence: float = Field(ge=0, le=1)
    # ES: Solo para el Tutor, nunca para el Sénior. EN: Guardian only, never senior.
    explanation: str = Field(min_length=1, max_length=1000)
    evidence: list[Evidence] = Field(default_factory=list, max_length=5)
