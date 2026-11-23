from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ES: Lee primero el .env de la raíz del repo y luego el de backend/ (si existe).
#     El backend/ sobreescribe la raíz, así que funciona en ambos setups.
# EN: Reads root .env first, then backend/ .env (if present).
#     backend/ overrides root, so it works in both setups.
ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_ENV_FILE, BACKEND_ENV_FILE), extra="ignore"
    )

    APP_ENV: str = "development"
    CONTRACT_VERSION: str = "1.0.0"

    DATABASE_URL: str

    @field_validator("DATABASE_URL")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        """ES: Railway y otros servicios dan "postgresql://" o "postgres://".
        SQLAlchemy usaría psycopg2 (no instalado); forzamos psycopg 3.
        EN: Railway and other hosts give "postgresql://" or "postgres://".
        SQLAlchemy would pick psycopg2 (not installed); we force psycopg 3.
        """
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

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
    # ES: "log" solo lo escribe en el log (desarrollo); "expo" envía el push real.
    # EN: "log" only writes it to the log (development); "expo" sends the real push.
    PUSH_PROVIDER: Literal["log", "expo"] = "log"
    # ES: Opcional: solo si el proyecto de Expo exige token de acceso.
    # EN: Optional: only if the Expo project requires an access token.
    EXPO_ACCESS_TOKEN: str | None = None

    # ES: "log" solo escribe el correo en el log (desarrollo); "smtp" lo envía
    #     por Gmail (local); "brevo" lo envía por la API HTTPS de Brevo
    #     (Railway bloquea el SMTP en los planes Free, Trial y Hobby).
    # EN: "log" only writes the email to the log (development); "smtp" sends it
    #     through Gmail (local); "brevo" sends it through Brevo's HTTPS API
    #     (Railway blocks SMTP on the Free, Trial and Hobby plans).
    MAIL_PROVIDER: Literal["log", "smtp", "brevo"] = "log"
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str | None = None
    # ES: Gmail: contraseña de aplicación, nunca la normal. Solo en el .env.
    # EN: Gmail: app password, never the normal one. Only in the .env.
    MAIL_PASSWORD: str | None = None
    MAIL_FROM: str | None = None
    # ES: Clave de API de Brevo. Solo en el .env o en Railway, nunca en el repo.
    # EN: Brevo API key. Only in the .env or Railway, never in the repo.
    BREVO_API_KEY: SecretStr = SecretStr("")
    EMAIL_CODE_EXPIRE_MINUTES: int = 15
    EMAIL_CODE_MAX_ATTEMPTS: int = 5
    # ES: Dirección donde se abre el enlace para cambiar la contraseña.
    # EN: Address where the password reset link opens.
    FRONTEND_URL: str = "http://localhost:8000"
    PASSWORD_RESET_EXPIRE_MINUTES: int = 15

    # ES: Clasificador de texto (#38): "keywords" (reglas) o "ml" (modelo ONNX).
    #     Si "ml" no puede cargar el modelo, se usan las reglas.
    # EN: Text classifier (#38): "keywords" (rules) or "ml" (ONNX model).
    #     If "ml" cannot load the model, rules are used.
    CLASSIFIER_PROVIDER: Literal["keywords", "ml"] = "keywords"
    # ES: Carpeta con avizor_classifier.json, model.int8.onnx y tokenizer.json.
    # EN: Folder with avizor_classifier.json, model.int8.onnx and tokenizer.json.
    ML_MODEL_DIR: str | None = None
    # ES: Vacío = el umbral del paquete del modelo. EN: Empty = the bundle's threshold.
    ML_FRAUD_THRESHOLD: float | None = Field(default=None, gt=0, lt=1)
    ML_THREADS: int = Field(default=1, ge=1)

    @field_validator("ML_MODEL_DIR", "ML_FRAUD_THRESHOLD", mode="before")
    @classmethod
    def empty_is_none(cls, value):
        """ES: "ML_FRAUD_THRESHOLD=" vacío (como en .env.example) = sin valor.
        EN: An empty "ML_FRAUD_THRESHOLD=" (as in .env.example) = no value.
        """
        return None if isinstance(value, str) and not value.strip() else value

    # Issue #42: remote egress is limited to an explicit reviewed URL list.
    AVIZOR_RAG_ENABLED: bool = False
    AVIZOR_PHISHTANK_LOCAL: bool = True
    AVIZOR_EXTERNAL_URLS: bool = False
    AVIZOR_REPUTATION_PUBLIC_URLS: list[str] = Field(default_factory=list)
    AVIZOR_VT_KEY: SecretStr = SecretStr("")
    AVIZOR_GSB_KEY: SecretStr = SecretStr("")


settings = Settings()
