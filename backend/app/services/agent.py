"""Optional, process-local RAG runtime for manual forwarding (#43)."""

import logging
from typing import Protocol

from pydantic import ValidationError

from app.schemas.agent import AgentInput, AgentOutput
from app.schemas.enums import BlockTemplate, RiskLevel, ThreatType
from app.services.detection.decision import FastDecision

logger = logging.getLogger(__name__)
_engine = None


class ManualAgent(Protocol):
    model_version: str

    def analyze(self, data: AgentInput) -> dict | None: ...


def build_runtime():
    """Imports and model loading are optional; only official local data is used."""
    from rag.src.agent.graph import AgentEngine, build_graph
    from rag.src.agent.hybrid import HybridSelector
    from rag.src.agent.retriever import Retriever
    from rag.src.ingestion.pipeline import resolve_official_path
    from rag.src.vector_store.chroma_store import ChromaStore
    from rag.src.vector_store.embeddings import E5Embedder

    path = resolve_official_path()
    if not (path / "chroma.sqlite3").is_file():
        raise ValueError("Official corpus not initialized")
    embedder = E5Embedder()
    store = ChromaStore(path, revision=embedder.revision, synthetic=False)
    if not store.collection.count():
        raise ValueError("Official corpus empty")
    warm_ollama()
    return AgentEngine(build_graph(Retriever(store, embedder), HybridSelector()))


def warm_ollama() -> None:
    """Best effort preload with no user content; recovery can occur on a later request."""
    import httpx

    try:
        with httpx.Client(trust_env=False, follow_redirects=False) as client:
            response = client.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": "gemma3:1b",
                    "keep_alive": "15m",
                    "options": {"num_ctx": 4096},
                },
                timeout=20.0,
            )
            response.raise_for_status()
    except (httpx.HTTPError, ValueError):
        logger.warning("Ollama preload unavailable; fast path remains available")


def initialize_agent(enabled: bool) -> None:
    global _engine
    close_agent()
    if not enabled:
        return
    try:
        _engine = build_runtime()
    except Exception:  # noqa: BLE001 - no potentially sensitive exception details
        logger.warning("RAG initialization failed; fast path remains available")
    else:
        logger.info("Local RAG runtime initialized")


def close_agent() -> None:
    global _engine
    engine, _engine = _engine, None
    if engine is not None:
        engine.close()


class RagManualAgent:
    model_version = "rag-gemma3-1b-0.1"

    def __init__(self, fast: FastDecision, *, timeout: float = 13.0):
        self.fast = fast
        self.timeout = timeout

    def analyze(self, data: AgentInput) -> dict | None:
        engine = _engine
        if (
            engine is None
            or self.timeout <= 0
            or not data.text.strip()
            or self.fast.risk_level == RiskLevel.GREEN
            or self.fast.threat_type == ThreatType.NONE
            or data.fast_risk_level != self.fast.risk_level
            or data.fast_threat_type != self.fast.threat_type
        ):
            return None
        from rag.src.agent.graph import allowed_templates
        from rag.src.ingestion.models import official_url

        risk, threat = self.fast.risk_level.value, self.fast.threat_type.value
        templates = allowed_templates(risk, threat, self.fast.block_template or "")
        technical = [
            {"type": "domain", "value": f.domain, "reason": f.reasons[0]}
            for f in self.fast.url_findings
            if f.domain and f.reasons
        ][:4]
        result = engine.analyze(
            {
                "text": data.text,
                "risk": risk,
                "threat": threat,
                "confidence": self.fast.confidence,
                "templates": templates,
                "technical": technical,
            },
            timeout=self.timeout,
        )
        if result is None:
            return None
        output = AgentOutput.model_validate(result)
        if (
            output.risk_level != self.fast.risk_level
            or output.threat_type != self.fast.threat_type
            or output.confidence != self.fast.confidence
            or output.block_template not in templates
        ):
            return None
        # The graph, not the LLM, constructs citations; check the boundary again.
        evidence = [item.model_dump(mode="json") for item in output.evidence]
        official = [item for item in evidence if item["type"] == "official_notice"]
        if not official or any(
            not official_url(item["source"], item["url"]) for item in official
        ):
            return None
        if any(
            item not in technical
            for item in evidence
            if item["type"] != "official_notice"
        ):
            return None
        return output.model_dump(mode="json")


def get_agent(fast: FastDecision, *, timeout: float = 13.0) -> ManualAgent:
    return RagManualAgent(fast, timeout=timeout)


def run_agent(agent: ManualAgent, data: AgentInput) -> AgentOutput | None:
    """Never expose untrusted text, validation payloads or model errors in logs."""
    try:
        result = agent.analyze(data)
        if result is None:
            return None
        output = AgentOutput.model_validate(result)
    except ValidationError:
        logger.warning("Agent output rejected by schema")
        return None
    except Exception:  # noqa: BLE001
        logger.warning("Agent unavailable; using fast path")
        return None
    if (
        output.risk_level != data.fast_risk_level
        or output.threat_type != data.fast_threat_type
        or (
            output.risk_level != RiskLevel.GREEN
            and output.block_template == BlockTemplate.LOOKS_SAFE
        )
        or (
            output.risk_level == RiskLevel.RED and output.threat_type == ThreatType.NONE
        )
    ):
        return None
    return output
