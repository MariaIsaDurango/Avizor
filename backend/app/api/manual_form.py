"""Lectura del multipart del reenvío manual, siempre en memoria.
Reading of the manual forward multipart, always in memory.

ES: Starlette guarda en disco (archivo temporal) los archivos de más de 1 MB.
    El contrato prohíbe escribir el binario en disco, así que usamos un parser
    cuyo límite en memoria cubre el tamaño máximo del envío.
EN: Starlette writes files over 1 MB to disk (temporary file). The contract
    forbids writing the binary to disk, so we use a parser whose in-memory
    limit covers the maximum request size.
"""

from collections.abc import AsyncGenerator

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from app.core.errors import ApiError
from app.schemas.analysis import ATTACHMENT_RULES, MB, ManualAnalysisMetadata
from app.schemas.enums import ErrorCode

# ES: Un vídeo (50 MB) + margen. EN: One video (50 MB) + margin.
MAX_REQUEST_BYTES = 60 * MB
METADATA_MAX_BYTES = 64 * 1024
TOO_LARGE = "El envío supera el tamaño máximo (60 MB)."


class InMemoryMultiPartParser(MultiPartParser):
    # ES: Nunca pasa a disco. EN: Never rolls over to disk.
    spool_max_size = MAX_REQUEST_BYTES


async def _limited(request: Request) -> AsyncGenerator[bytes]:
    """ES: Corta el envío si supera el límite, aunque no traiga Content-Length.
    EN: Stops the upload if it exceeds the limit, even without Content-Length.
    """
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > MAX_REQUEST_BYTES:
            raise ApiError(413, ErrorCode.VALIDATION_ERROR, TOO_LARGE)
        yield chunk


def _invalid(detail: str) -> ApiError:
    return ApiError(422, ErrorCode.VALIDATION_ERROR, detail)


async def read_manual_form(
    request: Request,
) -> tuple[ManualAnalysisMetadata, dict[str, int]]:
    """ES: Devuelve la metadata validada y el tamaño real de cada adjunto.
    El contenido de los archivos se lee y se descarta (no se guarda).
    EN: Returns the validated metadata and the real size of each attachment.
    File contents are read and discarded (not stored).
    """
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > MAX_REQUEST_BYTES:
        raise ApiError(413, ErrorCode.VALIDATION_ERROR, TOO_LARGE)

    parser = InMemoryMultiPartParser(
        request.headers,
        _limited(request),
        max_files=5,
        max_fields=1,
        max_part_size=METADATA_MAX_BYTES,
    )
    try:
        form = await parser.parse()
    except MultiPartException:
        raise _invalid("El formulario no es válido.") from None

    try:
        raw = form.get("metadata")
        if not isinstance(raw, str):
            raise _invalid("Falta la parte metadata.")
        try:
            metadata = ManualAnalysisMetadata.model_validate_json(raw)
        except ValidationError as exc:
            raise RequestValidationError(
                [{**e, "loc": ("body", "metadata", *e["loc"])} for e in exc.errors()]
            ) from None

        uploads = [(k, v) for k, v in form.multi_items() if isinstance(v, UploadFile)]
        declared = {a.file_field: a for a in metadata.attachments}
        if len(uploads) != len(declared) or {k for k, _ in uploads} != set(declared):
            raise _invalid("Los archivos no coinciden con metadata.attachments.")

        sizes: dict[str, int] = {}
        for field, upload in uploads:
            size = len(await upload.read())
            if size > ATTACHMENT_RULES[declared[field].type]["max_bytes"]:
                raise _invalid(f"{field} supera el tamaño permitido.")
            sizes[field] = size
        return metadata, sizes
    finally:
        # ES: Libera la memoria de los archivos. EN: Frees the files' memory.
        await form.close()
