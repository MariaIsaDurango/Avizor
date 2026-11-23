"""Tests del registro de móviles del Tutor (necesitan PostgreSQL).
Guardian phone registration tests (need PostgreSQL).
"""

import uuid

from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models.user import Device, User
from app.schemas.device import DeviceRead
from app.schemas.enums import UserRole

DEVICES = "/api/v1/devices"
TOKEN = "ExponentPushToken[test-token-1]"


def body(push_token=TOKEN):
    return {"platform": "android", "app_version": "0.5.0", "push_token": push_token}


def other_guardian_headers(db_session, email):
    user = User(
        role=UserRole.GUARDIAN,
        display_name="Otro",
        email=email,
        password_hash=hash_password("contraseña-larga-9"),
    )
    db_session.add(user)
    db_session.flush()
    token = create_access_token(user.id, UserRole.GUARDIAN)
    return user, {"Authorization": f"Bearer {token}"}


def test_register_device(api_client, db_session, guardian, guardian_headers):
    response = api_client.post(DEVICES, json=body(), headers=guardian_headers)
    assert response.status_code == 201
    device = DeviceRead.model_validate(response.json())
    assert "push_token" not in response.json()
    stored = db_session.get(Device, device.id)
    assert stored.user_id == guardian.id
    assert stored.push_token == TOKEN


def test_same_token_is_not_duplicated(api_client, db_session, guardian_headers):
    first = api_client.post(DEVICES, json=body(), headers=guardian_headers).json()
    second = api_client.post(DEVICES, json=body(), headers=guardian_headers).json()
    assert first["id"] == second["id"]
    count = db_session.scalars(select(Device).where(Device.push_token == TOKEN)).all()
    assert len(count) == 1


def test_token_moves_to_the_new_account(api_client, db_session, guardian_headers):
    """ES: Mismo móvil, otra cuenta: la anterior deja de recibir avisos.
    EN: Same phone, another account: the previous one stops getting alerts.
    """
    old = api_client.post(DEVICES, json=body(), headers=guardian_headers).json()
    _, headers = other_guardian_headers(db_session, "otro.movil@example.com")
    api_client.post(DEVICES, json=body(), headers=headers)
    assert db_session.get(Device, uuid.UUID(old["id"])).push_token is None


def test_push_token_is_required(api_client, guardian_headers):
    data = body()
    del data["push_token"]
    response = api_client.post(DEVICES, json=data, headers=guardian_headers)
    assert response.status_code == 422


def test_senior_cannot_register(api_client, paired_senior):
    response = api_client.post(DEVICES, json=body(), headers=paired_senior.headers)
    assert response.status_code == 403


def test_delete_own_device(api_client, db_session, guardian_headers):
    device = api_client.post(DEVICES, json=body(), headers=guardian_headers).json()
    response = api_client.delete(f"{DEVICES}/{device['id']}", headers=guardian_headers)
    assert response.status_code == 204
    assert db_session.get(Device, uuid.UUID(device["id"])) is None


def test_cannot_delete_other_users_device(api_client, db_session, guardian_headers):
    device = api_client.post(DEVICES, json=body(), headers=guardian_headers).json()
    _, headers = other_guardian_headers(db_session, "otro.borrar@example.com")
    response = api_client.delete(f"{DEVICES}/{device['id']}", headers=headers)
    assert response.status_code == 404


def test_cannot_delete_senior_device(api_client, guardian_headers, paired_senior):
    response = api_client.delete(
        f"{DEVICES}/{paired_senior.device.id}", headers=guardian_headers
    )
    assert response.status_code == 404
