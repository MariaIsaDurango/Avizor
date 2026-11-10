"""Endpoint de análisis (Contrato v1.0.0).
Analysis endpoint (Contract v1.0.0).

ES: Esta issue (#14) cubre la vía rápida en JSON. El reenvío multimodal
    (multipart, 202 + agente) llega en la #15.
EN: This issue (#14) covers the JSON fast path. The multimodal forward
    (multipart, 202 + agent) comes in #15.
"""

from fastapi import APIRouter

from app.api.deps import DbSession, SeniorToken
from app.schemas.analysis import AnalysisRequest
from app.schemas.verdict import Verdict
from app.services import analysis as analysis_service

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("")
def create_analysis(
    body: AnalysisRequest, db: DbSession, token: SeniorToken
) -> Verdict:
    """ES: Intercepción automática o consulta de número: respuesta síncrona.
    EN: Automatic interception or phone lookup: synchronous response.
    """
    return analysis_service.analyze_fast(db, token, body)
