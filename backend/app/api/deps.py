"""Dependencias de autenticación, permisos por rol y base de datos.
Authentication, role-based permission and database dependencies.

ES: Uso en un endpoint / EN: Usage in an endpoint:
    def endpoint(db: DbSession, token: GuardianToken): ...
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import InvalidTokenError, TokenPayload, decode_access_token
from app.db.session import get_db
from app.models.user import Device, User
from app.schemas.enums import ErrorCode, UserRole

# ES: auto_error=False para devolver nuestro error del contrato, no el de FastAPI.
# EN: auto_error=False to return our contract error, not FastAPI's.
bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> TokenPayload:
    if credentials is None:
        raise ApiError(401, ErrorCode.UNAUTHENTICATED, "Falta el token de acceso.")
    try:
        token = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise ApiError(
            401, ErrorCode.UNAUTHENTICATED, "Token no válido o caducado."
        ) from None

    # ES: Tutor, admin y senior_solo (#174, tiene contraseña): el token debe tener
    #     la versión de sesión actual. Al cambiar la contraseña sube la versión y
    #     se cierran todas las sesiones. El token del senior_solo lleva su
    #     dispositivo, así que el usuario se busca a través de él.
    #     (El Sénior se revoca al desvincular: ver identity.senior_id_from_device.)
    # EN: Guardian, admin and senior_solo (#174, has a password): the token must
    #     carry the current session version. Changing the password bumps it and
    #     closes every session. The senior_solo token carries its device, so the
    #     user is found through it.
    #     (Seniors are revoked on unlink: see identity.senior_id_from_device.)
    if token.role in (UserRole.GUARDIAN, UserRole.ADMIN, UserRole.SENIOR_SOLO):
        query = select(User.token_version).where(User.deleted_at.is_(None))
        if token.role == UserRole.SENIOR_SOLO:
            query = query.join(Device, Device.user_id == User.id).where(
                Device.id == token.sub
            )
        else:
            query = query.where(User.id == token.sub)
        current = db.scalar(query)
        if current is None or current != token.tv:
            raise ApiError(
                401,
                ErrorCode.UNAUTHENTICATED,
                "Tu sesión ha caducado. Vuelve a iniciar sesión.",
            )
    return token


CurrentToken = Annotated[TokenPayload, Depends(get_current_token)]


def require_role(*roles: UserRole) -> Callable[..., TokenPayload]:
    """ES: Solo deja pasar a los roles indicados (403 si no).
    EN: Only lets the given roles through (403 otherwise).
    """

    def checker(token: CurrentToken) -> TokenPayload:
        if token.role not in roles:
            raise ApiError(403, ErrorCode.FORBIDDEN, "No tienes permiso para esto.")
        return token

    return checker


# ES: Atajos para los endpoints. EN: Shortcuts for endpoints.
GuardianToken = Annotated[TokenPayload, Depends(require_role(UserRole.GUARDIAN))]
SeniorToken = Annotated[TokenPayload, Depends(require_role(UserRole.SENIOR))]
# ES: Token con dispositivo: Sénior vinculado o Sénior sin Tutor (#174).
# EN: Device token: paired senior or senior without a guardian (#174).
DeviceToken = Annotated[
    TokenPayload, Depends(require_role(UserRole.SENIOR, UserRole.SENIOR_SOLO))
]
SeniorSoloToken = Annotated[TokenPayload, Depends(require_role(UserRole.SENIOR_SOLO))]
AdminToken = Annotated[TokenPayload, Depends(require_role(UserRole.ADMIN))]
