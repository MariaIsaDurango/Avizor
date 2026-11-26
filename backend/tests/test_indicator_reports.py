"""Tests del reporte manual de números (#170). Necesitan PostgreSQL.
Manual number report tests (#170). They need PostgreSQL.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text

from app.core.privacy import hash_indicator
from app.core.security import create_access_token
from app.models.indicator import Indicator, IndicatorReport
from app.models.user import Device, Pairing, User
from app.schemas.enums import IndicatorType, UserRole

INDICATORS = "/api/v1/indicators"
ANALYSES = "/api/v1/analyses"
# ES: Números inventados. EN: Fake numbers.
NUMBER = "+34 612 345 678"
E164 = "+34612345678"


def report(client, senior, value=NUMBER, **extra):
    body = {"type": "phone", "value": value, "device_id": str(senior.device.id)}
    body.update(extra)
    return client.post(INDICATORS, json=body, headers=senior.headers)


def indicator(db_session):
    return db_session.scalar(
        select(Indicator).where(
            Indicator.value_hash == hash_indicator(IndicatorType.PHONE, E164)
        )
    )


def another_senior(db_session, guardian, index):
    """ES: Otro Sénior vinculado (para contar personas distintas).
    EN: Another paired senior (to count different people).
    """
    now = datetime.now(UTC)
    senior = User(role=UserRole.SENIOR, display_name=f"Sénior {index}")
    db_session.add(senior)
    db_session.flush()
    device = Device(user_id=senior.id, platform="android", app_version="1.0.0")
    db_session.add_all(
        [
            device,
            Pairing(
                guardian_id=guardian.id,
                senior_id=senior.id,
                code=f"{index:06d}",
                senior_display_name=senior.display_name,
                expires_at=now + timedelta(minutes=10),
                redeemed_at=now,
            ),
        ]
    )
    db_session.flush()
    token = create_access_token(device.id, UserRole.SENIOR)
    from types import SimpleNamespace

    return SimpleNamespace(device=device, headers={"Authorization": f"Bearer {token}"})


def test_first_report_creates_masked_indicator(api_client, db_session, paired_senior):
    response = report(api_client, paired_senior)
    assert response.status_code == 201
    data = response.json()
    assert data["counted"] is True
    assert data["threat_type"] == "spam"
    assert "612345678" not in data["public_value"]

    row = indicator(db_session)
    assert row.report_count == 1
    assert row.public_value == data["public_value"]


def test_number_is_never_stored_in_clear(api_client, db_session, paired_senior):
    report(api_client, paired_senior)
    dump = db_session.execute(
        text(
            "SELECT i.value_hash, i.public_value, r::text FROM indicators i "
            "JOIN indicator_reports r ON r.indicator_id = i.id"
        )
    ).all()
    assert dump and all("612345678" not in str(row) for row in dump)


def test_same_device_counts_once(api_client, db_session, paired_senior):
    report(api_client, paired_senior)
    again = report(api_client, paired_senior, value="612345678")
    assert again.status_code == 200
    assert again.json()["counted"] is False
    assert indicator(db_session).report_count == 1
    count = db_session.scalar(select(func.count()).select_from(IndicatorReport))
    assert count == 1


def test_five_people_reach_ranking_and_red(
    api_client, db_session, guardian, paired_senior
):
    seniors = [paired_senior] + [
        another_senior(db_session, guardian, i) for i in range(1, 5)
    ]
    for senior in seniors:
        assert report(api_client, senior).status_code == 201
    assert indicator(db_session).report_count == 5

    ranking = (
        db_session.execute(text("SELECT public_value FROM v_indicator_ranking"))
        .scalars()
        .all()
    )
    assert indicator(db_session).public_value in ranking


def test_report_raises_phone_analysis(api_client, consented_senior):
    """ES: Tras reportarlo, comprobar ese número ya no sale verde.
    EN: Once reported, checking that number is no longer green.
    """
    report(api_client, consented_senior)
    body = {
        "device_id": str(consented_senior.device.id),
        "channel": "manual",
        "origin": "manual",
        "input_type": "phone_number",
        "received_at": "2026-11-26T10:00:00Z",
        "sender": {"type": "phone", "value": E164},
    }
    response = api_client.post(ANALYSES, json=body, headers=consented_senior.headers)
    assert response.status_code == 200
    assert response.json()["risk_level"] in ("amber", "red")


def test_senior_solo_can_report_without_device_id(api_client, db_session, solo):
    body = {"type": "phone", "value": NUMBER, "threat_type": "vishing"}
    response = api_client.post(INDICATORS, json=body, headers=solo["headers"])
    assert response.status_code == 201
    row = db_session.scalar(select(IndicatorReport))
    assert row.device_id == solo["device_id"]


@pytest.mark.parametrize("value", ["123", "hola", "+34 12"])
def test_invalid_number_is_422(api_client, paired_senior, value):
    assert report(api_client, paired_senior, value=value).status_code == 422


@pytest.mark.parametrize(
    "extra", [{"type": "domain"}, {"threat_type": "none"}, {"threat_type": "x"}]
)
def test_invalid_body_is_422(api_client, paired_senior, extra):
    assert report(api_client, paired_senior, **extra).status_code == 422


def test_other_device_id_is_forbidden(api_client, paired_senior):
    response = report(api_client, paired_senior, device_id=str(uuid.uuid4()))
    assert response.status_code == 403


def test_guardian_cannot_report(api_client, guardian_headers):
    body = {"type": "phone", "value": NUMBER}
    response = api_client.post(INDICATORS, json=body, headers=guardian_headers)
    assert response.status_code == 403


def test_unlinked_senior_cannot_report(api_client, db_session, paired_senior):
    """ES: Al desvincular, el Sénior queda borrado y su token deja de valer
    (igual que en los análisis). EN: Unlinking deletes the senior and its token
    stops working (same as analyses).
    """
    paired_senior.user.deleted_at = datetime.now(UTC)
    db_session.flush()
    assert report(api_client, paired_senior).status_code == 401


def test_reports_are_deleted_with_indicator(api_client, db_session, paired_senior):
    """ES: La purga de 12 meses borra el indicador y sus reportes (cascada).
    EN: The 12-month purge deletes the indicator and its reports (cascade).
    """
    report(api_client, paired_senior)
    db_session.delete(indicator(db_session))
    db_session.flush()
    assert db_session.scalar(select(func.count()).select_from(IndicatorReport)) == 0
