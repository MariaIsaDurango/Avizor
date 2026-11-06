"""Formato único de error de la API (RFC 9457, problem details).
Single API error format (RFC 9457, problem details).

ES: title y detail van en español (los ve el usuario).
EN: title and detail are in Spanish (shown to the user).
"""

from uuid import UUID

from pydantic import Field, HttpUrl

from app.schemas.common import ContractModel
from app.schemas.enums import ErrorCode


class ProblemDetail(ContractModel):
    type: HttpUrl
    title: str = Field(min_length=1)
    status: int = Field(ge=400, le=599)
    code: ErrorCode
    detail: str
    trace_id: UUID
