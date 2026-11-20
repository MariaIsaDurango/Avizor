"""Unit tests of the optional production adapter, without Ollama or PostgreSQL."""

from unittest.mock import Mock

import pytest

from app.schemas.agent import AgentInput
from app.schemas.enums import Action, BlockTemplate, RiskLevel, ThreatType
from app.services import agent
from app.services.detection.decision import FastDecision
from app.services.detection.url_rules import UrlFinding

URL = "https://www.incibe.es/ciudadania/avisos/campana-de-smishing-que-suplanta-entidades-bancarias-solicitando-que-les-llames"


def decision():
    return FastDecision(
        RiskLevel.RED,
        ThreatType.SMISHING,
        Action.BLOCK_AND_ALERT,
        BlockTemplate.DANGEROUS_LINK,
        0.9,
        [],
        [UrlFinding("example.invalid", 0.8, ["Dominio sospechoso."])],
    )


def data():
    return AgentInput(
        text="[NAME] Su banco solicita sus claves",
        urls=["https://example.invalid"],
        fast_risk_level="red",
        fast_threat_type="smishing",
    )


def result(state, *, timeout):
    assert 0 < timeout <= 13
    assert state["text"] == data().text
    assert "urls" not in state
    return {
        "risk_level": state["risk"],
        "threat_type": state["threat"],
        "confidence": state["confidence"],
        "block_template": "FAKE_DO_NOT_TOUCH",
        "explanation": "Aviso relacionado.",
        "evidence": state["technical"]
        + [{"type": "official_notice", "source": "incibe", "url": URL}],
    }


@pytest.fixture(autouse=True)
def runtime(monkeypatch):
    engine = Mock()
    engine.analyze.side_effect = result
    monkeypatch.setattr(agent, "_engine", engine)
    return engine


def test_adapter_reuses_engine_and_preserves_baseline(runtime):
    for _ in range(2):
        output = agent.run_agent(agent.get_agent(decision(), timeout=4), data())
        assert output is not None
        assert output.risk_level == RiskLevel.RED
        assert len(output.evidence) == 2
        assert str(output.evidence[1].url) == URL
    assert runtime.analyze.call_count == 2
    assert runtime.analyze.call_args.kwargs["timeout"] == 4


@pytest.mark.parametrize(
    "change",
    [
        {"risk_level": "green"},
        {"threat_type": "other"},
        {"confidence": 1},
        {"block_template": "LOOKS_SAFE"},
        {
            "evidence": [
                {
                    "type": "official_notice",
                    "source": "incibe",
                    "url": "https://example.invalid/fake",
                }
            ]
        },
        {"evidence": []},
        {"extra": "free text"},
    ],
)
def test_adapter_rejects_unsafe_output(runtime, change):
    runtime.analyze.side_effect = lambda state, **kwargs: {
        **result(state, **kwargs),
        **change,
    }
    assert agent.run_agent(agent.get_agent(decision()), data()) is None


def test_adapter_fallback_when_disabled(monkeypatch):
    monkeypatch.setattr(agent, "_engine", None)
    assert agent.run_agent(agent.get_agent(decision()), data()) is None


def test_adapter_fallback_when_engine_unavailable(runtime):
    runtime.analyze.side_effect = TimeoutError("sensitive text must not be logged")
    assert agent.run_agent(agent.get_agent(decision()), data()) is None


def test_runtime_lifecycle_and_initialization_failure(monkeypatch, runtime):
    builder = Mock(return_value=runtime)
    monkeypatch.setattr(agent, "build_runtime", builder)
    agent.initialize_agent(True)
    builder.assert_called_once()
    assert agent._engine is runtime
    agent.close_agent()
    assert agent._engine is None
    builder.side_effect = RuntimeError("private settings")
    agent.initialize_agent(True)
    assert agent._engine is None
    agent.initialize_agent(False)
    assert builder.call_count == 2
