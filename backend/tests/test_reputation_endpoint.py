"""JSON endpoint integration tests (requires migrated test PostgreSQL)."""

import asyncio
import json
from time import perf_counter

from fastapi.testclient import TestClient
from rag.src.reputation.models import Signal
from rag.src.reputation.service import ReputationService
from sqlalchemy import select
from test_analyses_fast import ANALYSES, FAMILY, phone_lookup, sms_request

from app.main import app
from app.models.alert import Alert
from app.models.indicator import Indicator
from app.services.detection.reputation import ReputationRuntime

URL = "https://phishing.example/login"


class Provider:
    name = "phishtank"
    kinds = ("url",)

    def __init__(self, status, score=None, delay=0):
        self.status, self.score, self.delay = status, score, delay
        self.calls = 0

    async def check(self, kind, value):
        self.calls += 1
        await asyncio.sleep(self.delay)
        return Signal(self.name, self.status, self.score)


def inject(monkeypatch, provider):
    runtime = ReputationRuntime(ReputationService([provider]))
    monkeypatch.setattr(app.state, "reputation", runtime, raising=False)


def test_external_positive_changes_verdict_without_false_reports(
    api_client, db_session, consented_senior, monkeypatch
):
    provider = Provider("malicious", 100)
    inject(monkeypatch, provider)
    before = db_session.scalars(select(Indicator)).all()
    response = api_client.post(
        ANALYSES,
        json=sms_request(consented_senior.device.id, FAMILY, [URL]),
        headers=consented_senior.headers,
    )
    assert response.status_code == 200
    assert response.json()["risk_level"] == "red"
    assert provider.calls == 1
    alert = db_session.scalar(
        select(Alert).where(Alert.analysis_id == response.json()["analysis_id"])
    )
    assert alert is not None
    assert "PhishTank" in alert.evidence[0]["reason"]
    assert alert.evidence[0]["value"] == "phishing.example"
    assert db_session.scalars(select(Indicator)).all() == before


def test_timeout_keeps_baseline_and_response_under_800ms(
    api_client, db_session, consented_senior, monkeypatch
):
    from app.models.analysis import Analysis

    provider = Provider("malicious", 100, delay=2)
    inject(monkeypatch, provider)
    started = perf_counter()
    response = api_client.post(
        ANALYSES,
        json=sms_request(consented_senior.device.id, FAMILY, [URL]),
        headers=consented_senior.headers,
    )
    assert response.status_code == 200
    assert (perf_counter() - started) * 1000 < 800
    assert response.json()["risk_level"] == "green"
    assert provider.calls == 1
    analysis = db_session.get(Analysis, response.json()["analysis_id"])
    assert analysis.latency_ms < 800


def test_no_consent_and_phone_do_not_call_url_providers(
    api_client, paired_senior, monkeypatch
):
    provider = Provider("malicious", 100)
    inject(monkeypatch, provider)
    response = api_client.post(
        ANALYSES,
        json=sms_request(paired_senior.device.id, FAMILY, [URL]),
        headers=paired_senior.headers,
    )
    assert response.status_code == 403
    response = api_client.post(
        ANALYSES,
        json=phone_lookup(paired_senior.device.id),
        headers=paired_senior.headers,
    )
    assert response.status_code == 200
    assert provider.calls == 0


def test_lifespan_wires_real_local_feed(
    api_client, consented_senior, tmp_path, monkeypatch
):
    from app.core.config import settings
    from app.services.detection import reputation

    monkeypatch.setattr(reputation, "ROOT", tmp_path)
    monkeypatch.setattr(settings, "AVIZOR_PHISHTANK_LOCAL", True)
    monkeypatch.setattr(settings, "AVIZOR_EXTERNAL_URLS", False)
    monkeypatch.setattr(settings, "RETENTION_PURGE_MINUTES", 0)
    feed = tmp_path / "rag/data/reputation/online-valid.json"
    feed.parent.mkdir(parents=True)
    feed.write_text(json.dumps([{"url": URL, "verified": "yes", "online": "yes"}]))
    # Existing api_client fixture supplies the rollback-only DB dependency.
    with TestClient(app) as client:
        response = client.post(
            ANALYSES,
            json=sms_request(consented_senior.device.id, FAMILY, [URL]),
            headers=consented_senior.headers,
        )
        assert response.status_code == 200
        assert response.json()["risk_level"] == "red"
    assert app.state.reputation is None


def test_link_only_in_text_reaches_reputation(
    api_client, db_session, consented_senior, monkeypatch
):
    """ES: El enlace escrito en el texto también se consulta (#151).
    EN: A link written in the text is also checked (#151).
    """
    provider = Provider("malicious", 100)
    inject(monkeypatch, provider)
    response = api_client.post(
        ANALYSES,
        json=sms_request(consented_senior.device.id, f"Mira esto: {URL}"),
        headers=consented_senior.headers,
    )
    assert response.status_code == 200
    assert response.json()["risk_level"] == "red"
    assert provider.calls == 1
    alert = db_session.scalar(
        select(Alert).where(Alert.analysis_id == response.json()["analysis_id"])
    )
    assert alert.evidence[0]["value"] == "phishing.example"
