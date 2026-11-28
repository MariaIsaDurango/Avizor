"""Configuración común de los tests.
Shared test configuration.

ES: En la CI no hay .env: se usan valores de prueba (nunca secretos reales).
EN: There is no .env in CI: test values are used (never real secrets).
"""

import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# ES: No se importa app.* aquí arriba: la configuración fallaría sin estos valores.
# EN: app.* is not imported up here: settings would fail without these values.
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
# ES: En los tests no se lanza la limpieza en segundo plano.
# EN: The background purge is not started in tests.
os.environ.setdefault("RETENTION_PURGE_MINUTES", "0")
os.environ.setdefault("APP_ENV", "test")

if not ROOT_ENV_FILE.exists():
    os.environ.setdefault(
        "DATABASE_URL", "postgresql+psycopg://avizor:avizor@localhost:5432/avizor"
    )
    os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production-0123456789")
    os.environ.setdefault("PHONE_HMAC_KEY", "test-hmac-key-not-for-production")


@pytest.fixture
def db_session():
    """ES: Sesión dentro de una transacción que se deshace al acabar cada test.
    La base de datos queda igual que antes. Se salta si no hay PostgreSQL.
    EN: Session inside a transaction rolled back after each test.
    The database is left untouched. Skipped if PostgreSQL is not available.
    """
    from app.db.session import engine

    try:
        connection = engine.connect()
    except OperationalError:
        pytest.skip("PostgreSQL no disponible / PostgreSQL not available")
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def api_client(db_session):
    """ES: Cliente HTTP de la app que usa la sesión de test.
    EN: App HTTP client that uses the test session.
    """
    from app.db.session import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def guardian(db_session):
    """ES: Tutor de prueba guardado en la BD (datos inventados).
    EN: Test guardian stored in the DB (fake data).
    """
    from app.core.security import hash_password
    from app.models.user import User
    from app.schemas.enums import UserRole

    user = User(
        role=UserRole.GUARDIAN,
        display_name="Lucía",
        email="lucia.tutora@example.com",
        password_hash=hash_password("contraseña-larga-1"),
        is_verified=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def guardian_headers(guardian):
    """ES: Cabecera Authorization del Tutor de prueba.
    EN: Authorization header of the test guardian.
    """
    from app.core.security import create_access_token
    from app.schemas.enums import UserRole

    token = create_access_token(guardian.id, UserRole.GUARDIAN)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def paired_senior(db_session, guardian):
    """ES: Sénior ya vinculado al Tutor de prueba, con su dispositivo y token.
    EN: Senior already paired with the test guardian, with device and token.
    """
    from datetime import UTC, datetime, timedelta
    from types import SimpleNamespace

    from app.core.security import create_access_token
    from app.models.user import Device, Pairing, User
    from app.schemas.enums import UserRole

    now = datetime.now(UTC)
    senior = User(role=UserRole.SENIOR, display_name="Carmen")
    db_session.add(senior)
    db_session.flush()
    device = Device(user_id=senior.id, platform="android", app_version="0.4.0")
    pairing = Pairing(
        guardian_id=guardian.id,
        senior_id=senior.id,
        code="123456",
        senior_display_name="Carmen",
        expires_at=now + timedelta(minutes=10),
        redeemed_at=now,
    )
    db_session.add_all([device, pairing])
    db_session.flush()
    token = create_access_token(device.id, UserRole.SENIOR)
    return SimpleNamespace(
        user=senior, device=device, headers={"Authorization": f"Bearer {token}"}
    )


@pytest.fixture
def consented_senior(db_session, paired_senior):
    """ES: Sénior vinculado que ya ha dado su consentimiento (todos los canales).
    EN: Paired senior who has already given consent (all channels).
    """
    from datetime import UTC, datetime

    from app.models.user import Consent
    from app.schemas.enums import Channel, ConsentType

    db_session.add(
        Consent(
            senior_id=paired_senior.user.id,
            type=ConsentType.SELF,
            scope=[Channel.SMS, Channel.NOTIFICATION, Channel.SCREEN, Channel.CALL],
            text_version="accessibility-notice-2026-11",
            granted_by=paired_senior.user.id,
            granted_at=datetime.now(UTC),
        )
    )
    db_session.flush()
    return paired_senior


# ---------- Sénior sin Tutor (#174) / Senior without a guardian ----------

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ANALYSES = "/api/v1/analyses"
CONSENTS = "/api/v1/consents"

# ES: Datos inventados, nunca reales. EN: Fake data, never real.
SOLO = {
    "email": "Mayor.Solo@Example.com",
    "password": "contraseña-larga-1",
    "display_name": "Carmen",
    "role": "senior_solo",
    "device": {"platform": "android", "app_version": "1.0.0"},
}
PHISHING = (
    "BBVA: su cuenta ha sido bloqueada. Introduzca su [IBAN] y su clave "
    "urgente en https://bbva-seguro.top/login"
)


def analysis_body(text, device_id=None, channel="sms"):
    body = {
        "channel": channel,
        "origin": "automatic",
        "input_type": "text",
        "received_at": "2026-11-24T13:12:05Z",
        "content": {
            "text": text,
            "urls": [],
            "language": "es",
            "anonymization": {
                "applied": True,
                "ner_model_version": "regex-v0",
                "redacted_entities": ["IBAN"],
            },
        },
    }
    if device_id is not None:
        body["device_id"] = str(device_id)
    return body


@pytest.fixture
def solo(api_client, db_session):
    """ES: senior_solo registrado y verificado (la verificación se prueba aparte).
    EN: Registered and verified senior_solo (verification is tested elsewhere).
    """
    from app.models.user import User

    response = api_client.post(REGISTER, json=SOLO)
    assert response.status_code == 201
    user = db_session.get(User, uuid.UUID(response.json()["id"]))
    user.is_verified = True
    db_session.flush()
    login = api_client.post(
        LOGIN, json={"email": SOLO["email"], "password": SOLO["password"]}
    )
    assert login.status_code == 200
    data = login.json()
    return {
        "user_id": user.id,
        "device_id": uuid.UUID(data["device_id"]),
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


@pytest.fixture
def consented_solo(api_client, solo):
    body = {
        "senior_id": str(solo["user_id"]),
        "type": "self",
        "scope": ["sms", "notification", "screen", "call"],
        "text_version": "accessibility-notice-2026-11",
        "granted_by": str(solo["user_id"]),
        "evidence": None,
        "granted_at": "2026-11-24T10:00:00Z",
    }
    response = api_client.post(CONSENTS, json=body, headers=solo["headers"])
    assert response.status_code == 201
    return solo
