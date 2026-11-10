"""Contraseñas (Argon2) y tokens JWT.
Passwords (Argon2) and JWT tokens.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.schemas.enums import UserRole

JWT_ALGORITHM = "HS256"

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """ES: Nunca se guarda la contraseña, solo su hash Argon2.
    EN: The password is never stored, only its Argon2 hash.
    """
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


class TokenPayload(BaseModel):
    """ES: Contenido del JWT según el contrato: sub + role.
    EN: JWT content as defined in the contract: sub + role.
    """

    sub: uuid.UUID  # ES: id del usuario o dispositivo / EN: user or device id
    role: UserRole
    exp: datetime


def create_access_token(
    subject: uuid.UUID, role: UserRole, expires_minutes: int | None = None
) -> str:
    minutes = expires_minutes or settings.JWT_EXPIRE_MINUTES
    payload = {
        "sub": str(subject),
        "role": role.value,
        "exp": datetime.now(UTC) + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)


class InvalidTokenError(Exception):
    """ES: Token caducado, manipulado o mal formado.
    EN: Expired, tampered or malformed token.
    """


def decode_access_token(token: str) -> TokenPayload:
    try:
        data = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "role", "exp"]},
        )
        return TokenPayload.model_validate(data)
    except (jwt.PyJWTError, ValidationError) as exc:
        raise InvalidTokenError from exc
