"""Tests de retirar el consentimiento sin id (#184) y borrar la cuenta (#194).
Tests for withdrawing consent without an id (#184) and deleting the account (#194).

ES: Datos inventados. EN: Fake data.
"""

from datetime import UTC, datetime, timedelta

from conftest import ANALYSES, LOGIN, PHISHING, SOLO, analysis_body
from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models.alert import Alert, Unlock
from app.models.analysis import Analysis
from app.models.user import Consent, Device, Pairing, User
from app.schemas.enums import Channel, ConsentType, UnlockStatus, UserRole

REVOKE_ME = "/api/v1/consents/me/revoke"
ME = "/api/v1/auth/me"
GUARDIAN_PASSWORD = "contraseña-larga-1"


def delete_me(client, headers, password):
    return client.request("DELETE", ME, json={"password": password}, headers=headers)


def send_phishing(client, headers, device_id=None):
    response = client.post(
        ANALYSES, json=analysis_body(PHISHING, device_id), headers=headers
    )
    assert response.status_code in (200, 201)
    return response.json()


# ---------- POST /consents/me/revoke (#184) ----------


def test_senior_revokes_active_consent_without_id(
    api_client, db_session, consented_senior
):
    response = api_client.post(REVOKE_ME, headers=consented_senior.headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1 and body[0]["revoked_at"] is not None
    consent = db_session.scalars(
        select(Consent).where(Consent.senior_id == consented_senior.user.id)
    ).one()
    assert consent.revoked_at is not None


def test_revoke_me_twice_returns_empty(api_client, consented_senior):
    api_client.post(REVOKE_ME, headers=consented_senior.headers)
    second = api_client.post(REVOKE_ME, headers=consented_senior.headers)
    assert second.status_code == 200
    assert second.json() == []


def test_senior_solo_revokes_without_id(api_client, consented_solo):
    response = api_client.post(REVOKE_ME, headers=consented_solo["headers"])
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_revoke_me_keeps_legal_guardianship(
    api_client, db_session, paired_senior, guardian
):
    """ES: La tutela legal la retira el Tutor, no el Sénior.
    EN: Legal guardianship is withdrawn by the guardian, not the senior.
    """
    db_session.add(
        Consent(
            senior_id=paired_senior.user.id,
            type=ConsentType.LEGAL_GUARDIANSHIP,
            scope=[Channel.SMS],
            text_version="accessibility-notice-2026-11",
            granted_by=guardian.id,
            evidence={"document": "resolucion-judicial", "verified": True},
            granted_at=datetime.now(UTC),
        )
    )
    db_session.flush()
    response = api_client.post(REVOKE_ME, headers=paired_senior.headers)
    assert response.json() == []


def test_guardian_cannot_use_revoke_me(api_client, guardian_headers):
    assert api_client.post(REVOKE_ME, headers=guardian_headers).status_code == 403


# ---------- DELETE /auth/me (#194) ----------


def test_senior_solo_deletes_account_and_data(api_client, db_session, consented_solo):
    send_phishing(api_client, consented_solo["headers"])
    response = delete_me(api_client, consented_solo["headers"], SOLO["password"])
    assert response.status_code == 204

    user_id, device_id = consented_solo["user_id"], consented_solo["device_id"]
    assert db_session.get(User, user_id) is None
    assert db_session.get(Device, device_id) is None
    assert (
        db_session.scalars(select(Consent).where(Consent.senior_id == user_id)).all()
        == []
    )
    assert (
        db_session.scalars(
            select(Analysis).where(Analysis.device_id == device_id)
        ).all()
        == []
    )
    # ES/EN: the old token and the password no longer work
    assert api_client.get(ME, headers=consented_solo["headers"]).status_code == 401
    login = api_client.post(
        LOGIN, json={"email": SOLO["email"], "password": SOLO["password"]}
    )
    assert login.status_code == 401


def test_wrong_password_deletes_nothing(api_client, db_session, solo):
    response = delete_me(api_client, solo["headers"], "otra-contraseña")
    assert response.status_code == 400
    assert db_session.get(User, solo["user_id"]) is not None


def test_password_is_required(api_client, solo):
    response = api_client.request("DELETE", ME, json={}, headers=solo["headers"])
    assert response.status_code == 422


def test_paired_senior_has_no_account(api_client, paired_senior):
    response = delete_me(api_client, paired_senior.headers, "lo-que-sea")
    assert response.status_code == 403


def test_guardian_deletion_removes_alerts_and_retires_senior(
    api_client, db_session, guardian, guardian_headers, consented_senior
):
    verdict = send_phishing(
        api_client, consented_senior.headers, consented_senior.device.id
    )
    assert db_session.scalars(
        select(Alert).where(Alert.guardian_id == guardian.id)
    ).all()
    db_session.add(
        Unlock(
            analysis_id=verdict["analysis_id"],
            status=UnlockStatus.APPROVED,
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
            resolved_by=guardian.id,
            resolved_at=datetime.now(UTC),
        )
    )
    consented_senior.device.push_token = "ExponentPushToken[senior-de-prueba]"
    db_session.flush()

    response = delete_me(api_client, guardian_headers, GUARDIAN_PASSWORD)
    assert response.status_code == 204

    db_session.expire_all()
    assert db_session.get(User, guardian.id) is None
    assert db_session.scalars(select(Alert)).all() == []
    assert (
        db_session.scalars(
            select(Pairing).where(Pairing.guardian_id == guardian.id)
        ).all()
        == []
    )
    unlock = db_session.scalars(select(Unlock)).one()
    assert unlock.resolved_by is None
    # ES: Sin Tutor, el Sénior se da de baja como al desvincular.
    # EN: Without a guardian the senior is retired as on unlink.
    senior = db_session.get(User, consented_senior.user.id)
    assert senior.deleted_at is not None
    assert db_session.get(Device, consented_senior.device.id).push_token is None
    assert api_client.get(ME, headers=guardian_headers).status_code == 401


def test_senior_with_another_guardian_stays_active(
    api_client, db_session, guardian_headers, paired_senior
):
    other = User(
        role=UserRole.GUARDIAN,
        display_name="Pablo",
        email="pablo.tutor@example.com",
        password_hash=hash_password("contraseña-larga-2"),
        is_verified=True,
    )
    db_session.add(other)
    db_session.flush()
    db_session.add(
        Pairing(
            guardian_id=other.id,
            senior_id=paired_senior.user.id,
            code="654321",
            senior_display_name="Carmen",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
            redeemed_at=datetime.now(UTC),
        )
    )
    db_session.flush()

    assert delete_me(api_client, guardian_headers, GUARDIAN_PASSWORD).status_code == 204
    db_session.expire_all()
    assert db_session.get(User, paired_senior.user.id).deleted_at is None
    other_headers = {
        "Authorization": f"Bearer {create_access_token(other.id, UserRole.GUARDIAN)}"
    }
    assert api_client.get(ME, headers=other_headers).status_code == 200
