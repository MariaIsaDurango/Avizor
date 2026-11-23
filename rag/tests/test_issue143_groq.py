"""Issue #143: provider migration without network calls or credentials."""

from types import SimpleNamespace

import pytest

from rag.src.agent.hybrid import HybridSelector
from rag.src.agent.llm import GroqSelector


def fake(content):
    class Endpoints:
        def create(self, **kwargs):
            assert kwargs["timeout"] <= 13
            assert kwargs["response_format"] == {"type": "json_object"}
            assert "tools" not in kwargs
            return SimpleNamespace(choices=[SimpleNamespace(
                finish_reason="stop", message=SimpleNamespace(content=content)
            )])
    return SimpleNamespace(chat=SimpleNamespace(completions=Endpoints()))


def test_model_override(monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")
    assert GroqSelector(client=fake("{}")).model == "openai/gpt-oss-120b"
    assert HybridSelector(client=fake("{}")).model == "openai/gpt-oss-120b"


def test_rejects_empty_notices_without_external_request():
    with pytest.raises(ValueError):
        GroqSelector(client=fake("{}")).select({"notices": [], "allowed_templates": ["FAKE_DO_NOT_TOUCH"]}, timeout=2)


def test_hybrid_rejects_extraneous_model_fields():
    with pytest.raises(ValueError):
        HybridSelector(client=fake('{"relevance":"yes","block_template":"FAKE_DO_NOT_TOUCH","url":"https://untrusted.invalid"}')).select({
            "anonymized_text":"[NAME]", "fast_threat_type":"smishing", "fast_risk_level":"red",
            "allowed_templates":["FAKE_DO_NOT_TOUCH"],
            "notices":[{"index":0,"title":"notice","excerpt":"test"}],
        }, timeout=1)


@pytest.mark.parametrize("content", [
    '{"template":"FAKE_DO_NOT_TOUCH","references":[0]}',
    '{"block_template":"FAKE_DO_NOT_TOUCH","references":[0]}',
])
def test_groq_selector_accepts_canonical_and_known_template_alias(content):
    payload = {"allowed_templates": ["FAKE_DO_NOT_TOUCH"],
               "notices": [{"index": 0, "title": "Aviso", "excerpt": "SMS"}]}
    result = GroqSelector(client=fake(content)).select(payload, timeout=2)
    assert result.block_template == "FAKE_DO_NOT_TOUCH"
    assert result.references == [0]


@pytest.mark.parametrize("content", [
    '{"template":"FAKE_DO_NOT_TOUCH","references":[0],"url":"https://bad.invalid"}',
    '{"template":"OTHER","references":[0]}',
    '{"template":"FAKE_DO_NOT_TOUCH","references":[9]}',
    '{"template":"FAKE_DO_NOT_TOUCH","references":[0,0]}',
])
def test_groq_selector_alias_does_not_weaken_security(content):
    payload = {"allowed_templates": ["FAKE_DO_NOT_TOUCH"],
               "notices": [{"index": 0, "title": "Aviso", "excerpt": "SMS"}]}
    with pytest.raises(ValueError):
        GroqSelector(client=fake(content)).select(payload, timeout=2)
