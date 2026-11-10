"""Tests de retención mínima de datos (necesitan PostgreSQL).
Minimum data retention tests (need PostgreSQL).
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.alert import Unlock
from app.models.analysis import Analysis, TempContent
from app.models.indicator import Case, Indicator
from app.schemas.enums import (
    Action,
    Channel,
    IndicatorType,
    InputType,
    Origin,
    RiskLevel,
    ThreatType,
    UnlockStatus,
    VerdictPhase,
)
from app.services.retention import purge_expired

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


@pytest.fixture
def analysis(db_session, paired_senior):
    row = Analysis(
        device_id=paired_senior.device.id,
        channel=Channel.SMS,
        origin=Origin.AUTOMATIC,
        input_types=[InputType.TEXT],
        received_at=NOW,
        risk_level=RiskLevel.RED,
        threat_type=ThreatType.SMISHING,
        action=Action.BLOCK_AND_ALERT,
        phase=VerdictPhase.FAST,
        model_version="test",
    )
    db_session.add(row)
    db_session.flush()
    return row


def add_temp(db_session, analysis, delete_at):
    db_session.add(
        TempContent(
            analysis_id=analysis.id,
            anonymized_text="Texto de prueba [IBAN]",
            delete_at=delete_at,
        )
    )
    db_session.flush()


def add_indicator(db_session, last_seen_at):
    indicator = Indicator(
        type=IndicatorType.DOMAIN,
        value_hash=uuid.uuid4().hex,
        public_value="ejemplo-estafa.top",
        first_seen_at=last_seen_at,
        last_seen_at=last_seen_at,
    )
    db_session.add(indicator)
    db_session.flush()
    return indicator


# ---------- temp_content ----------


def test_expired_text_is_deleted(db_session, analysis):
    add_temp(db_session, analysis, NOW - timedelta(minutes=1))
    result = purge_expired(db_session, NOW)
    assert result.temp_content_deleted == 1
    assert db_session.get(TempContent, analysis.id) is None


def test_text_not_yet_expired_is_kept(db_session, analysis):
    add_temp(db_session, analysis, NOW + timedelta(days=1))
    assert purge_expired(db_session, NOW).temp_content_deleted == 0
    assert db_session.get(TempContent, analysis.id) is not None


def test_open_case_keeps_the_text(db_session, analysis):
    """ES: Caso abierto: se conserva hasta cerrarlo + 90 d.
    EN: Open case: kept until closed + 90 d.
    """
    add_temp(db_session, analysis, NOW - timedelta(days=1))
    db_session.add(Case(analysis_id=analysis.id))
    db_session.flush()
    assert purge_expired(db_session, NOW).temp_content_deleted == 0


@pytest.mark.parametrize(("closed_days_ago", "deleted"), [(30, 0), (91, 1)])
def test_closed_case_keeps_text_for_90_days(
    db_session, analysis, closed_days_ago, deleted
):
    add_temp(db_session, analysis, NOW - timedelta(days=1))
    db_session.add(
        Case(analysis_id=analysis.id, closed_at=NOW - timedelta(days=closed_days_ago))
    )
    db_session.flush()
    assert purge_expired(db_session, NOW).temp_content_deleted == deleted


def test_analysis_metadata_is_kept(db_session, analysis):
    """ES: Solo se borra el texto; el análisis queda para estadísticas.
    EN: Only the text is deleted; the analysis stays for statistics.
    """
    add_temp(db_session, analysis, NOW - timedelta(days=1))
    purge_expired(db_session, NOW)
    assert db_session.get(Analysis, analysis.id) is not None


# ---------- unlocks ----------


def test_pending_unlock_past_24h_expires(db_session, analysis):
    unlock = Unlock(
        analysis_id=analysis.id,
        status=UnlockStatus.PENDING_GUARDIAN,
        requested_at=NOW - timedelta(hours=25),
        expires_at=NOW - timedelta(hours=1),
    )
    db_session.add(unlock)
    db_session.flush()
    assert purge_expired(db_session, NOW).unlocks_expired == 1
    db_session.refresh(unlock)
    assert unlock.status == UnlockStatus.EXPIRED


def test_resolved_unlock_is_not_touched(db_session, analysis):
    unlock = Unlock(
        analysis_id=analysis.id,
        status=UnlockStatus.APPROVED,
        requested_at=NOW - timedelta(hours=25),
        expires_at=NOW - timedelta(hours=1),
    )
    db_session.add(unlock)
    db_session.flush()
    assert purge_expired(db_session, NOW).unlocks_expired == 0


# ---------- indicators ----------


def test_indicator_without_reports_for_a_year_is_deleted(db_session):
    old = add_indicator(db_session, NOW - timedelta(days=366))
    recent = add_indicator(db_session, NOW - timedelta(days=10))
    assert purge_expired(db_session, NOW).indicators_deleted == 1
    assert db_session.get(Indicator, old.id) is None
    assert db_session.get(Indicator, recent.id) is not None


def test_indicator_with_case_is_kept(db_session):
    old = add_indicator(db_session, NOW - timedelta(days=400))
    db_session.add(Case(indicator_id=old.id))
    db_session.flush()
    assert purge_expired(db_session, NOW).indicators_deleted == 0
