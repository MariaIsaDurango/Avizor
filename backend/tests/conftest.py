"""Configuración común de los tests.
Shared test configuration.

ES: En la CI no hay .env: se usan valores de prueba (nunca secretos reales).
EN: There is no .env in CI: test values are used (never real secrets).
"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# ES: No se importa app.* aquí arriba: la configuración fallaría sin estos valores.
# EN: app.* is not imported up here: settings would fail without these values.
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

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
