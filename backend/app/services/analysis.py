"""Vía rápida de análisis (< 800 ms): sin LLM, sin RAG.
Fast analysis path (< 800 ms): no LLM, no RAG.

ES: Guarda solo metadatos en analyses. El texto anonimizado va a temp_content
    con fecha de borrado (green 0 d, amber 7 d, red 30 d). Los teléfonos, solo
    como HMAC. En rojo se crea una alerta para cada Tutor vinculado.
EN: Stores only metadata in analyses. Anonymized text goes to temp_content
    with a deletion date (green 0 d, amber 7 d, red 30 d). Phones only as HMAC.
    On red, an alert is created for every paired guardian.
"""

import uuid
from datetime import UTC, datetime, timedelta
from functools import partial
from time import perf_counter
from typing import NamedTuple

from anyio.from_thread import run as run_on_app_loop
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError
from app.core.privacy import InvalidPhoneError, hash_indicator, public_value
from app.core.security import TokenPayload
from app.models.alert import Alert
from app.models.analysis import Analysis, TempContent
from app.models.indicator import Indicator
from app.models.user import Pairing, User
from app.schemas.analysis import AnalysisRequest
from app.schemas.enums import (
    Channel,
    ErrorCode,
    IndicatorType,
    InputType,
    Origin,
    RiskLevel,
    VerdictPhase,
)
from app.schemas.verdict import Verdict
from app.services.consent import has_active_consent
from app.services.detection.decision import AMBER_THRESHOLD, decide
from app.services.detection.ml_classifier import build_classifier
from app.services.detection.reputation import ReputationRuntime
from app.services.detection.text_rules import ThreatClassifier
from app.services.detection.url_extract import merge_urls
from app.services.detection.url_rules import domain_of
from app.services.devices import touch_device
from app.services.identity import request_device_id, senior_id_from_device

# ES: Reglas por defecto; el modelo de IA con CLASSIFIER_PROVIDER=ml (#38).
# EN: Rules by default; the AI model with CLASSIFIER_PROVIDER=ml (#38).
CLASSIFIER: ThreatClassifier = build_classifier(
    settings.CLASSIFIER_PROVIDER,
    settings.ML_MODEL_DIR,
    fraud_threshold=settings.ML_FRAUD_THRESHOLD,
    threads=settings.ML_THREADS,
)
PHONE_MODEL_VERSION = "phone-reputation-0.1"

RETENTION_DAYS = {RiskLevel.AMBER: 7, RiskLevel.RED: 30}

CHANNEL_NAMES = {
    Channel.SMS: "SMS",
    Channel.NOTIFICATION: "notificación",
    Channel.SCREEN: "un mensaje en pantalla",
    Channel.CALL: "llamada",
    Channel.MANUAL: "un mensaje reenviado",
}


def _report_count(db: Session, indicator_type: IndicatorType, value_hash: str) -> int:
    count = db.scalar(
        select(Indicator.report_count).where(
            Indicator.type == indicator_type, Indicator.value_hash == value_hash
        )
    )
    return count or 0


def record_indicator(
    db: Session, indicator_type: IndicatorType, value: str, now: datetime
) -> None:
    """ES: Suma un reporte (crea el indicador si no existe).
    EN: Adds one report (creates the indicator if it does not exist).
    """
    stmt = insert(Indicator).values(
        type=indicator_type,
        value_hash=hash_indicator(indicator_type, value),
        public_value=public_value(indicator_type, value),
        first_seen_at=now,
        last_seen_at=now,
    )
    db.execute(
        stmt.on_conflict_do_update(
            index_elements=["type", "value_hash"],
            set_={
                "report_count": Indicator.report_count + 1,
                "last_seen_at": now,
            },
        )
    )


def create_alerts(
    db: Session,
    analysis: Analysis,
    senior_id: uuid.UUID,
    explanation: str,
    evidence: list[dict],
) -> list[uuid.UUID]:
    senior_name = db.scalar(select(User.display_name).where(User.id == senior_id))
    guardian_ids = db.scalars(
        select(Pairing.guardian_id).where(
            Pairing.senior_id == senior_id,
            Pairing.active.is_(True),
            Pairing.redeemed_at.is_not(None),
        )
    ).all()
    # ES: Textos fijos con plantilla, nunca contenido del mensaje.
    # EN: Fixed template texts, never message content.
    summary = (
        f"Hemos bloqueado un intento de estafa por "
        f"{CHANNEL_NAMES[analysis.channel]} en el móvil de {senior_name}."
    )

    alerts = [
        Alert(
            analysis_id=analysis.id,
            guardian_id=guardian_id,
            summary=summary,
            explanation=explanation,
            evidence=evidence,
        )
        for guardian_id in set(guardian_ids)
    ]
    db.add_all(alerts)
    # ES: flush para que PostgreSQL asigne los ids. EN: flush so PG assigns ids.
    db.flush()
    return [alert.id for alert in alerts]


def explain(reasons: list[str]) -> str:
    """ES: Explicación para el Tutor con motivos fijos (nunca texto del mensaje).
    EN: Explanation for the guardian with fixed reasons (never message text).
    """
    return " ".join(reasons[:3]) or "Contenido peligroso detectado."


class FastResult(NamedTuple):
    """ES: Veredicto para el Sénior + alertas creadas (para el push).
    EN: Verdict for the senior + created alerts (for the push).
    """

    verdict: Verdict
    alert_ids: list[uuid.UUID]


def analyze_fast(
    db: Session,
    token: TokenPayload,
    body: AnalysisRequest,
    reputation: ReputationRuntime | None = None,
) -> FastResult:
    started = perf_counter()
    now = datetime.now(UTC)

    device_id = request_device_id(token, body.device_id)
    senior_id = senior_id_from_device(db, token.sub)

    if body.origin == Origin.AUTOMATIC and not has_active_consent(
        db, senior_id, body.channel
    ):
        raise ApiError(403, ErrorCode.CONSENT_MISSING)
    if body.content and not body.content.anonymization.applied:
        raise ApiError(422, ErrorCode.CONTENT_NOT_ANONYMIZED)
    # ES: Solo cuenta como actividad una petición válida.
    # EN: Only a valid request counts as activity.
    touch_device(db, token.sub, now)

    # ES: Remitente: solo HMAC. EN: Sender: HMAC only.
    sender_hash, sender_reports, sender_type = None, 0, None
    if body.sender:
        sender_type = IndicatorType(body.sender.type)
        try:
            sender_hash = hash_indicator(sender_type, body.sender.value)
        except InvalidPhoneError:
            raise ApiError(
                422, ErrorCode.VALIDATION_ERROR, "El número no es válido."
            ) from None
        sender_reports = _report_count(db, sender_type, sender_hash)

    # ES: También los enlaces escritos dentro del texto (#151).
    # EN: Also the links written inside the text (#151).
    urls = (
        merge_urls([str(url) for url in body.content.urls], body.content.text)
        if body.content
        else []
    )
    domains = {domain_of(url) for url in urls} - {""}
    domain_reports = max(
        (
            _report_count(
                db, IndicatorType.DOMAIN, hash_indicator(IndicatorType.DOMAIN, d)
            )
            for d in domains
        ),
        default=0,
    )

    classify = partial(
        decide,
        input_type=body.input_type,
        origin=body.origin,
        channel=body.channel,
        text=body.content.text if body.content else "",
        urls=urls,
        classifier=CLASSIFIER,
        sender_reports=sender_reports,
        domain_reports=domain_reports,
    )

    is_phone = body.input_type == InputType.PHONE_NUMBER
    # SQLAlchemy stays in this worker. Only the pure decision and IO run concurrently.
    # Phone analysis keeps the existing local HMAC route; no external phone calls.
    if reputation is not None and urls and not is_phone:
        decision = run_on_app_loop(reputation.evaluate, classify, urls, body.channel)
    else:
        decision = classify()
    analysis = Analysis(
        device_id=device_id,
        channel=body.channel,
        origin=body.origin,
        input_types=[body.input_type],
        sender_hash=sender_hash,
        received_at=body.received_at,
        risk_level=decision.risk_level,
        threat_type=decision.threat_type,
        action=decision.action,
        block_template=decision.block_template,
        confidence=decision.confidence,
        phase=VerdictPhase.FAST,
        model_version=PHONE_MODEL_VERSION if is_phone else CLASSIFIER.model_version,
        server_processed=False,
    )
    db.add(analysis)
    db.flush()

    evidence: list[dict] = []
    if decision.risk_level != RiskLevel.GREEN:
        if body.content:
            db.add(
                TempContent(
                    analysis_id=analysis.id,
                    anonymized_text=body.content.text,
                    urls=urls,
                    delete_at=now + timedelta(days=RETENTION_DAYS[decision.risk_level]),
                )
            )
        for finding in decision.url_findings:
            if finding.score >= AMBER_THRESHOLD and finding.domain:
                record_indicator(db, IndicatorType.DOMAIN, finding.domain, now)
                evidence.append(
                    {
                        "type": "domain",
                        "value": finding.domain,
                        "reason": finding.reasons[0],
                    }
                )
        for finding in decision.reputation_findings:
            evidence.append(
                {
                    "type": "domain",
                    "value": finding.domain,
                    "reason": finding.reasons[0],
                }
            )
        # An external URL match alone must not create a sender/domain report.
        if body.sender and sender_type and not decision.reputation_only:
            record_indicator(db, sender_type, body.sender.value, now)
            if sender_reports:
                evidence.append(
                    {
                        "type": sender_type.value,
                        "value": public_value(sender_type, body.sender.value),
                        "reason": f"Reportado {sender_reports} veces.",
                    }
                )

    alert_ids: list[uuid.UUID] = []
    if decision.risk_level == RiskLevel.RED:
        alert_ids = create_alerts(
            db, analysis, senior_id, explain(decision.reasons), evidence
        )
    analysis.latency_ms = round((perf_counter() - started) * 1000)
    db.commit()

    verdict = Verdict(
        analysis_id=analysis.id,
        phase=VerdictPhase.FAST,
        risk_level=decision.risk_level,
        threat_type=decision.threat_type,
        action=decision.action,
        block_template=decision.block_template,
        confidence=decision.confidence,
        final=True,
        retry_after_ms=None,
        issued_at=datetime.now(UTC),
    )
    return FastResult(verdict, alert_ids)
