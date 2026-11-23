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


def test_empty_ml_settings_mean_not_set(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setenv("ML_MODEL_DIR", "")
    monkeypatch.setenv("ML_FRAUD_THRESHOLD", "")
    settings = Settings()
    assert settings.ML_MODEL_DIR is None
    assert settings.ML_FRAUD_THRESHOLD is None
    assert settings.CLASSIFIER_PROVIDER == "keywords"


def test_ml_threshold_must_be_a_probability(monkeypatch):
    from pydantic import ValidationError

    from app.core.config import Settings

    monkeypatch.setenv("ML_FRAUD_THRESHOLD", "1.5")
    with pytest.raises(ValidationError):
        Settings()
