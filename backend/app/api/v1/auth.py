"""Endpoints de registro e inicio de sesión del Tutor.
Guardian sign-up and login endpoints.
"""

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentToken, DbSession
from app.core.config import settings
from app.core.errors import ApiError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import GuardianRegister, LoginRequest, TokenResponse, UserRead
from app.schemas.enums import ErrorCode, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])

# ES: Hash falso para que el login tarde lo mismo exista o no el email
#     (evita descubrir emails registrados midiendo el tiempo).
# EN: Dummy hash so login takes the same time whether the email exists or not
#     (prevents discovering registered emails by timing).
_DUMMY_HASH = hash_password("dummy-password-for-timing")

LOGIN_ROLES = {UserRole.GUARDIAN, UserRole.ADMIN}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_guardian(body: GuardianRegister, db: DbSession) -> UserRead:
    # ES: Mensaje genérico: no confirma si el email ya existe.
    # EN: Generic message: does not confirm whether the email exists.
    duplicated = ApiError(
        409, ErrorCode.VALIDATION_ERROR, "No se ha podido completar el registro."
    )
    if db.scalar(select(User.id).where(User.email == body.email)):
        raise duplicated
    user = User(
        role=UserRole.GUARDIAN,
        display_name=body.display_name,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # ES: Dos registros a la vez con el mismo email. EN: Two concurrent sign-ups.
        db.rollback()
        raise duplicated from None
    return UserRead.model_validate(user, from_attributes=True)


@router.post("/login")
def login(body: LoginRequest, db: DbSession) -> TokenResponse:
    user = db.scalar(
        select(User).where(User.email == body.email, User.deleted_at.is_(None))
    )
    password_hash = user.password_hash if user and user.password_hash else _DUMMY_HASH
    password_ok = verify_password(body.password, password_hash)

    # ES: Mismo mensaje para email o contraseña incorrectos.
    # EN: Same message for wrong email or wrong password.
    if not user or not password_ok or user.role not in LOGIN_ROLES:
        raise ApiError(
            401, ErrorCode.UNAUTHENTICATED, "Email o contraseña incorrectos."
        )

    token = create_access_token(user.id, user.role)
    return TokenResponse(
        access_token=token, expires_in=settings.JWT_EXPIRE_MINUTES * 60
    )


@router.get("/me")
def read_me(token: CurrentToken, db: DbSession) -> UserRead:
    user = db.get(User, token.sub)
    if user is None or user.deleted_at is not None:
        raise ApiError(401, ErrorCode.UNAUTHENTICATED, "Usuario no encontrado.")
    return UserRead.model_validate(user, from_attributes=True)
