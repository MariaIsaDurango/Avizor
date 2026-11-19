"""Spanish test numbers are synthetic metadata examples; never contact real numbers."""

import asyncio
import hashlib
import hmac

import httpx
import pytest

from rag.scripts import validate_reputation_live as live
from rag.src.reputation.config import Config
from rag.src.reputation.models import Signal
from rag.src.reputation.phone_checker import LocalPhoneChecker
from rag.src.reputation.providers.numverify import Numverify
from rag.src.reputation.service import ReputationService, fast_path


@pytest.mark.parametrize("number", ["+34612345678", "+34912345678"])
@pytest.mark.parametrize("valid", [True, False])
def test_spanish_numverify_mock(number, valid):
    async def run():
        def handler(req):
            assert req.url.scheme == "https"
            assert req.url.host == "api.apilayer.net"
            assert req.url.path == "/numverify/validate"
            assert req.url.params["access_key"] == "fake"
            assert req.url.params["number"] == number
            assert req.url.params["country_code"] == "ES"
            return httpx.Response(200, json={"valid": valid, "country_code": "ES"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = ReputationService([Numverify(client, "fake")])
            result = await service.check("phone", number)
            assert result.signals[0].status == ("valid" if valid else "invalid")
            assert result.score is None
            assert not result.actionable
            assert not service.cache._items
            assert number not in repr(result)

    asyncio.run(run())


@pytest.mark.parametrize("kind", ["MOBILE", "FIXED_LINE"])
def test_spanish_normalization(kind):
    pn = pytest.importorskip("phonenumbers")
    example = pn.example_number_for_type("ES", getattr(pn.PhoneNumberType, kind))
    canonical = pn.format_number(example, pn.PhoneNumberFormat.E164)
    national = pn.format_number(example, pn.PhoneNumberFormat.NATIONAL)
    assert live.spanish_test_number(national) == canonical
    assert live.spanish_test_number(canonical) == canonical
    assert live.spanish_test_number("00" + canonical[1:]) == canonical


@pytest.mark.parametrize("value", ["123", "+12025550101", "911234567 ext 1"])
def test_probe_rejects_non_spanish_or_invalid(value):
    pytest.importorskip("phonenumbers")
    with pytest.raises(ValueError):
        live.spanish_test_number(value)


def test_spanish_local_hmac():
    number = "+34612345678"

    def digest(value):
        return hmac.new(b"test-only", value.encode(), hashlib.sha256).hexdigest()

    service = ReputationService([LocalPhoneChecker(digest, [digest(number)])])
    result = asyncio.run(service.check("phone", number))
    assert result.score == 95
    assert number not in repr(result)
    assert not service.cache._items


def test_concurrent_fallback():
    class Slow:
        name = "slow"
        kinds = ("url",)

        async def check(self, kind, value):
            await asyncio.sleep(2)
            return Signal(self.name, "no_match")

    async def run():
        async def classify():
            await asyncio.sleep(0.02)
            return {"risk_level": "amber"}

        service = ReputationService([Slow()], Config(budget_ms=100))
        classification, reputation = await fast_path(
            classify, service, [("url", "https://example.com/")]
        )
        assert classification == {"risk_level": "amber"}
        assert reputation.signals[0].reason == "deadline_exceeded"
        assert not reputation.actionable
        assert reputation.elapsed_ms < 400

    asyncio.run(run())


def test_live_requires_explicit_consent(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["probe", "numverify"])
    assert live.main() == 1
    assert "ValueError" in capsys.readouterr().out
