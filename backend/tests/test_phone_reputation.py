"""Prefijo 400 y OpenSpam en el análisis de teléfonos (#168). Necesitan PostgreSQL.
400 prefix and OpenSpam in phone analysis (#168). They need PostgreSQL.
"""

import asyncio
import logging
from time import perf_counter

import pytest
from rag.src.reputation.models import Signal
from rag.src.reputation.service import ReputationService
from sqlalchemy import select
from test_analyses_fast import ANALYSES, phone_lookup

from app.core.config import Settings
from app.main import app
from app.models.indicator import Indicator
from app.schemas.enums import Origin, RiskLevel, ThreatType
from app.services.detection.decision import (
    apply_phone_reputation,
    decide_phone,
    is_commercial_number,
)
from app.services.detection.reputation import ReputationRuntime, create_runtime

COMMERCIAL = "+34400123456"
MOBILE = "+34612345678"  # fake


class PhoneProvider:
    name = "openspam"
    kinds = ("phone",)

    def __init__(self, status="malicious", score=85, delay=0.0, error=False):
        self.status, self.score, self.delay, self.error = status, score, delay, error
        self.calls: list[str] = []

    async def check(self, kind, value):
        self.calls.append(value)
        await asyncio.sleep(self.delay)
        if self.error:
            raise RuntimeError(f"boom {value}")
        return Signal(self.name, self.status, self.score)


def inject(monkeypatch, provider, budget=0.6):
    runtime = ReputationRuntime(
        ReputationService([]), phone_provider=provider, phone_budget=budget
    )
    monkeypatch.setattr(app.state, "reputation", runtime, raising=False)


def check(api_client, senior, number):
    response = api_client.post(
        ANALYSES, json=phone_lookup(senior.device.id, number), headers=senior.headers
    )
    assert response.status_code == 200
    return response.json()


# ---------- Prefijo 400 / 400 prefix ----------


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (COMMERCIAL, True),
        (MOBILE, False),
        ("+3440012345", False),  # 8 digits
        ("+34900123456", False),
        (None, False),
    ],
)
def test_is_commercial_number(number, expected):
    assert is_commercial_number(number) is expected


def test_400_number_is_amber_spam_without_reports():
    decision = decide_phone(Origin.MANUAL, 0, COMMERCIAL)
    assert decision.risk_level == RiskLevel.AMBER
    assert decision.threat_type == ThreatType.SPAM
    assert decision.confidence == 0.95
    assert any("400" in r for r in decision.reasons)


def test_reported_400_number_is_still_red():
    decision = decide_phone(Origin.MANUAL, 5, COMMERCIAL)
    assert decision.risk_level == RiskLevel.RED


def test_400_endpoint_without_any_api(api_client, consented_senior, monkeypatch):
    monkeypatch.setattr(app.state, "reputation", None, raising=False)
    data = check(api_client, consented_senior, COMMERCIAL)
    assert data["risk_level"] == "amber"
    assert data["threat_type"] == "spam"


# ---------- OpenSpam ----------


def test_openspam_positive_raises_to_red(
    api_client, db_session, consented_senior, monkeypatch
):
    provider = PhoneProvider("malicious", 85)
    inject(monkeypatch, provider)
    data = check(api_client, consented_senior, MOBILE)
    assert data["risk_level"] == "red"
    assert data["threat_type"] == "vishing"
    assert provider.calls == [MOBILE]
    # ES/EN: an external hit alone must not create a local report
    assert db_session.scalars(select(Indicator)).all() == []


def test_openspam_medium_is_amber(api_client, consented_senior, monkeypatch):
    inject(monkeypatch, PhoneProvider("suspicious", 60))
    assert check(api_client, consented_senior, MOBILE)["risk_level"] == "amber"


def test_openspam_no_match_keeps_baseline(api_client, consented_senior, monkeypatch):
    inject(monkeypatch, PhoneProvider("no_match", None))
    assert check(api_client, consented_senior, MOBILE)["risk_level"] == "green"


def test_openspam_cannot_lower_400_rule(api_client, consented_senior, monkeypatch):
    inject(monkeypatch, PhoneProvider("no_match", None))
    assert check(api_client, consented_senior, COMMERCIAL)["risk_level"] == "amber"


def test_slow_openspam_does_not_block(api_client, consented_senior, monkeypatch):
    inject(monkeypatch, PhoneProvider("malicious", 95, delay=2.0), budget=0.2)
    started = perf_counter()
    data = check(api_client, consented_senior, MOBILE)
    assert perf_counter() - started < 1.5
    assert data["risk_level"] == "green"


def test_openspam_error_is_not_logged_with_number(
    api_client, consented_senior, monkeypatch, caplog
):
    inject(monkeypatch, PhoneProvider(error=True))
    with caplog.at_level(logging.DEBUG):
        data = check(api_client, consented_senior, MOBILE)
    assert data["risk_level"] == "green"
    assert "612345678" not in caplog.text


def test_text_analysis_never_calls_openspam(api_client, consented_senior, monkeypatch):
    from test_analyses_fast import FAMILY, sms_request

    provider = PhoneProvider()
    inject(monkeypatch, provider)
    api_client.post(
        ANALYSES,
        json=sms_request(consented_senior.device.id, FAMILY),
        headers=consented_senior.headers,
    )
    assert provider.calls == []


# ---------- Activación / Opt-in ----------


@pytest.mark.parametrize(
    ("enabled", "key", "active"),
    [(False, "k", False), (True, "", False), (True, "k", True)],
)
def test_openspam_only_with_explicit_opt_in(enabled, key, active):
    settings = Settings(
        AVIZOR_EXTERNAL_PHONES=enabled,
        AVIZOR_OPENSPAM_KEY=key,
        AVIZOR_PHISHTANK_LOCAL=False,
    )
    runtime = create_runtime(client=None, settings=settings)
    assert (runtime.phone_provider is not None) is active


def test_policy_never_downgrades():
    red = decide_phone(Origin.MANUAL, 5, MOBILE)
    assert apply_phone_reputation(red, "suspicious", 40, "OpenSpam").risk_level == (
        RiskLevel.RED
    )
    green = decide_phone(Origin.MANUAL, 0, MOBILE)
    assert apply_phone_reputation(green, "suspicious", 30, "OpenSpam") == green
    raised = apply_phone_reputation(green, "malicious", 95, "OpenSpam")
    assert raised.reputation_only is True
