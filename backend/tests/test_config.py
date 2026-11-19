"""Tests de la configuración (no necesitan PostgreSQL).
Configuration tests (no PostgreSQL needed).
"""

import pytest

from app.core.config import Settings

SECRET = "x" * 32


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "postgresql://u:p@db.railway.internal:5432/railway",
            "postgresql+psycopg://u:p@db.railway.internal:5432/railway",
        ),
        ("postgres://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
        (
            "postgresql+psycopg://u:p@localhost:5432/avizor",
            "postgresql+psycopg://u:p@localhost:5432/avizor",
        ),
    ],
)
def test_database_url_uses_psycopg(raw, expected):
    settings = Settings(
        DATABASE_URL=raw, JWT_SECRET=SECRET, PHONE_HMAC_KEY=SECRET, _env_file=None
    )
    assert settings.DATABASE_URL == expected
