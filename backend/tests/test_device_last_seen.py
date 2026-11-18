"""Tests de la última actividad del móvil del Sénior (necesitan PostgreSQL).
Senior phone last activity tests (need PostgreSQL).
"""

import json
from datetime import UTC, datetime, timedelta

import pytest

from app.services import devices as devices_service
from app.services import manual_analysis as manual_service

ANALYSES = "/api/v1/analyses"
SENIOR = "/api/v1/senior"
# ES: Mensaje inventado ya anonimizado. EN: Fake, already anonymized message.
FAMILY = "Hola, ¿comemos el domingo en casa?"
LONG_AGO = datetime(2026, 1, 1, tzinfo=UTC)


def fast_request(device_id):
    return {
        "device_id": str(device_id),
        "channel": "sms",
        "origin": "automatic",
        "input_type": "text",
        "received_at": "2026-11-18T16:00:00Z",
        "content": {
            "text": FAMILY,
            "urls": [],
            "language": "es",
            "anonymization": {"applied": True, "ner_model_version": "ner-test"},
        },
        "app": {"version": "0.4.0", "android_api": 34},
    }


def manual_request(senior, applied=True):
    meta = {
        "device_id": str(senior.device.id),
        "channel": "manual",
        "origin": "manual",
        "received_at": "2026-11-18T16:00:00Z",
        "text": FAMILY,
        "anonymization": {"applied": applied, "ner_model_version": "ner-test"},
        "attachments": [],
    }
    return {"metadata": (None, json.dumps(meta), "application/json")}


@pytest.fixture
def old_device(db_session, consented_senior):
    consented_senior.device.last_seen_at = LONG_AGO
    db_session.flush()
    return consented_senior


def seen(db_session, senior):
    db_session.refresh(senior.device)
    return senior.device.last_seen_at


# ---------- Análisis / analyses ----------


def test_fast_analysis_updates_last_seen(api_client, db_session, old_device):
    before = datetime.now(UTC)
    response = api_client.post(
        ANALYSES, json=fast_request(old_device.device.id), headers=old_device.headers
    )
    assert response.status_code == 200
    assert seen(db_session, old_device) >= before - timedelta(seconds=1)


def test_manual_analysis_updates_last_seen(
    api_client, db_session, old_device, monkeypatch
):
    monkeypatch.setattr(manual_service, "run_manual_job", lambda job: None)
    response = api_client.post(
        ANALYSES, files=manual_request(old_device), headers=old_device.headers
    )
    assert response.status_code == 202
    assert seen(db_session, old_device) > LONG_AGO


def test_rejected_request_does_not_count(api_client, db_session, old_device):
    # ES: Texto sin anonimizar → 422: no se guarda la actividad.
    # EN: Non-anonymized text → 422: activity is not saved.
    response = api_client.post(
        ANALYSES,
        files=manual_request(old_device, applied=False),
        headers=old_device.headers,
    )
    assert response.status_code == 422
    assert seen(db_session, old_device) == LONG_AGO


def test_guardian_panel_shows_new_activity(
    api_client, db_session, guardian_headers, old_device
):
    api_client.post(
        ANALYSES, json=fast_request(old_device.device.id), headers=old_device.headers
    )
    body = api_client.get(SENIOR, headers=guardian_headers).json()
    assert datetime.fromisoformat(body["last_seen_at"]) > LONG_AGO


# ---------- touch_device ----------


def test_touch_sets_first_activity(db_session, paired_senior):
    paired_senior.device.last_seen_at = None
    db_session.flush()
    now = datetime.now(UTC)
    devices_service.touch_device(db_session, paired_senior.device.id, now)
    assert seen(db_session, paired_senior) == now


def test_touch_writes_at_most_once_per_minute(db_session, paired_senior):
    first = datetime.now(UTC)
    paired_senior.device.last_seen_at = first
    db_session.flush()

    devices_service.touch_device(
        db_session, paired_senior.device.id, first + timedelta(seconds=30)
    )
    assert seen(db_session, paired_senior) == first

    later = first + timedelta(minutes=2)
    devices_service.touch_device(db_session, paired_senior.device.id, later)
    assert seen(db_session, paired_senior) == later
