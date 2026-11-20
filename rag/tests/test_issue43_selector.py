"""Regression tests for bounded reference selection and abstention."""

import json

import httpx
import pytest

from rag.src.agent.llm import OllamaSelector


@pytest.mark.parametrize("references", [[0], [], [-1], [1], [0, 0]])
def test_selector_references(references):
    payload = {
        "allowed_templates": ["FAKE_DO_NOT_TOUCH"],
        "notices": [{"index": 0, "title": "Aviso", "excerpt": "SMS"}],
    }

    def handler(request):
        body = json.loads(request.content)
        rules = body["format"]["properties"]["references"]
        assert rules["minItems"] == rules["maxItems"] == 1
        assert rules["items"]["enum"] == [-1, 0]
        return httpx.Response(
            200,
            json={
                "done": True,
                "done_reason": "stop",
                "message": {
                    "content": json.dumps(
                        {
                            "block_template": "FAKE_DO_NOT_TOUCH",
                            "references": references,
                        }
                    )
                },
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        selector = OllamaSelector(client=client)
        if references == [0]:
            assert selector.select(payload, timeout=1).references == [0]
        else:
            with pytest.raises(ValueError):
                selector.select(payload, timeout=1)
