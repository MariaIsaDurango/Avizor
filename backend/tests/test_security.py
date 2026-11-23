"""Tests de contraseñas y tokens JWT.
Tests for passwords and JWT tokens.
"""

import uuid

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    JWT_ALGORITHM,
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.schemas.enums import UserRole

USER_ID = uuid.UUID("9c8b7a6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d")


def test_password_is_hashed_not_stored_in_clear():
    password_hash = hash_password("Contraseña-segura-1")
    assert "Contraseña-segura-1" not in password_hash
    assert password_hash.startswith("$argon2")


def test_verify_password():
    password_hash = hash_password("Contraseña-segura-1")
    assert verify_password("Contraseña-segura-1", password_hash)
    assert not verify_password("otra", password_hash)


def test_verify_password_with_broken_hash_returns_false():
    assert not verify_password("x", "not-a-hash")


def test_token_round_trip():
    token = create_access_token(USER_ID, UserRole.GUARDIAN)
    payload = decode_access_token(token)
    assert payload.sub == USER_ID
    assert payload.role == UserRole.GUARDIAN


def test_expired_token_fails():
    token = create_access_token(USER_ID, UserRole.GUARDIAN, expires_minutes=-1)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_token_signed_with_other_secret_fails():
    """ES: Un token manipulado no se acepta. EN: A tampered token is rejected."""
    token = jwt.encode(
        {"sub": str(USER_ID), "role": "admin", "exp": 9999999999},
        "other-secret-0123456789-0123456789",
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_token_with_unknown_role_fails():
    token = jwt.encode(
        {"sub": str(USER_ID), "role": "superuser", "exp": 9999999999},
        settings.JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_token_without_exp_fails():
    token = jwt.encode(
        {"sub": str(USER_ID), "role": "guardian"},
        settings.JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_alg_none_is_rejected():
    """ES: Ataque clásico: token sin firma. EN: Classic attack: unsigned token."""
    token = jwt.encode(
        {"sub": str(USER_ID), "role": "admin", "exp": 9999999999},
        key=None,
        algorithm="none",
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)
