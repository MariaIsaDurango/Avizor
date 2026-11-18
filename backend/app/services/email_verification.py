"""Verificación del email del Tutor con un código de 6 dígitos.
Guardian email verification with a 6-digit code.

ES: El código se guarda como HMAC (con la clave del servidor), caduca en
    EMAIL_CODE_EXPIRE_MINUTES y admite EMAIL_CODE_MAX_ATTEMPTS intentos.
    Los errores son genéricos para no revelar qué emails existen.
EN: The code is stored as an HMAC (with the server key), expires after
    EMAIL_CODE_EXPIRE_MINUTES and allows EMAIL_CODE_MAX_ATTEMPTS attempts.
    Errors are generic so they do not reveal which emails exist.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError
from app.models.user import User
from app.schemas.enums import ErrorCode, UserRole

# ES: Tiempo mínimo entre dos códigos. EN: Minimum time between two codes.
RESEND_COOLDOWN = timedelta(seconds=60)
INVALID_CODE = "Código no válido o caducado. Puedes pedir uno nuevo."


def _hash_code(user: User, code: str) -> str:
    message = f"{user.id}:{code}".encode()
    return hmac.new(settings.JWT_SECRET.encode(), message, hashlib.sha256).hexdigest()


def issue_code(user: User, now: datetime | None = None) -> str:
    """ES: Genera un código nuevo (invalida el anterior). Devuelve el código en
    claro solo para enviarlo por correo; no se guarda.
    EN: Generates a new code (invalidating the previous one). Returns the plain
    code only to email it; it is not stored.
    """
    now = now or datetime.now(UTC)
    code = f"{secrets.randbelow(1_000_000):06d}"
    user.verification_code_hash = _hash_code(user, code)
    user.verification_code_expires_at = now + timedelta(
        minutes=settings.EMAIL_CODE_EXPIRE_MINUTES
    )
    user.verification_attempts = 0
    return code


def _pending_user(db: Session, email: str) -> User | None:
    """ES: Tutor sin verificar, bloqueado para contar bien los intentos.
    EN: Unverified guardian, locked so attempts are counted correctly.
    """
    return db.scalar(
        select(User)
        .where(
            User.email == email,
            User.role == UserRole.GUARDIAN,
            User.deleted_at.is_(None),
            User.is_verified.is_(False),
        )
        .with_for_update()
    )


def verify_code(db: Session, email: str, code: str) -> None:
    now = datetime.now(UTC)
    user = _pending_user(db, email)
    invalid = ApiError(400, ErrorCode.VALIDATION_ERROR, INVALID_CODE)
    if (
        user is None
        or user.verification_code_hash is None
        or user.verification_code_expires_at is None
        or user.verification_code_expires_at <= now
    ):
        raise invalid

    if not hmac.compare_digest(user.verification_code_hash, _hash_code(user, code)):
        user.verification_attempts += 1
        # ES: Demasiados intentos: el código deja de valer.
        # EN: Too many attempts: the code stops working.
        if user.verification_attempts >= settings.EMAIL_CODE_MAX_ATTEMPTS:
            user.verification_code_hash = None
        db.commit()
        raise invalid

    user.is_verified = True
    user.verification_code_hash = None
    user.verification_code_expires_at = None
    user.verification_attempts = 0
    db.commit()


def reissue_code(db: Session, email: str) -> str | None:
    """ES: Nuevo código si el Tutor existe, no está verificado y pasó el tiempo
    mínimo. None en cualquier otro caso (la API responde igual).
    EN: New code if the guardian exists, is unverified and the cooldown has
    passed. None otherwise (the API answers the same way).
    """
    now = datetime.now(UTC)
    user = _pending_user(db, email)
    if user is None:
        return None
    expires_at = user.verification_code_expires_at
    if expires_at is not None:
        issued_at = expires_at - timedelta(minutes=settings.EMAIL_CODE_EXPIRE_MINUTES)
        if now - issued_at < RESEND_COOLDOWN:
            return None
    code = issue_code(user, now)
    db.commit()
    return code
