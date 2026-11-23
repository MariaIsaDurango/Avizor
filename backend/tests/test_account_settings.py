"""Tests de los ajustes de cuenta del Tutor y del Sénior vinculado (#117).
Guardian account and linked senior settings tests (#117). Need PostgreSQL.
"""

from datetime import UTC, datetime, timedelta

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import Pairing, User
from app.schemas.enums import UserRole

ME = "/api/v1/auth/me"
CHANGE_PASSWORD = "/api/v1/auth/change-password"
LOGIN = "/api/v1/auth/login"
SENIOR = "/api/v1/senior"
ACCESSIBILITY = "/api/v1/senior/accessibility"
SENIOR_ME = "/api/v1/senior/me"
ANALYSES = "/api/v1/analyses"

# ES: Contraseña del Tutor de conftest. EN: Password of the conftest guardian.
CURRENT = "contraseña-larga-1"
NEW = "contraseña-nueva-9"
PROFILE = {
    "color_blindness": True,
    "low_vision": False,
    "blindness": False,
    "hearing_impairment": True,
}


def other_guardian(db_session, email="otro.tutor@example.com"):
    user = User(
        role=UserRole.GUARDIAN,
        display_name="Pablo",
        email=email,
        password_hash=hash_password(CURRENT),
        is_verified=True,
    )
    db_session.add(user)
    db_session.flush()
    token = create_access_token(user.id, UserRole.GUARDIAN)
    return user, {"Authorization": f"Bearer {token}"}


# ---------- PATCH /auth/me ----------


def test_update_name(api_client, db_session, guardian, guardian_headers):
    response = api_client.patch(
        ME, json={"display_name": "  Lucía M.  "}, headers=guardian_headers
    )
    assert response.status_code == 200
    assert response.json()["display_name"] == "Lucía M."
    db_session.refresh(guardian)
    assert guardian.display_name == "Lucía M."


def test_update_name_rejects_blank_and_long(api_client, guardian_headers):
    for name in ["   ", "", "x" * 51]:
        response = api_client.patch(
            ME, json={"display_name": name}, headers=guardian_headers
        )
        assert response.status_code == 422


def test_update_name_ignores_other_fields(
    api_client, db_session, guardian, guardian_headers
):
    response = api_client.patch(
        ME,
        json={"display_name": "Lucía", "role": "admin", "email": "x@example.com"},
        headers=guardian_headers,
    )
    assert response.status_code == 200
    db_session.refresh(guardian)
    assert guardian.role == UserRole.GUARDIAN
    assert guardian.email == "lucia.tutora@example.com"


def test_update_name_requires_guardian(api_client, paired_senior):
    assert api_client.patch(ME, json={"display_name": "X"}).status_code == 401
    response = api_client.patch(
        ME, json={"display_name": "X"}, headers=paired_senior.headers
    )
    assert response.status_code == 403


# ---------- POST /auth/change-password ----------


def change(api_client, headers, current=CURRENT, new=NEW):
    return api_client.post(
        CHANGE_PASSWORD,
        json={"current_password": current, "new_password": new},
        headers=headers,
    )


def test_change_password(api_client, db_session, guardian, guardian_headers):
    assert change(api_client, guardian_headers).status_code == 204
    db_session.refresh(guardian)
    assert verify_password(NEW, guardian.password_hash)
    email = guardian.email
    assert (
        api_client.post(LOGIN, json={"email": email, "password": CURRENT}).status_code
        == 401
    )
    assert (
        api_client.post(LOGIN, json={"email": email, "password": NEW}).status_code
        == 200
    )


def test_wrong_current_password(api_client, db_session, guardian, guardian_headers):
    response = change(api_client, guardian_headers, current="no-es-la-buena")
    assert response.status_code == 400
    assert "actual no es correcta" in response.json()["detail"]
    db_session.refresh(guardian)
    assert verify_password(CURRENT, guardian.password_hash)


def test_new_password_too_short(api_client, guardian_headers):
    assert change(api_client, guardian_headers, new="corta").status_code == 422


def test_new_password_must_differ(api_client, guardian_headers):
    response = change(api_client, guardian_headers, new=CURRENT)
    assert response.status_code == 400


def test_change_password_requires_guardian(api_client, paired_senior):
    assert change(api_client, {}).status_code == 401
    assert change(api_client, paired_senior.headers).status_code == 403


# ---------- PATCH /senior/accessibility ----------


def test_update_accessibility(api_client, db_session, guardian_headers, paired_senior):
    response = api_client.patch(ACCESSIBILITY, json=PROFILE, headers=guardian_headers)
    assert response.status_code == 200
    assert response.json() == PROFILE
    db_session.refresh(paired_senior.user)
    assert paired_senior.user.accessibility_profile == PROFILE
    # ES: La app del Sénior lo recibe. EN: The senior app receives it.
    me = api_client.get(SENIOR_ME, headers=paired_senior.headers).json()
    assert me["accessibility_profile"] == PROFILE


def test_update_accessibility_partial_fills_false(
    api_client, guardian_headers, paired_senior
):
    response = api_client.patch(
        ACCESSIBILITY, json={"low_vision": True}, headers=guardian_headers
    )
    assert response.status_code == 200
    assert response.json() == {
        "color_blindness": False,
        "low_vision": True,
        "blindness": False,
        "hearing_impairment": False,
    }


def test_update_accessibility_rejects_unknown_fields(
    api_client, guardian_headers, paired_senior
):
    response = api_client.patch(
        ACCESSIBILITY, json={"diagnosis": "glaucoma"}, headers=guardian_headers
    )
    assert response.status_code == 422


def test_update_accessibility_without_senior_is_404(api_client, guardian_headers):
    response = api_client.patch(ACCESSIBILITY, json=PROFILE, headers=guardian_headers)
    assert response.status_code == 404


def test_other_guardian_cannot_change_profile(api_client, db_session, paired_senior):
    _, headers = other_guardian(db_session)
    response = api_client.patch(ACCESSIBILITY, json=PROFILE, headers=headers)
    assert response.status_code == 404
    db_session.refresh(paired_senior.user)
    assert paired_senior.user.accessibility_profile is None


def test_senior_cannot_change_profile(api_client, paired_senior):
    response = api_client.patch(
        ACCESSIBILITY, json=PROFILE, headers=paired_senior.headers
    )
    assert response.status_code == 403


# ---------- DELETE /senior ----------


def test_unlink_senior(api_client, db_session, guardian_headers, paired_senior):
    paired_senior.device.push_token = "ExponentPushToken[prueba]"
    db_session.flush()

    assert api_client.delete(SENIOR, headers=guardian_headers).status_code == 204
    assert api_client.get(SENIOR, headers=guardian_headers).status_code == 404

    db_session.refresh(paired_senior.user)
    db_session.refresh(paired_senior.device)
    assert paired_senior.user.deleted_at is not None
    assert paired_senior.device.push_token is None


def test_unlinked_device_token_stops_working(
    api_client, guardian_headers, paired_senior
):
    api_client.delete(SENIOR, headers=guardian_headers)
    assert api_client.get(SENIOR_ME, headers=paired_senior.headers).status_code == 404
    # ES: Un análisis con el token antiguo ya no se acepta.
    # EN: An analysis with the old token is no longer accepted.
    response = api_client.post(
        ANALYSES,
        json={
            "device_id": str(paired_senior.device.id),
            "channel": "sms",
            "origin": "automatic",
            "input_type": "text",
            "received_at": "2026-11-19T10:00:00Z",
            "content": {
                "text": "Hola, ¿comemos el domingo?",
                "urls": [],
                "language": "es",
                "anonymization": {"applied": True, "ner_model_version": "ner-test"},
            },
            "app": {"version": "0.5.0", "android_api": 34},
        },
        headers=paired_senior.headers,
    )
    assert response.status_code == 401


def test_unlink_twice_is_404(api_client, guardian_headers, paired_senior):
    assert api_client.delete(SENIOR, headers=guardian_headers).status_code == 204
    assert api_client.delete(SENIOR, headers=guardian_headers).status_code == 404


def test_unlink_without_senior_is_404(api_client, guardian_headers):
    assert api_client.delete(SENIOR, headers=guardian_headers).status_code == 404


def test_other_guardian_cannot_unlink(api_client, db_session, paired_senior):
    _, headers = other_guardian(db_session)
    assert api_client.delete(SENIOR, headers=headers).status_code == 404
    db_session.refresh(paired_senior.user)
    assert paired_senior.user.deleted_at is None


def test_senior_stays_active_if_another_guardian_remains(
    api_client, db_session, guardian_headers, paired_senior
):
    # ES: Segundo Tutor vinculado al mismo Sénior (decisión abierta en el ADR 4).
    # EN: Second guardian linked to the same senior (open decision, ADR 4).
    second, second_headers = other_guardian(db_session)
    now = datetime.now(UTC)
    db_session.add(
        Pairing(
            guardian_id=second.id,
            senior_id=paired_senior.user.id,
            code="654321",
            senior_display_name="Carmen",
            expires_at=now + timedelta(minutes=10),
            redeemed_at=now,
        )
    )
    db_session.flush()

    assert api_client.delete(SENIOR, headers=guardian_headers).status_code == 204
    db_session.refresh(paired_senior.user)
    assert paired_senior.user.deleted_at is None
    assert api_client.get(SENIOR, headers=second_headers).status_code == 200
    assert api_client.get(SENIOR_ME, headers=paired_senior.headers).status_code == 200


# ---------- Cerrar sesiones / close sessions (token_version) ----------


def login_token(api_client, email, password):
    response = api_client.post(LOGIN, json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_change_password_closes_all_sessions(api_client, guardian):
    phone = login_token(api_client, guardian.email, CURRENT)
    laptop = login_token(api_client, guardian.email, CURRENT)
    assert api_client.get(ME, headers=laptop).status_code == 200

    assert change(api_client, phone).status_code == 204

    for headers in (phone, laptop):
        response = api_client.get(ME, headers=headers)
        assert response.status_code == 401
        assert "Vuelve a iniciar sesión" in response.json()["detail"]
    new_session = login_token(api_client, guardian.email, NEW)
    assert api_client.get(ME, headers=new_session).status_code == 200


def test_failed_change_keeps_sessions(api_client, guardian):
    session = login_token(api_client, guardian.email, CURRENT)
    assert change(api_client, session, current="no-es-la-buena").status_code == 400
    assert api_client.get(ME, headers=session).status_code == 200


def test_password_reset_closes_sessions(api_client, db_session, guardian):
    from app.services import password_reset

    session = login_token(api_client, guardian.email, CURRENT)
    token = password_reset.create_reset_token(guardian)
    response = api_client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": NEW}
    )
    assert response.status_code == 204
    assert api_client.get(ME, headers=session).status_code == 401


def test_deleted_guardian_token_stops_working(api_client, db_session, guardian):
    session = login_token(api_client, guardian.email, CURRENT)
    guardian.deleted_at = datetime.now(UTC)
    db_session.flush()
    assert api_client.get(ME, headers=session).status_code == 401


def test_senior_token_not_affected(api_client, guardian_headers, paired_senior):
    assert change(api_client, guardian_headers).status_code == 204
    response = api_client.get(SENIOR_ME, headers=paired_senior.headers)
    assert response.status_code == 200
