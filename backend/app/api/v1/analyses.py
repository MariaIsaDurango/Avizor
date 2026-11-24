"""Endpoints de análisis (Contrato v1.0.0).
Analysis endpoints (Contract v1.0.0).

POST /api/v1/analyses
  - application/json     → vía rápida / fast path: 200 + Verdict (#14)
  - multipart/form-data  → reenvío manual / manual forward: 202 (#15)
GET  /api/v1/analyses/{id}/verdict
  → 202 mientras el agente trabaja / while the agent works; luego / then 200
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.deps import DbSession, DeviceToken
from app.api.manual_form import read_manual_form
from app.schemas.analysis import AnalysisRequest
from app.schemas.verdict import AnalysisAccepted, Verdict
from app.services import analysis as analysis_service
from app.services import manual_analysis as manual_service
from app.services import push as push_service

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _inline_refs(schema: dict, defs: dict | None = None) -> dict:
    """ES: Copia los $defs dentro del schema para documentarlo en OpenAPI.
    EN: Copies $defs into the schema so it can be documented in OpenAPI.
    """
    defs = schema.get("$defs", {}) if defs is None else defs
    if isinstance(schema, dict):
        if "$ref" in schema:
            return _inline_refs(defs[schema["$ref"].split("/")[-1]], defs)
        return {k: _inline_refs(v, defs) for k, v in schema.items() if k != "$defs"}
    if isinstance(schema, list):
        return [_inline_refs(item, defs) for item in schema]
    return schema


# ES: Al leer el body a mano, FastAPI no lo documenta solo: lo describimos aquí.
# EN: Since the body is read by hand, FastAPI does not document it: done here.
REQUEST_BODY = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": _inline_refs(AnalysisRequest.model_json_schema())
            },
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["metadata"],
                    "properties": {
                        "metadata": {
                            "type": "string",
                            "description": "ManualAnalysisMetadata (JSON)",
                        },
                        **{
                            f"attachment_{i}": {"type": "string", "format": "binary"}
                            for i in range(5)
                        },
                    },
                }
            },
        },
    }
}


def _accepted(body: AnalysisAccepted) -> JSONResponse:
    return JSONResponse(status_code=202, content=body.model_dump(mode="json"))


@router.post(
    "",
    response_model=Verdict,
    responses={202: {"model": AnalysisAccepted}},
    openapi_extra=REQUEST_BODY,
)
async def create_analysis(
    request: Request,
    db: DbSession,
    token: DeviceToken,
    background_tasks: BackgroundTasks,
):
    """ES: JSON: respuesta síncrona (< 800 ms). Multipart: 202 y el agente
    trabaja en segundo plano.
    EN: JSON: synchronous response (< 800 ms). Multipart: 202 and the agent
    works in the background.
    """
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        metadata, sizes = await read_manual_form(request)
        job = await run_in_threadpool(
            manual_service.start_manual_analysis, db, token, metadata, sizes
        )
        background_tasks.add_task(manual_service.run_manual_job, job)
        return _accepted(
            AnalysisAccepted(
                analysis_id=job.analysis_id,
                retry_after_ms=manual_service.RETRY_AFTER_MS,
            )
        )

    try:
        body = AnalysisRequest.model_validate_json(await request.body())
    except ValidationError as exc:
        raise RequestValidationError(
            [{**e, "loc": ("body", *e["loc"])} for e in exc.errors()]
        ) from None

    result = await run_in_threadpool(
        analysis_service.analyze_fast,
        db,
        token,
        body,
        getattr(request.app.state, "reputation", None),
    )
    if result.alert_ids:
        # ES: El push sale después de responder: no suma latencia (< 800 ms).
        # EN: The push goes out after replying: adds no latency (< 800 ms).
        background_tasks.add_task(push_service.send_alert_pushes_job, result.alert_ids)
    return result.verdict


@router.get(
    "/{analysis_id}/verdict",
    response_model=Verdict,
    responses={202: {"model": AnalysisAccepted}},
)
def get_verdict(
    analysis_id: uuid.UUID,
    db: DbSession,
    token: DeviceToken,
    background_tasks: BackgroundTasks,
):
    """ES: La app consulta cada retry_after_ms hasta recibir el 200.
    EN: The app polls every retry_after_ms until it gets the 200.
    """
    result = manual_service.get_verdict(db, token, analysis_id)
    if result.alert_ids:
        background_tasks.add_task(push_service.send_alert_pushes_job, result.alert_ids)
    if isinstance(result.response, AnalysisAccepted):
        return _accepted(result.response)
    return result.response
