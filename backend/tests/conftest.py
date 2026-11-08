"""Configuración común de los tests.
Shared test configuration.

ES: En la CI no hay .env: se usan valores de prueba (nunca secretos reales).
EN: There is no .env in CI: test values are used (never real secrets).
"""

import os
from pathlib import Path

# ES: No se importa app.core.config aquí: fallaría antes de poner los valores.
# EN: app.core.config is not imported here: it would fail before setting values.
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

if not ROOT_ENV_FILE.exists():
    os.environ.setdefault(
        "DATABASE_URL", "postgresql+psycopg://avizor:avizor@localhost:5432/avizor"
    )
    os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production-0123456789")
    os.environ.setdefault("PHONE_HMAC_KEY", "test-hmac-key-not-for-production")
