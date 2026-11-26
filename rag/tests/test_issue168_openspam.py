"""OpenSpam provider (#168): parsing, cache, quotas and privacy. No network."""

import asyncio
import json

import httpx
import pytest

from rag.src.reputation.providers.openspam import OpenSpam

NUMBER = "+34612345678"  # fake


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def found(level, reports=12):
    return {
        "success": True,
        "data": {
            "encontrado": True,
            "numero": {
                "telefono": NUMBER,
                "total_reportes": reports,
                "tipo_spam": "fraude",
                "nivel_peligro": level,
            },
            "reportes_recientes": [],
            "recomendacion": "No contestar",
        },
    }


NOT_FOUND = {"success": True, "data": {"encontrado": False}}


def run(responses, numbers=(NUMBER,), clock=None, step=3.0):
    """Calls check() for each number; returns (signals, captured requests)."""
    requests = []
    queue = list(responses)

    def handler(request):
        requests.append(request)
        status, body = queue.pop(0)
        return httpx.Response(status, content=json.dumps(body).encode())

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenSpam(client, "test-key", clock=clock or Clock())
            signals = []
            for number in numbers:
                signals.append(await provider.check("phone", number))
                if clock:
                    clock.now += step
            return signals

    return asyncio.run(go()), requests


@pytest.mark.parametrize(
    ("level", "status", "score"),
    [
        ("bajo", "suspicious", 40),
        ("medio", "suspicious", 60),
        ("alto", "malicious", 85),
        ("muy_alto", "malicious", 95),
        ("nuevo_valor", "suspicious", 50),
    ],
)
def test_levels_map_to_policy_scores(level, status, score):
    (signal,), _ = run([(200, found(level))])
    assert (signal.status, signal.score) == (status, score)


@pytest.mark.parametrize("response", [(200, NOT_FOUND), (404, {})])
def test_not_reported_is_no_match(response):
    (signal,), _ = run([response])
    assert signal.status == "no_match"
    assert signal.score is None


def test_key_in_header_not_in_url():
    _, (request,) = run([(200, found("alto"))])
    assert request.headers["X-API-Key"] == "test-key"
    assert "test-key" not in str(request.url)
    assert request.url.path == f"/api/number/{NUMBER}"


def test_same_number_within_24h_calls_api_once():
    clock = Clock()
    signals, requests = run(
        [(200, found("alto"))], numbers=(NUMBER, NUMBER), clock=clock
    )
    assert len(requests) == 1
    assert signals[0] == signals[1]


def test_cache_expires_after_24h():
    clock = Clock()
    signals, requests = run(
        [(200, found("alto")), (200, NOT_FOUND)],
        numbers=(NUMBER, NUMBER),
        clock=clock,
        step=86400 + 1,
    )
    assert len(requests) == 2
    assert signals[1].status == "no_match"


def test_errors_are_not_cached():
    clock = Clock()
    signals, requests = run(
        [(500, {}), (200, found("medio"))], numbers=(NUMBER, NUMBER), clock=clock
    )
    assert signals[0].status == "unavailable"
    assert signals[1].status == "suspicious"
    assert len(requests) == 2


@pytest.mark.parametrize(
    "body", [{"success": False}, {"success": True, "data": []}, {"data": {}}]
)
def test_invalid_response_is_unavailable(body):
    (signal,), _ = run([(200, body)])
    assert signal.status == "unavailable"


def test_non_spanish_number_is_not_sent():
    (signal,), requests = run([], numbers=("+447911123456",))
    assert signal.status == "unknown"
    assert requests == []


def test_two_seconds_between_requests():
    clock = Clock()
    numbers = ("+34612345671", "+34612345672")
    signals, requests = run([(200, NOT_FOUND)], numbers=numbers, clock=clock, step=1)
    assert signals[1].reason == "local_quota"
    assert len(requests) == 1


def test_hourly_and_daily_limits():
    clock = Clock()
    hour = [f"+346120000{i:02d}" for i in range(21)]
    signals, requests = run(
        [(200, NOT_FOUND)] * 20, numbers=hour, clock=clock, step=2.5
    )
    assert len(requests) == 20
    assert signals[-1].reason == "local_quota"

    clock = Clock()
    day = [f"+34612{i:06d}" for i in range(51)]
    signals, requests = run([(200, NOT_FOUND)] * 50, numbers=day, clock=clock, step=200)
    assert len(requests) == 50
    assert signals[-1].reason == "local_quota"


def test_network_error_is_unavailable():
    def handler(request):
        raise httpx.ConnectError("down")

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await OpenSpam(client, "k", clock=Clock()).check("phone", NUMBER)

    assert asyncio.run(go()).status == "unavailable"
