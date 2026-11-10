"""Tests de consentimientos (necesitan PostgreSQL).
Consent tests (need PostgreSQL).
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.schemas.enums import Channel, UserRole
from app.services.consent import has_active_consent

CONSENTS = "/api/v1/consents"
EVIDENCE = {"document": "court_ruling", "reference": "JDO-123/2026"}


def self_consent(senior_id, **changes):
    body = {
        "senior_id": str(senior_id),
        "type": "self",
        "scope": ["sms", "notification", "screen", "call"],
        "text_version": "accessibility-notice-2026-11",
        "granted_by": str(senior_id),
        "evidence": None,
        "granted_at": "2026-11-04T10:00:00Z",
    }
    return {**body, **changes}


def guardianship(senior_id, guardian_id, **changes):
    defaults = {
        "type": "legal_guardianship",
        "granted_by": str(guardian_id),
        "evidence": EVIDENCE,
    }
    return self_consent(senior_id, **{**defaults, **changes})


# ---------- Consentimiento propio / Self consent ----------


def test_senior_gives_own_consent(api_client, paired_senior):
    senior_id = paired_senior.user.id
    response = api_client.post(
        CONSENTS, json=self_consent(senior_id), headers=paired_senior.headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["granted_by"] == str(senior_id)


def test_server_sets_granted_at(api_client, paired_senior):
    """ES: No se confía en la fecha del cliente. EN: Client date is not trusted."""
    response = api_client.post(
        CONSENTS,
        json=self_consent(paired_senior.user.id),
        headers=paired_senior.headers,
    )
    granted_at = datetime.fromisoformat(response.json()["granted_at"])
    assert datetime.now(UTC) - granted_at < timedelta(minutes=1)


def test_senior_cannot_consent_for_someone_else(api_client, paired_senior):
    other = uuid.uuid4()
    response = api_client.post(
        CONSENTS,
        json=self_consent(other, granted_by=str(other)),
        headers=paired_senior.headers,
    )
    assert response.status_code == 403


def test_granted_by_must_match_the_caller(api_client, paired_senior):
    body = self_consent(paired_senior.user.id, granted_by=str(uuid.uuid4()))
    response = api_client.post(CONSENTS, json=body, headers=paired_senior.headers)
    assert response.status_code == 403


def test_guardian_cannot_give_self_consent(api_client, paired_senior, guardian_headers):
    response = api_client.post(
        CONSENTS, json=self_consent(paired_senior.user.id), headers=guardian_headers
    )
    assert response.status_code == 403


# ---------- Tutela legal / Legal guardianship ----------


def test_paired_guardian_records_legal_guardianship(
    api_client, paired_senior, guardian, guardian_headers
):
    body = guardianship(paired_senior.user.id, guardian.id)
    response = api_client.post(CONSENTS, json=body, headers=guardian_headers)
    assert response.status_code == 201
    assert response.json()["evidence"]["reference"] == "JDO-123/2026"


def test_legal_guardianship_without_evidence_is_rejected(
    api_client, paired_senior, guardian, guardian_headers
):
    body = guardianship(paired_senior.user.id, guardian.id, evidence=None)
    response = api_client.post(CONSENTS, json=body, headers=guardian_headers)
    assert response.status_code == 422


def test_unpaired_guardian_cannot_record_guardianship(
    api_client, db_session, paired_senior
):
    stranger = User(
        role=UserRole.GUARDIAN,
        display_name="Otro",
        email="otro.tutor@example.com",
        password_hash=hash_password("contraseña-larga-2"),
    )
    db_session.add(stranger)
    db_session.flush()
    token = create_access_token(stranger.id, UserRole.GUARDIAN)

    response = api_client.post(
        CONSENTS,
        json=guardianship(paired_senior.user.id, stranger.id),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_senior_cannot_record_guardianship(api_client, paired_senior, guardian):
    body = guardianship(paired_senior.user.id, guardian.id)
    response = api_client.post(CONSENTS, json=body, headers=paired_senior.headers)
    assert response.status_code == 403


def test_consent_requires_token(api_client, paired_senior):
    response = api_client.post(CONSENTS, json=self_consent(paired_senior.user.id))
    assert response.status_code == 401


# ---------- Consentimiento vigente / Active consent ----------


@pytest.mark.parametrize(
    ("channel", "expected"), [(Channel.SMS, True), (Channel.MANUAL, False)]
)
def test_has_active_consent_checks_scope(
    api_client, db_session, paired_senior, channel, expected
):
    api_client.post(
        CONSENTS,
        json=self_consent(paired_senior.user.id),
        headers=paired_senior.headers,
    )
    assert has_active_consent(db_session, paired_senior.user.id, channel) is expected


def test_no_consent_means_not_active(db_session, paired_senior):
    assert not has_active_consent(db_session, paired_senior.user.id, Channel.SMS)


# ---------- Revocar / Revoke ----------


def revoke(api_client, consent_id, headers):
    return api_client.post(f"{CONSENTS}/{consent_id}/revoke", headers=headers)


@pytest.fixture
def given_consent(api_client, paired_senior):
    response = api_client.post(
        CONSENTS,
        json=self_consent(paired_senior.user.id),
        headers=paired_senior.headers,
    )
    return response.json()


def test_senior_revokes_own_consent(
    api_client, db_session, paired_senior, given_consent
):
    response = revoke(api_client, given_consent["id"], paired_senior.headers)
    assert response.status_code == 200
    assert response.json()["revoked_at"] is not None
    assert not has_active_consent(db_session, paired_senior.user.id, Channel.SMS)


def test_revoke_twice_keeps_first_date(api_client, paired_senior, given_consent):
    first = revoke(api_client, given_consent["id"], paired_senior.headers).json()
    second = revoke(api_client, given_consent["id"], paired_senior.headers).json()
    assert first["revoked_at"] == second["revoked_at"]


def test_guardian_cannot_revoke_senior_self_consent(
    api_client, guardian_headers, given_consent
):
    response = revoke(api_client, given_consent["id"], guardian_headers)
    assert response.status_code == 404


def test_paired_guardian_revokes_guardianship(
    api_client, paired_senior, guardian, guardian_headers
):
    created = api_client.post(
        CONSENTS,
        json=guardianship(paired_senior.user.id, guardian.id),
        headers=guardian_headers,
    ).json()
    response = revoke(api_client, created["id"], guardian_headers)
    assert response.status_code == 200


def test_revoke_unknown_consent(api_client, paired_senior):
    response = revoke(api_client, uuid.uuid4(), paired_senior.headers)
    assert response.status_code == 404
