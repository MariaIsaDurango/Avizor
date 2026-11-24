"""Regression tests for bounded reference selection with Groq."""

import json
from types import SimpleNamespace

import pytest

from rag.src.agent.llm import GroqSelector


@pytest.mark.parametrize("references", [[0], [], [-1], [1], [0, 0]])
def test_selector_references(references):
    payload = {
        "allowed_templates": ["FAKE_DO_NOT_TOUCH"],
        "notices": [{"index": 0, "title": "Aviso", "excerpt": "SMS"}],
    }

    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["response_format"] == {"type": "json_object"}
            assert kwargs["temperature"] == 0
            assert kwargs["max_completion_tokens"] == 256
            assert kwargs["timeout"] == 1

            messages = kwargs["messages"]
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"
            assert json.loads(messages[1]["content"]) == payload

            content = json.dumps({
                "block_template": "FAKE_DO_NOT_TOUCH",
                "references": references,
            })

            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(content=content),
                    )
                ]
            )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )

    selector = GroqSelector(client=fake_client)

    if references == [0]:
        assert selector.select(payload, timeout=1).references == [0]
    else:
        with pytest.raises(ValueError):
            selector.select(payload, timeout=1)
