"""Offline tests for the bridge and preservation of the fast-path policy."""

import asyncio
import logging
import time
from functools import partial
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
from pydantic import SecretStr
from rag.src.reputation.models import Signal
from rag.src.reputation.service import ReputationService

from app.schemas.enums import Channel, InputType, Origin, RiskLevel
from app.services.detection.decision import decide
from app.services.detection.reputation import ReputationRuntime, create_runtime
from app.services.detection.text_rules import KeywordClassifier

URL = "https://phishing.example/login"
OTHER = "https://other.example/private?token=secret"


def baseline(urls=(URL,), text="Hola mamá"):
    return partial(
        decide,
        input_type=InputType.TEXT,
        origin=Origin.AUTOMATIC,
        channel=Channel.SMS,
        text=text,
        urls=list(urls),
        classifier=KeywordClassifier(),
    )


class Provider:
    name = "phishtank"
    kinds = ("url",)

    def __init__(self, status, score=None, delay=0):
        self.status, self.score, self.delay = status, score, delay

    async def check(self, kind, value):
        await asyncio.sleep(self.delay)
        return Signal(self.name, self.status, self.score, "test fixture")


def test_positive_url_raises_risk_without_polluting_internal_reports():
    runtime = ReputationRuntime(ReputationService([Provider("malicious", 100)]))
    result = asyncio.run(runtime.evaluate(baseline(), [URL], Channel.SMS))
    assert result.risk_level == RiskLevel.RED
    assert result.reputation_only
    assert result.url_findings[0].score == 0
    assert result.reputation_findings[0].domain == "phishing.example"
    assert result.reputation_findings[0].score == 1
    assert "PhishTank" in result.reasons[0]


def test_no_match_and_number_validity_preserve_baseline():
    classify = baseline()
    for status in ("no_match", "unknown", "unavailable", "valid", "invalid"):
        runtime = ReputationRuntime(ReputationService([Provider(status, 100)]))
        assert asyncio.run(runtime.evaluate(classify, [URL], Channel.SMS)) == classify()


def test_provider_failure_preserves_baseline():
    class Broken(Provider):
        async def check(self, kind, value):
            raise RuntimeError("private details must not be returned")

    classify = baseline()
    runtime = ReputationRuntime(ReputationService([Broken("unavailable")]))
    assert asyncio.run(runtime.evaluate(classify, [URL], Channel.SMS)) == classify()


def test_service_failure_preserves_baseline():
    class Broken:
        async def check_many(self, indicators):
            raise RuntimeError("private details")

    classify = baseline()
    runtime = ReputationRuntime(Broken())
    assert asyncio.run(runtime.evaluate(classify, [URL], Channel.SMS)) == classify()


def test_concurrent_deadline_preserves_local_positive():
    class Slow(Provider):
        name = "virustotal"

    runtime = ReputationRuntime(
        ReputationService([Provider("malicious", 100), Slow("no_match", delay=2)])
    )
    classify = baseline()

    def slow_classifier():
        time.sleep(0.2)
        return classify()

    start = time.monotonic()
    result = asyncio.run(runtime.evaluate(slow_classifier, [URL], Channel.SMS))
    elapsed = time.monotonic() - start
    assert result.risk_level == RiskLevel.RED
    # Generous wall-clock guard: not an SLA measurement; CI can be noisy.
    assert elapsed < 0.8


def test_existing_red_never_downgraded():
    classify = baseline(text="BBVA: su cuenta [IBAN] ha sido bloqueada. Verifique.")
    runtime = ReputationRuntime(ReputationService([Provider("suspicious", 60)]))
    result = asyncio.run(runtime.evaluate(classify, [URL], Channel.SMS))
    assert result.risk_level == classify().risk_level == RiskLevel.RED
    assert result.action == classify().action
    assert result.block_template == classify().block_template


def settings(**kwargs):
    defaults = {
        "AVIZOR_PHISHTANK_LOCAL": False,
        "AVIZOR_EXTERNAL_URLS": False,
        "AVIZOR_REPUTATION_PUBLIC_URLS": [],
        "AVIZOR_VT_KEY": SecretStr("fake-vt"),
        "AVIZOR_GSB_KEY": SecretStr("fake-gsb"),
    }
    return SimpleNamespace(**(defaults | kwargs))


def test_external_disabled_even_with_keys():
    client = Mock()
    runtime = create_runtime(client, settings(AVIZOR_REPUTATION_PUBLIC_URLS=[URL]))
    assert runtime.service.providers == ()
    assert not client.mock_calls


def test_only_reviewed_public_urls_and_domains_leave_backend():
    requests = []

    async def handler(request):
        requests.append(request)
        if request.url.host == "www.virustotal.com":
            return httpx.Response(404)
        return httpx.Response(200, json={})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            runtime = create_runtime(
                client,
                settings(
                    AVIZOR_EXTERNAL_URLS=True,
                    AVIZOR_REPUTATION_PUBLIC_URLS=[URL, OTHER],
                ),
            )
            result = await runtime.evaluate(
                baseline([URL, OTHER]), [URL, OTHER], Channel.SMS
            )
            assert result == baseline([URL, OTHER])()
            assert len(requests) == 3
            assert all("secret" not in str(r.url) for r in requests)
            assert all(b"secret" not in r.content for r in requests)
            assert all("other.example" not in str(r.url) for r in requests)
            assert all(b"other.example" not in r.content for r in requests)
            await runtime.service.check("phone", "+34612345678")
            assert len(requests) == 3

    asyncio.run(run())


def test_classifier_and_provider_overlap():
    from threading import Event

    started = Event()
    observed = Event()
    classify = baseline()

    def classifier():
        started.set()
        assert observed.wait(0.7)
        return classify()

    class Overlap(Provider):
        async def check(self, kind, value):
            for _ in range(100):
                if started.is_set():
                    observed.set()
                    break
                await asyncio.sleep(0.002)
            return Signal(self.name, "malicious", 100)

    runtime = ReputationRuntime(ReputationService([Overlap("malicious", 100)]))
    result = asyncio.run(runtime.evaluate(classifier, [URL], Channel.SMS))
    assert observed.is_set()
    assert result.risk_level == RiskLevel.RED


def test_load_local_snapshot_at_startup(tmp_path, monkeypatch):
    import json

    from app.services.detection import reputation

    monkeypatch.setattr(reputation, "ROOT", tmp_path)
    feed = tmp_path / "rag/data/reputation/online-valid.json"
    feed.parent.mkdir(parents=True)
    feed.write_text(json.dumps([{"url": URL, "verified": "yes", "online": "yes"}]))
    runtime = create_runtime(Mock(), settings(AVIZOR_PHISHTANK_LOCAL=True))
    result = asyncio.run(runtime.evaluate(baseline(), [URL], Channel.SMS))
    assert result.risk_level == RiskLevel.RED
    feed.unlink()
    runtime = create_runtime(Mock(), settings(AVIZOR_PHISHTANK_LOCAL=True))
    assert asyncio.run(runtime.evaluate(baseline(), [URL], Channel.SMS)) == baseline()()


def test_bridge_can_run_from_fastapi_style_worker():
    from anyio import to_thread
    from anyio.from_thread import run

    runtime = ReputationRuntime(ReputationService([Provider("malicious", 100)]))

    def worker():
        return run(runtime.evaluate, baseline(), [URL], Channel.SMS)

    async def request():
        return await to_thread.run_sync(worker)

    assert asyncio.run(request()).risk_level == RiskLevel.RED


def test_external_request_logs_are_filtered_without_hiding_other_logs(caplog):
    from app.services.detection.reputation import install_private_request_filters

    async def handler(request):
        return httpx.Response(200, json={})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            runtime = create_runtime(
                client,
                settings(
                    AVIZOR_EXTERNAL_URLS=True,
                    AVIZOR_REPUTATION_PUBLIC_URLS=[URL],
                ),
            )
            await runtime.evaluate(baseline(), [URL], Channel.SMS)
            await client.get("https://outside.example/")

    remove_filters = install_private_request_filters()
    try:
        with caplog.at_level(logging.INFO, logger="httpx"):
            asyncio.run(run())
    finally:
        remove_filters()
    assert "outside.example" in caplog.text
    assert "fake-gsb" not in caplog.text
    assert "safebrowsing.googleapis.com" not in caplog.text
    assert "virustotal.com" not in caplog.text
