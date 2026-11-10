from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ES: Ruta absoluta al .env de la raíz del repo (funciona desde cualquier carpeta).
# EN: Absolute path to the repo root .env (works from any folder).
ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_ENV_FILE, extra="ignore")

    APP_ENV: str = "development"
    CONTRACT_VERSION: str = "1.0.0"

    DATABASE_URL: str
    # ES: Mínimo 32 caracteres (openssl rand -hex 32 genera 64).
    # EN: At least 32 characters (openssl rand -hex 32 generates 64).
    JWT_SECRET: str = Field(min_length=32)
    JWT_EXPIRE_MINUTES: int = 60
    # ES: El móvil del Sénior no inicia sesión: su token dura más.
    # EN: The senior's phone never logs in: its token lasts longer.
    DEVICE_TOKEN_EXPIRE_DAYS: int = 180
    PAIRING_CODE_EXPIRE_MINUTES: int = 10
    PHONE_HMAC_KEY: str = Field(min_length=32)
    # ES: Cada cuánto se borran los datos caducados (0 = desactivado).
    # EN: How often expired data is deleted (0 = disabled).
    RETENTION_PURGE_MINUTES: int = 60


settings = Settings()
