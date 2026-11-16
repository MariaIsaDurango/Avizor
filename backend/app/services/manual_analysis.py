"""Reenvío manual multimodal: respuesta 202 + agente en segundo plano.
Multimodal manual forward: 202 response + background agent.

ES: 1. start: guarda el análisis con un veredicto provisional (final=false)
       y metadatos de los adjuntos. El binario nunca se guarda.
    2. finish (segundo plano): el agente decide; si falla, vale la vía rápida.
    3. get_verdict: 202 mientras no es final; 200 con el Verdict al terminar.
    El texto anonimizado viaja en memoria hasta el agente; solo se guarda en
    temp_content si el resultado final es amber o red.
EN: 1. start: stores the analysis with a provisional verdict (final=false)
       and attachment metadata. The binary is never stored.
    2. finish (background): the agent decides; if it fails, the fast path wins.
    3. get_verdict: 202 while not final; 200 with the Verdict when done.
    Anonymized text travels in memory to the agent; it is only stored in
    temp_content if the final result is amber or red.
"""

import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import TokenPayload
from app.db.session import SessionLocal
from app.models.analysis import Analysis, AnalysisAttachment, TempContent
from app.schemas.agent import AgentInput
from app.schemas.analysis import Attachment, ManualAnalysisMetadata
from app.schemas.enums import (
    Action,
    BlockTemplate,
    Channel,
    ErrorCode,
    IndicatorType,
    InputType,
    Origin,
    RiskLevel,
    ThreatType,
    VerdictPhase,
)
from app.schemas.verdict import AnalysisAccepted, Verdict
from app.services import push as push_service
from app.services.agent import get_agent, run_agent
from app.services.analysis import (
    CLASSIFIER,
    RETENTION_DAYS,
    create_alerts,
    explain,
    record_indicator,
)
from app.services.detection.decision import FastDecision, decide
from app.services.identity import senior_id_from_device

logger = logging.getLogger(__name__)

RETRY_AFTER_MS = 2000
# ES: Si el agente no termina en este tiempo, vale la vía rápida.
# EN: If the agent does not finish in this time, the fast path wins.
AGENT_TIMEOUT = timedelta(seconds=60)
# ES: OCR/Whisper en servidor: decisión abierta (#7). De momento no se extrae
#     nada, así que ningún dato sin anonimizar llega al agente.
# EN: Server OCR/Whisper: open decision (#7). For now nothing is extracted,
#     so no non-anonymized data reaches the agent.
SERVER_EXTRACTION_ENGINE = "server-extraction-pending"

ACTION_BY_LEVEL = {
    RiskLevel.GREEN: Action.ALLOW,
    RiskLevel.AMBER: Action.SILENT_BLOCK,
    RiskLevel.RED: Action.BLOCK_AND_ALERT,
}
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


class ManualJob(NamedTuple):
    """ES: Lo que necesita el agente. Solo vive en memoria.
    EN: What the agent needs. It only lives in memory.
    """

    analysis_id: uuid.UUID
    text: str
    urls: list[str]


class VerdictResult(NamedTuple):
    response: Verdict | AnalysisAccepted
    alert_ids: list[uuid.UUID]


def extract_urls(text: str) -> list[str]:
    found = [url.rstrip(".,;:!?)") for url in URL_PATTERN.findall(text)]
    return list(dict.fromkeys(found))[:10]


def _fast_decision(text: str, urls: list[str]) -> FastDecision:
    return decide(
        input_type=InputType.TEXT,
        origin=Origin.MANUAL,
        channel=Channel.MANUAL,
        text=text,
        urls=urls,
        classifier=CLASSIFIER,
    )


def _attachment_text(attachment: Attachment) -> tuple[str, str, str]:
    """ES: Devuelve (texto, motor de extracción, dónde se aplicó el NER).
    EN: Returns (text, extraction engine, where NER was applied).
    """
    local = attachment.local_preprocessing
    if local is None:
        return "", SERVER_EXTRACTION_ENGINE, "server"
    if not local.ner_applied:
        raise ApiError(422, ErrorCode.CONTENT_NOT_ANONYMIZED)
    return local.extracted_text, "device-ocr" if local.ocr else "device", "device"


def start_manual_analysis(
    db: Session,
    token: TokenPayload,
    metadata: ManualAnalysisMetadata,
    sizes: dict[str, int],
) -> ManualJob:
    if metadata.device_id != token.sub:
        raise ApiError(403, ErrorCode.FORBIDDEN, "El dispositivo no coincide.")
    senior_id_from_device(db, token.sub)
    if not metadata.anonymization.applied:
        raise ApiError(422, ErrorCode.CONTENT_NOT_ANONYMIZED)

    texts = [metadata.text] if metadata.text else []
    rows = []
    for attachment in metadata.attachments:
        text, engine, ner_applied_on = _attachment_text(attachment)
        if text:
            texts.append(text)
        rows.append(
            AnalysisAttachment(
                type=attachment.type,
                mime=attachment.mime,
                size_bytes=sizes[attachment.file_field],
                duration_s=attachment.duration_s,
                local_preprocessing=attachment.local_preprocessing is not None,
                extraction_engine=engine,
                ner_applied_on=ner_applied_on,
            )
        )

    text = "\n\n".join(texts)
    urls = extract_urls(text)
    fast = _fast_decision(text, urls)
    input_types = [InputType.TEXT] if metadata.text else []
    input_types += list(dict.fromkeys(a.type for a in metadata.attachments))

    analysis = Analysis(
        device_id=metadata.device_id,
        channel=Channel.MANUAL,
        origin=Origin.MANUAL,
        input_types=input_types,
        received_at=metadata.received_at,
        risk_level=fast.risk_level,
        threat_type=fast.threat_type,
        action=fast.action,
        block_template=fast.block_template,
        confidence=fast.confidence,
        phase=VerdictPhase.FAST,
        model_version=CLASSIFIER.model_version,
        server_processed=any(r.ner_applied_on == "server" for r in rows),
        final=False,
    )
    db.add(analysis)
    db.flush()
    for row in rows:
        row.analysis_id = analysis.id
    db.add_all(rows)
    db.commit()
    return ManualJob(analysis.id, text, urls)


def _complete(
    db: Session,
    analysis: Analysis,
    *,
    risk_level: RiskLevel,
    threat_type: ThreatType,
    block_template: BlockTemplate,
    confidence: float,
    phase: VerdictPhase,
    model_version: str,
    explanation: str,
    evidence: list[dict],
    text: str,
) -> list[uuid.UUID]:
    """ES: Marca el análisis como final y crea texto temporal, indicadores y
    alertas. EN: Marks the analysis final and creates temp text, indicators
    and alerts.
    """
    now = datetime.now(UTC)
    analysis.risk_level = risk_level
    analysis.threat_type = threat_type
    analysis.action = ACTION_BY_LEVEL[risk_level]
    analysis.block_template = block_template
    analysis.confidence = confidence
    analysis.phase = phase
    analysis.model_version = model_version
    analysis.final = True

    alert_ids: list[uuid.UUID] = []
    if risk_level != RiskLevel.GREEN:
        if text:
            db.add(
                TempContent(
                    analysis_id=analysis.id,
                    anonymized_text=text,
                    urls=extract_urls(text),
                    delete_at=now + timedelta(days=RETENTION_DAYS[risk_level]),
                )
            )

        # ES: Solo dominios: el reenvío manual no trae remitente (sin campo sender).
        # EN: Domains only: a manual forward has no sender (no sender field).
        for item in evidence:
            if item.get("type") == IndicatorType.DOMAIN:
                record_indicator(db, IndicatorType.DOMAIN, item["value"], now)
    if risk_level == RiskLevel.RED:
        senior_id = senior_id_from_device(db, analysis.device_id)
        alert_ids = create_alerts(db, analysis, senior_id, explanation, evidence)
    db.commit()
    return alert_ids


def _locked_pending(db: Session, analysis_id: uuid.UUID) -> Analysis | None:
    """ES: Bloquea la fila: el agente y el sondeo no pueden cerrarla dos veces.
    EN: Locks the row: the agent and polling cannot finish it twice.
    """
    analysis = db.scalar(
        select(Analysis).where(Analysis.id == analysis_id).with_for_update()
    )
    return analysis if analysis is not None and not analysis.final else None


def finish_manual_analysis(db: Session, job: ManualJob) -> list[uuid.UUID]:
    analysis = _locked_pending(db, job.analysis_id)
    if analysis is None:
        return []

    fast = _fast_decision(job.text, job.urls)
    agent = get_agent(fast)
    output = run_agent(
        agent,
        AgentInput(
            text=job.text,
            urls=job.urls,
            fast_risk_level=fast.risk_level,
            fast_threat_type=fast.threat_type,
        ),
    )
    if output is None:
        # ES: Salida no válida: decisión de la vía rápida (contrato).
        # EN: Invalid output: fast path decision (contract).
        return _complete(
            db,
            analysis,
            risk_level=fast.risk_level,
            threat_type=fast.threat_type,
            block_template=fast.block_template or BlockTemplate.UNSURE_CALL_FAMILY,
            confidence=fast.confidence,
            phase=VerdictPhase.FAST,
            model_version=CLASSIFIER.model_version,
            explanation=explain(fast.reasons),
            evidence=[
                {"type": "domain", "value": f.domain, "reason": f.reasons[0]}
                for f in fast.url_findings
                if f.domain and f.reasons
            ],
            text=job.text,
        )
    return _complete(
        db,
        analysis,
        risk_level=output.risk_level,
        threat_type=output.threat_type,
        block_template=output.block_template,
        confidence=output.confidence,
        phase=VerdictPhase.AGENT,
        model_version=agent.model_version,
        explanation=output.explanation,
        evidence=[item.model_dump(mode="json") for item in output.evidence],
        text=job.text,
    )


def run_manual_job(job: ManualJob) -> None:
    """ES: Tarea en segundo plano, con su propia sesión.
    EN: Background task, with its own session.
    """
    try:
        with SessionLocal() as db:
            alert_ids = finish_manual_analysis(db, job)
        if alert_ids:
            push_service.send_alert_pushes_job(alert_ids)
    except Exception:
        logger.exception("Manual analysis failed for %s", job.analysis_id)


def _expire(db: Session, analysis_id: uuid.UUID) -> list[uuid.UUID]:
    """ES: El agente no terminó a tiempo: se cierra con la vía rápida guardada.
    EN: The agent did not finish in time: closed with the stored fast path.
    """
    analysis = _locked_pending(db, analysis_id)
    if analysis is None:
        return []
    return _complete(
        db,
        analysis,
        risk_level=analysis.risk_level,
        threat_type=analysis.threat_type,
        block_template=BlockTemplate(
            analysis.block_template or BlockTemplate.UNSURE_CALL_FAMILY
        ),
        confidence=float(analysis.confidence or 0),
        phase=VerdictPhase.FAST,
        model_version=analysis.model_version,
        explanation="Contenido peligroso detectado.",
        evidence=[],
        text="",
    )


def get_verdict(
    db: Session, token: TokenPayload, analysis_id: uuid.UUID
) -> VerdictResult:
    analysis = db.scalar(
        select(Analysis).where(
            Analysis.id == analysis_id, Analysis.device_id == token.sub
        )
    )
    # ES: 404 también si es de otro dispositivo. EN: 404 also for other devices.
    if analysis is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "Análisis no encontrado.")

    alert_ids: list[uuid.UUID] = []
    if not analysis.final:
        if analysis.created_at > datetime.now(UTC) - AGENT_TIMEOUT:
            return VerdictResult(
                AnalysisAccepted(
                    analysis_id=analysis.id, retry_after_ms=RETRY_AFTER_MS
                ),
                [],
            )
        alert_ids = _expire(db, analysis.id)
        db.refresh(analysis)

    verdict = Verdict(
        analysis_id=analysis.id,
        phase=analysis.phase,
        risk_level=analysis.risk_level,
        threat_type=analysis.threat_type,
        action=analysis.action,
        block_template=analysis.block_template,
        confidence=float(analysis.confidence or 0),
        final=True,
        retry_after_ms=None,
        issued_at=datetime.now(UTC),
    )
    return VerdictResult(verdict, alert_ids)
