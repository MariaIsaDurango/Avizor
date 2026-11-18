"""Tests use reserved example domains and mock HTTP, never real targets."""

import asyncio
import hashlib
import hmac
import json
import time

import httpx
import pytest

from rag.src.reputation.cache import TTLCache
from rag.src.reputation.config import Config
from rag.src.reputation.models import Signal
from rag.src.reputation.phone_checker import LocalPhoneChecker, check_phone
from rag.src.reputation.providers.common import Quota
from rag.src.reputation.providers.numverify import Numverify
from rag.src.reputation.providers.phishtank import PhishTank
from rag.src.reputation.providers.safe_browsing import SafeBrowsing
from rag.src.reputation.providers.virustotal import VirusTotal
from rag.src.reputation.service import ReputationService, build_service, fast_path
from rag.src.reputation.url_checker import check_domain, check_url
from rag.src.reputation.validators import domain, phone, url

URL = "https://phishing.example/login"
PHONE = "+12025550101"


@pytest.mark.parametrize(
    "value",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "http://localhost/a",
        "http://127.0.0.1/",
        "http://[::1]/",
        "https://user@phishing.example/",
        "https://phishing.example:81/a",
        "https://phishing.example/\n",
        "https://foo..example/",
        "http://test.internal/",
        "https://a.example\\b",
    ],
)
def test_bad_url(value):
    with pytest.raises(ValueError):
        url(value)


def test_normalization():
    assert url("HTTPS://EXAMPLE.COM:443/a?x=1#frag") == "https://example.com/a?x=1"
    assert domain("BÜCHER.example.") == "xn--bcher-kva.example"


@pytest.mark.parametrize(
    "value", ["1234", "+012345678", "+12 3456789", "+1234567890123456"]
)
def test_bad_phone(value):
    with pytest.raises(ValueError):
        phone(value)


def test_phone_format():
    assert phone(PHONE) == PHONE


def test_cache():
    now = [0]
    cache = TTLCache(max_entries=1, clock=lambda: now[0])
    key = cache.key("p", "url", URL)
    assert URL not in key
    assert cache.get(key) is None
    cache.put(key, 1, 10)
    assert cache.get(key) == 1
    now[0] = 10
    assert cache.get(key) is None
    cache.put(key, 1, 10)
    cache.put("other", 2, 10)
    assert cache.get(key) is None


def test_quota():
    now = [0]
    quota = Quota(minute=1, day=2, clock=lambda: now[0])
    assert quota.take()
    assert not quota.take()
    now[0] = 60
    assert quota.take()
    now[0] = 120
    assert not quota.take()
    now[0] = 86401
    assert quota.take()


@pytest.mark.parametrize(
    ("code", "payload", "status"),
    [
        (
            200,
            {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {"malicious": 3, "suspicious": 0}
                    }
                }
            },
            "malicious",
        ),
        (
            200,
            {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {"malicious": 0, "suspicious": 1}
                    }
                }
            },
            "suspicious",
        ),
        (
            200,
            {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {"malicious": 0, "suspicious": 0}
                    }
                }
            },
            "no_match",
        ),
        (200, {}, "unavailable"),
        (404, {}, "unknown"),
        (429, {}, "unavailable"),
        (503, {}, "unavailable"),
        (302, {}, "unavailable"),
    ],
)
def test_vt(code, payload, status):
    async def run():
        def handler(req):
            assert req.method == "GET"
            assert req.url.host == "www.virustotal.com"
            assert req.url.path.startswith("/api/v3/urls/")
            assert req.headers["x-apikey"] == "fake"
            return httpx.Response(code, json=payload, headers={"location": URL})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await VirusTotal(client, "fake").check("url", URL)
            assert result.status == status

    asyncio.run(run())


def test_vt_domain():
    async def run():
        def handler(req):
            assert req.url.path == "/api/v3/domains/phishing.example"
            return httpx.Response(404)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            assert (
                await VirusTotal(client, "fake").check("domain", "phishing.example")
            ).status == "unknown"

    asyncio.run(run())


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({}, "no_match"),
        (
            {
                "matches": [
                    {"threatType": "SOCIAL_ENGINEERING", "cacheDuration": "300s"}
                ]
            },
            "malicious",
        ),
        ({"matches": [{}]}, "unavailable"),
        ({"matches": [{"threatType": "MALWARE"}]}, "unavailable"),
    ],
)
def test_google(payload, status):
    async def run():
        def handler(req):
            assert req.url.host == "safebrowsing.googleapis.com"
            assert req.method == "POST"
            assert json.loads(req.content)["threatInfo"]["threatEntries"] == [
                {"url": URL}
            ]
            return httpx.Response(200, json=payload)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await SafeBrowsing(client, "fake").check("url", URL)
            assert result.status == status
            if status == "malicious":
                assert result.ttl == 300

    asyncio.run(run())


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"valid": True}, "valid"),
        ({"valid": False}, "invalid"),
        ({"success": False}, "unavailable"),
    ],
)
def test_numverify(payload, status):
    async def run():
        def handler(req):
            assert req.url.scheme == "https"
            assert req.url.host == "api.apilayer.net"
            assert req.url.path == "/numverify/validate"
            assert req.url.params["access_key"] == "fake"
            assert req.url.params["number"] == PHONE
            return httpx.Response(200, json=payload)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await Numverify(client, "fake").check("phone", PHONE)
            assert result.status == status
            assert result.score is None

    asyncio.run(run())


def test_local_feed(tmp_path):
    path = tmp_path / "feed.json"
    path.write_text(
        json.dumps(
            [
                {"url": URL, "verified": "yes", "online": "yes"},
                {"url": "https://ignored.example/", "verified": "no", "online": "yes"},
                {"url": "file:///bad", "verified": "yes", "online": "yes"},
            ]
        )
    )
    provider = PhishTank.from_file(path)
    service = ReputationService([provider])
    assert asyncio.run(check_url(service, URL)).score == 100
    assert asyncio.run(check_url(service, "https://ignored.example/")).score is None


def test_stale_feed():
    provider = PhishTank([URL], loaded_at=0, clock=lambda: 90000)
    assert asyncio.run(provider.check("url", URL)).status == "unavailable"


def test_phone_local():
    def digest(value):
        return hmac.new(b"test-key", value.encode(), hashlib.sha256).hexdigest()

    provider = LocalPhoneChecker(digest, [digest(PHONE)])
    service = ReputationService([provider])
    result = asyncio.run(check_phone(service, PHONE))
    assert result.score == 95
    assert PHONE not in repr(result)
    assert not service.cache._items
    assert asyncio.run(check_phone(service, "+12025550102")).score is None


class Slow:
    name = "slow"
    kinds = ("url",)

    async def check(self, kind, value):
        await asyncio.sleep(2)
        return Signal(self.name, "no_match")


class Broken:
    name = "broken"
    kinds = ("url",)

    async def check(self, kind, value):
        raise RuntimeError(value)


class Good:
    name = "good"
    kinds = ("url", "domain")

    def __init__(self):
        self.calls = 0

    async def check(self, kind, value):
        self.calls += 1
        return Signal(self.name, "malicious", 95, "mocked")


def test_parallel_deadline():
    service = ReputationService([Slow(), Good(), Broken()], Config(budget_ms=100))
    result = asyncio.run(
        service.check_many([("url", URL), ("url", "https://other.example/")])
    )
    assert result.score == 95
    assert result.actionable
    assert any(s.reason == "deadline_exceeded" for s in result.signals)
    assert any(s.reason == "provider_failed" for s in result.signals)
    assert result.elapsed_ms < 400


def test_fallback():
    async def classify():
        return {"risk_level": "amber"}

    result, rep = asyncio.run(
        fast_path(classify, ReputationService([Broken()]), [("url", URL)])
    )
    assert result == {"risk_level": "amber"}
    assert not rep.actionable
    assert rep.score is None
    assert URL not in repr(rep)


def test_service_cache_and_domain():
    provider = Good()
    service = ReputationService([provider])
    asyncio.run(check_domain(service, "phishing.example"))
    asyncio.run(check_domain(service, "PHISHING.example"))
    assert provider.calls == 1


def test_default_disabled():
    config = Config(virustotal_key="fake", google_key="fake", numverify_key="fake")
    assert not build_service(None, config).providers
    assert asyncio.run(ReputationService().check("url", URL)).score is None
    assert "fake" not in repr(config)


def test_explicit_opt_in():
    config = Config(
        virustotal_key="fake",
        google_key="fake",
        numverify_key="fake",
        allow_external_urls=True,
        allow_external_phones=True,
    )
    assert len(build_service(None, config).providers) == 3


def test_invalid_never_dispatched():
    provider = Good()
    result = asyncio.run(
        ReputationService([provider]).check("url", "ftp://phishing.example")
    )
    assert provider.calls == 0
    assert result.signals[0].status == "invalid"


def test_http_transport_failure():
    async def run():
        def handler(req):
            raise httpx.ConnectError("private data", request=req)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await VirusTotal(client, "fake").check("url", URL)
            assert result.status == "unavailable"
            assert "private data" not in repr(result)

    asyncio.run(run())


def test_latency_local():
    service = ReputationService([PhishTank([URL], time.time())])

    async def run():
        return [(await check_url(service, URL)).elapsed_ms for _ in range(100)]

    times = asyncio.run(run())
    assert max(times) < 400
