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
from app.models.user import User
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

    # ES: Tutor y admin: el token debe tener la versión de sesión actual. Al
    #     cambiar la contraseña sube la versión y se cierran todas las sesiones.
    #     (El Sénior se revoca al desvincular: ver identity.senior_id_from_device.)
    # EN: Guardian and admin: the token must carry the current session version.
    #     Changing the password bumps it and closes every session.
    #     (Seniors are revoked on unlink: see identity.senior_id_from_device.)
    if token.role in (UserRole.GUARDIAN, UserRole.ADMIN):
        current = db.scalar(
            select(User.token_version).where(
                User.id == token.sub, User.deleted_at.is_(None)
            )
        )
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
AdminToken = Annotated[TokenPayload, Depends(require_role(UserRole.ADMIN))]
