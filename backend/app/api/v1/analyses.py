"""Endpoint de análisis (Contrato v1.0.0).
Analysis endpoint (Contract v1.0.0).

ES: Esta issue (#14) cubre la vía rápida en JSON. El reenvío multimodal
    (multipart, 202 + agente) llega en la #15.
EN: This issue (#14) covers the JSON fast path. The multimodal forward
    (multipart, 202 + agent) comes in #15.
"""

from fastapi import APIRouter, BackgroundTasks

from app.api.deps import DbSession, SeniorToken
from app.schemas.analysis import AnalysisRequest
from app.schemas.verdict import Verdict
from app.services import analysis as analysis_service
from app.services import push as push_service

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("")
def create_analysis(
    body: AnalysisRequest,
    db: DbSession,
    token: SeniorToken,
    background_tasks: BackgroundTasks,
) -> Verdict:
    """ES: Intercepción automática o consulta de número: respuesta síncrona.
    EN: Automatic interception or phone lookup: synchronous response.
    """
    result = analysis_service.analyze_fast(db, token, body)
    if result.alert_ids:
        # ES: El push sale después de responder: no suma latencia (< 800 ms).
        # EN: The push goes out after replying: adds no latency (< 800 ms).
        background_tasks.add_task(push_service.send_alert_pushes_job, result.alert_ids)
    return result.verdict
