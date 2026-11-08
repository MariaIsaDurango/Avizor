"""Errores de la API en formato RFC 9457 (problem details).
API errors in RFC 9457 format (problem details).

ES: Toda la API responde los errores con el mismo formato (schema ProblemDetail).
EN: The whole API returns errors with the same format (ProblemDetail schema).
"""

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.enums import ErrorCode

logger = logging.getLogger(__name__)

ERROR_TYPE_BASE = "https://avizor.app/errors/"

# ES: Títulos en español (los ve el usuario). EN: Titles in Spanish (user-facing).
TITLES = {
    ErrorCode.VALIDATION_ERROR: "Datos no válidos",
    ErrorCode.UNAUTHENTICATED: "No autenticado",
    ErrorCode.FORBIDDEN: "Acceso denegado",
    ErrorCode.NOT_FOUND: "Recurso no encontrado",
    ErrorCode.CONSENT_MISSING: "Falta el consentimiento del usuario sénior",
    ErrorCode.PAIRING_EXPIRED: "El código de vinculación ha caducado",
    ErrorCode.CONTENT_NOT_ANONYMIZED: "El contenido no está anonimizado",
    ErrorCode.RATE_LIMITED: "Demasiadas peticiones",
    ErrorCode.INTERNAL_ERROR: "Error interno del servidor",
}

STATUS_TO_CODE = {
    401: ErrorCode.UNAUTHENTICATED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMITED,
}


class ApiError(Exception):
    """ES: Lánzala desde cualquier endpoint: raise ApiError(403, ErrorCode.FORBIDDEN).
    EN: Raise it from any endpoint: raise ApiError(403, ErrorCode.FORBIDDEN).
    """

    def __init__(self, status: int, code: ErrorCode, detail: str = "") -> None:
        self.status = status
        self.code = code
        self.detail = detail or TITLES[code]
        super().__init__(self.detail)


def problem_response(status: int, code: ErrorCode, detail: str) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        headers=headers,
        content={
            "type": ERROR_TYPE_BASE + code.value.lower().replace("_", "-"),
            "title": TITLES[code],
            "status": status,
            "code": code.value,
            "detail": detail,
            "trace_id": str(uuid.uuid4()),
        },
    )


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return problem_response(exc.status, exc.code, exc.detail)


async def http_error_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code = STATUS_TO_CODE.get(exc.status_code, ErrorCode.VALIDATION_ERROR)
    if exc.status_code >= 500:
        code = ErrorCode.INTERNAL_ERROR
    # ES: Starlette pone textos en inglés ("Not Found"); usamos el título en español.
    # EN: Starlette uses English texts ("Not Found"); we use the Spanish title.
    detail = exc.detail if exc.detail not in (None, "Not Found") else TITLES[code]
    return problem_response(exc.status_code, code, str(detail))


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # ES: Solo el nombre de los campos, nunca los valores (pueden ser datos personales).
    # EN: Field names only, never the values (they may be personal data).
    fields = sorted({".".join(str(p) for p in e["loc"][1:]) for e in exc.errors()})
    detail = "Revisa estos campos: " + ", ".join(f for f in fields if f)
    return problem_response(422, ErrorCode.VALIDATION_ERROR, detail)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url.path)
    return problem_response(
        500, ErrorCode.INTERNAL_ERROR, "Ha ocurrido un error inesperado."
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
