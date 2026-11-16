"""Agente del reenvío manual: interfaz + versión provisional.
Manual forward agent: interface + provisional version.

ES: AGENT es la pieza que se cambiará por el agente con RAG de María (#43).
    Mientras tanto, ProvisionalAgent repite la decisión de la vía rápida para
    que el flujo completo (202 → sondeo → veredicto final) ya funcione.
EN: AGENT is the piece to be swapped for María's RAG agent (#43).
    Meanwhile, ProvisionalAgent repeats the fast path decision so the whole
    flow (202 → polling → final verdict) already works.
"""

import logging
from typing import Protocol

from pydantic import ValidationError

from app.schemas.agent import AgentInput, AgentOutput
from app.schemas.enums import BlockTemplate, RiskLevel, ThreatType
from app.services.detection.decision import FastDecision

logger = logging.getLogger(__name__)


class ManualAgent(Protocol):
    """ES: Interfaz que debe cumplir el agente con RAG.
    EN: Interface the RAG agent must implement.
    """

    model_version: str

    def analyze(self, data: AgentInput) -> dict: ...


class ProvisionalAgent:
    """ES: Sin LLM ni RAG: devuelve la vía rápida con formato de agente.
    EN: No LLM or RAG: returns the fast path in agent format.
    """

    model_version = "agent-provisional-0.1"

    def __init__(self, fast: FastDecision) -> None:
        self.fast = fast

    def analyze(self, data: AgentInput) -> dict:
        evidence = [
            {"type": "domain", "value": f.domain, "reason": f.reasons[0]}
            for f in self.fast.url_findings
            if f.domain and f.reasons
        ]
        return {
            "risk_level": self.fast.risk_level,
            "threat_type": self.fast.threat_type,
            "block_template": self.fast.block_template
            or BlockTemplate.UNSURE_CALL_FAMILY,
            "confidence": self.fast.confidence,
            "explanation": " ".join(self.fast.reasons[:3])
            or "No se han encontrado señales claras de estafa.",
            "evidence": evidence[:5],
        }


def get_agent(fast: FastDecision) -> ManualAgent:
    """ES: Cuando llegue el agente de María, devolverlo aquí.
    EN: When María's agent arrives, return it here.
    """
    return ProvisionalAgent(fast)


def run_agent(agent: ManualAgent, data: AgentInput) -> AgentOutput | None:
    """ES: None si el agente falla o su salida no valida: se usa la vía rápida.
    EN: None if the agent fails or its output does not validate: fast path wins.
    """
    try:
        output = AgentOutput.model_validate(agent.analyze(data))
    except ValidationError:
        logger.warning("Agent output rejected by schema (%s)", agent.model_version)
        return None
    except Exception:
        logger.exception("Agent failed (%s)", agent.model_version)
        return None

    # ES: Un rojo sin tipo de amenaza no es coherente (lo exige el Verdict).
    # EN: A red without a threat type is inconsistent (the Verdict requires it).
    if output.risk_level == RiskLevel.RED and output.threat_type == ThreatType.NONE:
        logger.warning("Agent returned red without threat_type")
        return None
    return output
