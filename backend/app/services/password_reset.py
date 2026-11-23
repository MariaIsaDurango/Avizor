"""Recuperación de contraseña del Tutor con un enlace de un solo uso.
Guardian password recovery with a single-use link.

ES: El token es un JWT firmado con purpose "reset_password" y audiencia
    propia, así que no sirve como token de sesión (ni al revés). Caduca en
    PASSWORD_RESET_EXPIRE_MINUTES.
    Un solo uso sin tabla nueva ni lista negra: el token lleva una huella
    del password_hash actual. Al cambiar la contraseña, la huella deja de
    coincidir y el enlace (y cualquier otro enlace pendiente) deja de valer.
    Una lista negra en memoria se perdería al reiniciar el servidor y no se
    comparte entre varios procesos.
EN: The token is a signed JWT with purpose "reset_password" and its own
    audience, so it cannot be used as a session token (nor the reverse).
    It expires after PASSWORD_RESET_EXPIRE_MINUTES.
    Single use with no new table or blacklist: the token carries a
    fingerprint of the current password_hash. Once the password changes,
    the fingerprint no longer matches and the link (and any other pending
    link) stops working. An in-memory blacklist would be lost on restart
    and is not shared between processes.
"""

import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError
from app.core.security import JWT_ALGORITHM, hash_password
from app.models.user import User
from app.schemas.enums import ErrorCode, UserRole

PURPOSE = "reset_password"
AUDIENCE = "avizor:reset-password"
INVALID_LINK = "El enlace no es válido o ha caducado. Pide uno nuevo."
RESET_ROLES = (UserRole.GUARDIAN, UserRole.ADMIN)


def _fingerprint(password_hash: str) -> str:
    """ES: Huella corta del hash; el hash nunca viaja en el token.
    EN: Short fingerprint of the hash; the hash never travels in the token.
    """
    digest = hmac.new(
        settings.JWT_SECRET.encode(), password_hash.encode(), hashlib.sha256
    )
    return digest.hexdigest()[:32]


def create_reset_token(user: User, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "purpose": PURPOSE,
        "aud": AUDIENCE,
        "pwd": _fingerprint(user.password_hash or ""),
        "iat": now,
        "exp": now + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)


def build_reset_link(token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"


def _active_user(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User).where(
            User.email == email,
            User.role.in_(RESET_ROLES),
            User.deleted_at.is_(None),
            User.password_hash.is_not(None),
        )
    )


def request_reset(db: Session, email: str) -> str | None:
    """ES: Devuelve el enlace si la cuenta existe; None si no (la API responde
    igual en ambos casos para no revelar qué emails están registrados).
    EN: Returns the link if the account exists; None otherwise (the API
    answers the same way so it does not reveal which emails are registered).
    """
    user = _active_user(db, email)
    if user is None:
        return None
    return build_reset_link(create_reset_token(user))


def reset_password(db: Session, token: str, new_password: str) -> None:
    invalid = ApiError(400, ErrorCode.VALIDATION_ERROR, INVALID_LINK)
    try:
        data = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience=AUDIENCE,
            options={"require": ["sub", "purpose", "pwd", "exp"]},
        )
        user_id = uuid.UUID(data["sub"])
    except (jwt.PyJWTError, ValueError):
        raise invalid from None
    if data["purpose"] != PURPOSE:
        raise invalid

    # ES: Bloqueo de fila: dos peticiones con el mismo enlace no pasan las dos.
    # EN: Row lock: two requests with the same link cannot both succeed.
    user = db.scalar(
        select(User)
        .where(
            User.id == user_id,
            User.role.in_(RESET_ROLES),
            User.deleted_at.is_(None),
            User.password_hash.is_not(None),
        )
        .with_for_update()
    )
    if user is None or not hmac.compare_digest(
        data["pwd"], _fingerprint(user.password_hash)
    ):
        raise invalid

    user.password_hash = hash_password(new_password)
    # ES: Si alguien entró con la contraseña robada, pierde la sesión.
    # EN: Anyone who logged in with the stolen password loses the session.
    user.token_version += 1
    # ES: Abrir el enlace del correo demuestra que el email es suyo.
    # EN: Opening the emailed link proves the email belongs to them.
    user.is_verified = True
    user.verification_code_hash = None
    user.verification_code_expires_at = None
    user.verification_attempts = 0
    db.commit()
