"""Endpoints de registro e inicio de sesión del Tutor.
Guardian sign-up and login endpoints.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentToken, DbSession, GuardianToken
from app.core.config import settings
from app.core.email import send_password_reset_email, send_verification_email
from app.core.errors import ApiError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    GuardianRegister,
    LoginRequest,
    MessageResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdateMeRequest,
    UserRead,
    VerifyEmailRequest,
)
from app.schemas.enums import ErrorCode, UserRole
from app.services import email_verification, password_reset

router = APIRouter(prefix="/auth", tags=["auth"])

# ES: Hash falso para que el login tarde lo mismo exista o no el email
#     (evita descubrir emails registrados midiendo el tiempo).
# EN: Dummy hash so login takes the same time whether the email exists or not
#     (prevents discovering registered emails by timing).
_DUMMY_HASH = hash_password("dummy-password-for-timing")

LOGIN_ROLES = {UserRole.GUARDIAN, UserRole.ADMIN}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_guardian(
    body: GuardianRegister, db: DbSession, background_tasks: BackgroundTasks
) -> UserRead:
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
        db.flush()
        # ES: El código va por correo; aquí solo se guarda su HMAC.
        # EN: The code goes by email; only its HMAC is stored here.
        code = email_verification.issue_code(user)
        db.commit()
    except IntegrityError:
        # ES: Dos registros a la vez con el mismo email. EN: Two concurrent sign-ups.
        db.rollback()
        raise duplicated from None
    # ES: El correo sale después de responder (no hace esperar a la app).
    # EN: The email goes out after replying (the app does not wait for it).
    background_tasks.add_task(send_verification_email, user.email, code)
    return UserRead.model_validate(user, from_attributes=True)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
def verify_email(body: VerifyEmailRequest, db: DbSession):
    """ES: Marca el email como verificado si el código es correcto.
    EN: Marks the email as verified if the code is correct.
    """
    email_verification.verify_code(db, body.email, body.code)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
def resend_verification(
    body: ResendVerificationRequest, db: DbSession, background_tasks: BackgroundTasks
) -> MessageResponse:
    """ES: Siempre responde lo mismo, exista o no la cuenta.
    EN: Always answers the same, whether the account exists or not.
    """
    code = email_verification.reissue_code(db, body.email)
    if code:
        background_tasks.add_task(send_verification_email, body.email, code)
    return MessageResponse(
        message="Si la cuenta existe y no está verificada, recibirás un código nuevo."
    )


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    body: ForgotPasswordRequest, db: DbSession, background_tasks: BackgroundTasks
) -> MessageResponse:
    """ES: Siempre responde lo mismo, exista o no la cuenta.
    EN: Always answers the same, whether the account exists or not.
    """
    link = password_reset.request_reset(db, body.email)
    if link:
        background_tasks.add_task(send_password_reset_email, body.email, link)
    return MessageResponse(
        message="Si la cuenta existe, recibirás un correo para cambiar la contraseña."
    )


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(body: ResetPasswordRequest, db: DbSession):
    """ES: Cambia la contraseña con el enlace del correo (un solo uso).
    EN: Changes the password with the emailed link (single use).
    """
    password_reset.reset_password(db, body.token, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    # ES: Solo se dice tras comprobar la contraseña (no revela cuentas a terceros).
    # EN: Only said after checking the password (reveals no accounts to others).
    if not user.is_verified:
        raise ApiError(
            403,
            ErrorCode.FORBIDDEN,
            "Verifica tu email con el código que te enviamos antes de iniciar sesión.",
        )

    token = create_access_token(user.id, user.role, token_version=user.token_version)
    return TokenResponse(
        access_token=token, expires_in=settings.JWT_EXPIRE_MINUTES * 60
    )


@router.get("/me")
def read_me(token: CurrentToken, db: DbSession) -> UserRead:
    user = db.get(User, token.sub)
    if user is None or user.deleted_at is not None:
        raise ApiError(401, ErrorCode.UNAUTHENTICATED, "Usuario no encontrado.")
    return UserRead.model_validate(user, from_attributes=True)


def _active_guardian(db: DbSession, guardian_id: uuid.UUID) -> User:
    user = db.get(User, guardian_id)
    if user is None or user.deleted_at is not None:
        raise ApiError(401, ErrorCode.UNAUTHENTICATED, "Usuario no encontrado.")
    return user


@router.patch("/me")
def update_me(body: UpdateMeRequest, token: GuardianToken, db: DbSession) -> UserRead:
    """ES: El Tutor cambia su nombre y/o teléfono.
    EN: The guardian updates their name and/or phone.
    """
    user = _active_guardian(db, token.sub)
    user.display_name = body.display_name
    if "phone" in body.model_fields_set:
        user.phone = body.phone
    db.commit()
    return UserRead.model_validate(user, from_attributes=True)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: ChangePasswordRequest, token: GuardianToken, db: DbSession):
    """ES: Cambia la contraseña comprobando antes la actual. Al cambiarla se
    cierran todas las sesiones (token_version) y los enlaces de recuperación
    pendientes dejan de valer (ver password_reset).
    EN: Changes the password after checking the current one. Once changed,
    every session is closed (token_version) and pending reset links stop
    working (see password_reset).
    """
    user = _active_guardian(db, token.sub)
    if not user.password_hash or not verify_password(
        body.current_password, user.password_hash
    ):
        raise ApiError(
            400, ErrorCode.VALIDATION_ERROR, "La contraseña actual no es correcta."
        )
    if body.new_password == body.current_password:
        raise ApiError(
            400,
            ErrorCode.VALIDATION_ERROR,
            "La nueva contraseña debe ser distinta de la actual.",
        )
    user.password_hash = hash_password(body.new_password)
    # ES: Cierra todas las sesiones, también la actual: la app vuelve al login.
    # EN: Closes every session, including this one: the app returns to login.
    user.token_version += 1
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
