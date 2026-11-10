"""Tests de desbloqueos de falsos positivos (necesitan PostgreSQL).
False-positive unlock tests (need PostgreSQL).
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.security import create_access_token, hash_password
from app.models.alert import Unlock as UnlockModel
from app.models.user import User
from app.schemas.enums import UserRole
from app.schemas.unlock import Unlock

UNLOCKS = "/api/v1/unlocks"
ANALYSES = "/api/v1/analyses"


def analyze(api_client, senior, text, urls=()):
    body = {
        "device_id": str(senior.device.id),
        "channel": "sms",
        "origin": "automatic",
        "input_type": "text",
        "received_at": "2026-11-04T13:12:05Z",
        "content": {
            "text": text,
            "urls": list(urls),
            "anonymization": {"applied": True, "ner_model_version": "ner-test"},
        },
    }
    return api_client.post(ANALYSES, json=body, headers=senior.headers).json()


@pytest.fixture
def blocked_analysis_id(api_client, consented_senior):
    verdict = analyze(
        api_client,
        consented_senior,
        "BBVA: su cuenta [IBAN] ha sido bloqueada. Verifique.",
        ["https://bbva-seguro.top/login"],
    )
    assert verdict["action"] == "block_and_alert"
    return verdict["analysis_id"]


@pytest.fixture
def pending(api_client, consented_senior, blocked_analysis_id):
    response = api_client.post(
        UNLOCKS,
        json={"analysis_id": blocked_analysis_id},
        headers=consented_senior.headers,
    )
    assert response.status_code == 201
    return response.json()


def stranger_headers(db_session, email="otro.tutor@example.com"):
    stranger = User(
        role=UserRole.GUARDIAN,
        display_name="Otro",
        email=email,
        password_hash=hash_password("contraseña-larga-2"),
    )
    db_session.add(stranger)
    db_session.flush()
    token = create_access_token(stranger.id, UserRole.GUARDIAN)
    return {"Authorization": f"Bearer {token}"}


# ---------- POST /unlocks ----------


def test_senior_requests_unlock(pending):
    unlock = Unlock.model_validate(pending)
    assert unlock.status == "pending_guardian"
    assert unlock.resolved_by is None
    ttl = unlock.expires_at - unlock.requested_at
    assert timedelta(hours=23) < ttl <= timedelta(hours=24)


def test_request_is_idempotent(api_client, consented_senior, pending):
    again = api_client.post(
        UNLOCKS,
        json={"analysis_id": pending["analysis_id"]},
        headers=consented_senior.headers,
    )
    assert again.json()["id"] == pending["id"]


def test_cannot_unlock_allowed_content(api_client, consented_senior):
    verdict = analyze(api_client, consented_senior, "Hola mamá, llego a las 8.")
    response = api_client.post(
        UNLOCKS,
        json={"analysis_id": verdict["analysis_id"]},
        headers=consented_senior.headers,
    )
    assert response.status_code == 422


def test_unknown_analysis_is_404(api_client, consented_senior):
    response = api_client.post(
        UNLOCKS,
        json={"analysis_id": str(uuid.uuid4())},
        headers=consented_senior.headers,
    )
    assert response.status_code == 404


def test_guardian_cannot_request_unlock(
    api_client, guardian_headers, blocked_analysis_id
):
    response = api_client.post(
        UNLOCKS, json={"analysis_id": blocked_analysis_id}, headers=guardian_headers
    )
    assert response.status_code == 403


# ---------- GET /unlocks ----------


def test_guardian_lists_pending(api_client, guardian_headers, pending):
    items = api_client.get(UNLOCKS, headers=guardian_headers).json()
    assert [item["id"] for item in items] == [pending["id"]]


def test_other_guardian_lists_nothing(api_client, db_session, pending):
    items = api_client.get(UNLOCKS, headers=stranger_headers(db_session)).json()
    assert items == []


def test_senior_polls_status(api_client, consented_senior, pending):
    response = api_client.get(
        f"{UNLOCKS}/{pending['id']}", headers=consented_senior.headers
    )
    assert response.json()["status"] == "pending_guardian"


# ---------- PATCH /unlocks/{id} ----------


@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_guardian_resolves(api_client, guardian, guardian_headers, pending, decision):
    response = api_client.patch(
        f"{UNLOCKS}/{pending['id']}",
        json={"status": decision},
        headers=guardian_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == decision
    assert body["resolved_by"] == str(guardian.id)
    assert body["resolved_at"] is not None


def test_cannot_resolve_twice(api_client, guardian_headers, pending):
    url = f"{UNLOCKS}/{pending['id']}"
    api_client.patch(url, json={"status": "approved"}, headers=guardian_headers)
    second = api_client.patch(
        url, json={"status": "rejected"}, headers=guardian_headers
    )
    assert second.status_code == 409


def test_expired_request_cannot_be_resolved(
    api_client, db_session, guardian_headers, pending
):
    unlock = db_session.get(UnlockModel, uuid.UUID(pending["id"]))
    unlock.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()

    response = api_client.patch(
        f"{UNLOCKS}/{pending['id']}",
        json={"status": "approved"},
        headers=guardian_headers,
    )
    assert response.status_code == 409
    assert db_session.get(UnlockModel, unlock.id).status == "expired"


@pytest.mark.parametrize("status", ["pending_guardian", "expired"])
def test_guardian_cannot_set_system_statuses(
    api_client, guardian_headers, pending, status
):
    response = api_client.patch(
        f"{UNLOCKS}/{pending['id']}", json={"status": status}, headers=guardian_headers
    )
    assert response.status_code == 422


def test_unpaired_guardian_gets_404(api_client, db_session, pending):
    response = api_client.patch(
        f"{UNLOCKS}/{pending['id']}",
        json={"status": "approved"},
        headers=stranger_headers(db_session, "otro2.tutor@example.com"),
    )
    assert response.status_code == 404


def test_senior_cannot_approve_own_request(api_client, consented_senior, pending):
    response = api_client.patch(
        f"{UNLOCKS}/{pending['id']}",
        json={"status": "approved"},
        headers=consented_senior.headers,
    )
    assert response.status_code == 403
