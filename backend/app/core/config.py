from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# ES: Ruta absoluta al .env de la raíz del repo (funciona desde cualquier carpeta).
# EN: Absolute path to the repo root .env (works from any folder).
ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_ENV_FILE, extra="ignore")

    APP_ENV: str = "development"
    CONTRACT_VERSION: str = "1.0.0"

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int = 60
    PHONE_HMAC_KEY: str


settings = Settings()
