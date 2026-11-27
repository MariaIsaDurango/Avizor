"""Tests de los endpoints de estadísticas (necesitan PostgreSQL).
Statistics endpoint tests (need PostgreSQL).
"""

import pytest
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.analysis import Analysis
from app.schemas.enums import Action, Channel, InputType, Origin, RiskLevel, ThreatType, VerdictPhase


def test_daily_stats_returns_200_and_shape(api_client):
    response = api_client.get("/api/v1/stats/daily?period=7")
    assert response.status_code == 200
    data = response.json()
    assert data["period_days"] == 7
    assert isinstance(data["rows"], list)
    assert len(data["rows"]) == 7
    if data["rows"]:
        row = data["rows"][0]
        assert "date" in row
        assert "amber" in row
        assert "red" in row
        assert "green" not in row


def test_summary_stats_returns_200_and_shape(api_client):
    response = api_client.get("/api/v1/stats/summary?period=30")
    assert response.status_code == 200
    data = response.json()
    assert data["period_days"] == 30
    assert "total" in data
    assert isinstance(data["total"], int)
    assert "by_threat_type" in data
    assert "by_channel" in data


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/stats/daily?period=15",
        "/api/v1/stats/summary?period=15",
        "/api/v1/stats/daily?period=0",
        "/api/v1/stats/daily?period=abc",
    ],
)
def test_invalid_period_returns_422(api_client, path):
    assert api_client.get(path).status_code == 422


def _make_indicator(
    db_session, *, report_count, type="domain", public_value="evil.com"
):
    from datetime import UTC, datetime

    from app.models.indicator import Indicator
    from app.schemas.enums import IndicatorType

    now = datetime.now(UTC)
    ind = Indicator(
        type=IndicatorType(type),
        value_hash=f"hash-{public_value}-{report_count}",
        public_value=public_value,
        report_count=report_count,
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(ind)
    db_session.flush()
    return ind


def test_indicator_ranking_returns_200_and_shape(api_client, db_session):
    _make_indicator(db_session, report_count=5)
    response = api_client.get("/api/v1/stats/indicators")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    for item in data["items"]:
        assert "type" in item
        assert "public_value" in item
        assert "report_count" in item
        assert item["report_count"] >= 5
        assert "last_seen_at" in item


def test_indicator_ranking_threshold(api_client, db_session):
    _make_indicator(db_session, report_count=4, public_value="below-threshold.com")
    _make_indicator(db_session, report_count=5, public_value="above-threshold.com")
    data = api_client.get("/api/v1/stats/indicators").json()
    values = [item["public_value"] for item in data["items"]]
    assert "above-threshold.com" in values
    assert "below-threshold.com" not in values


def test_indicator_ranking_phone_is_masked(api_client, db_session):
    _make_indicator(
        db_session,
        report_count=5,
        type="phone",
        public_value="+34 6** *** 12",
    )
    data = api_client.get("/api/v1/stats/indicators").json()
    phones = [i for i in data["items"] if i["type"] == "phone"]
    assert phones
    assert phones[0]["public_value"] == "+34 6** *** 12"
    assert "type" in phones[0]


def _make_analysis(
    db_session,
    device_id,
    *,
    risk_level,
    threat_type,
    channel,
    created_at,
):
    analysis = Analysis(
        device_id=device_id,
        channel=channel,
        origin=Origin.AUTOMATIC,
        input_types=[InputType.TEXT],
        sender_hash=None,
        received_at=created_at,
        risk_level=risk_level,
        threat_type=threat_type,
        action=(
            Action.ALLOW
            if risk_level == RiskLevel.GREEN
            else Action.BLOCK_AND_ALERT
        ),
        block_template=None,
        confidence=Decimal("0.900"),
        phase=VerdictPhase.FAST,
        model_version="test",
        latency_ms=10,
        server_processed=False,
        final=True,
        created_at=created_at,
    )
    db_session.add(analysis)
    db_session.flush()
    return analysis


def test_daily_stats_groups_attacks_and_fills_empty_days(
    api_client, db_session, consented_senior
):
    today = datetime.now(UTC).date()
    today_at = datetime.now(UTC).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    yesterday_at = today_at - timedelta(days=1)

    device_id = consented_senior.device.id

    _make_analysis(
        db_session,
        device_id,
        risk_level=RiskLevel.AMBER,
        threat_type=ThreatType.SPAM,
        channel=Channel.SMS,
        created_at=today_at,
    )
    _make_analysis(
        db_session,
        device_id,
        risk_level=RiskLevel.RED,
        threat_type=ThreatType.PHISHING,
        channel=Channel.CALL,
        created_at=today_at,
    )
    _make_analysis(
        db_session,
        device_id,
        risk_level=RiskLevel.GREEN,
        threat_type=ThreatType.NONE,
        channel=Channel.SCREEN,
        created_at=today_at,
    )
    _make_analysis(
        db_session,
        device_id,
        risk_level=RiskLevel.AMBER,
        threat_type=ThreatType.SPAM,
        channel=Channel.SMS,
        created_at=yesterday_at,
    )

    response = api_client.get("/api/v1/stats/daily?period=7")

    assert response.status_code == 200
    rows = {row["date"]: row for row in response.json()["rows"]}

    assert rows[str(today)]["amber"] == 1
    assert rows[str(today)]["red"] == 1
    assert rows[str(today - timedelta(days=1))]["amber"] == 1
    assert rows[str(today - timedelta(days=1))]["red"] == 0
    assert rows[str(today - timedelta(days=2))]["amber"] == 0
    assert rows[str(today - timedelta(days=2))]["red"] == 0


def test_summary_stats_counts_only_amber_and_red(
    api_client, db_session, consented_senior
):
    created_at = datetime.now(UTC).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    device_id = consented_senior.device.id

    _make_analysis(
        db_session,
        device_id,
        risk_level=RiskLevel.AMBER,
        threat_type=ThreatType.SPAM,
        channel=Channel.SMS,
        created_at=created_at,
    )
    _make_analysis(
        db_session,
        device_id,
        risk_level=RiskLevel.RED,
        threat_type=ThreatType.PHISHING,
        channel=Channel.CALL,
        created_at=created_at,
    )
    _make_analysis(
        db_session,
        device_id,
        risk_level=RiskLevel.GREEN,
        threat_type=ThreatType.NONE,
        channel=Channel.SCREEN,
        created_at=created_at,
    )

    response = api_client.get("/api/v1/stats/summary?period=30")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    assert data["by_threat_type"] == {
        "spam": 1,
        "phishing": 1,
    }
    assert data["by_channel"] == {
        "sms": 1,
        "call": 1,
    }