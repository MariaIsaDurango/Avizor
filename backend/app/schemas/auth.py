"""Schemas de registro e inicio de sesión del Tutor.
Guardian sign-up and login schemas.

ES: No están en el Contrato v1.0.0: es un añadido MINOR (campos y rutas nuevas).
EN: Not in Contract v1.0.0: a MINOR addition (new fields and routes).
"""

from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import ContractModel
from app.schemas.enums import UserRole

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class GuardianRegister(ContractModel):
    email: str = Field(max_length=254, pattern=EMAIL_PATTERN)
    # ES: Mínimo 10 caracteres. EN: At least 10 characters.
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=1, max_length=50)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class LoginRequest(ContractModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class TokenResponse(ContractModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    # ES: Segundos hasta que caduca. EN: Seconds until it expires.
    expires_in: int


class UserRead(ContractModel):
    """ES: Nunca incluye password_hash. EN: Never includes password_hash."""

    id: UUID
    role: UserRole
    display_name: str
    email: str | None = None
