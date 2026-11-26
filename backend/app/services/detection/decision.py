"""Decisión de la vía rápida: semáforo, acción y plantilla.
Fast path decision: traffic light, action and template.

ES: Combina clasificador + señales de enlaces + reputación. Sin LLM ni RAG.
    El texto de la pantalla del Sénior es SIEMPRE una plantilla fija.
EN: Combines classifier + link signals + reputation. No LLM or RAG.
    The senior's screen text is ALWAYS a fixed template.
"""

from dataclasses import dataclass, field, replace

from app.schemas.enums import (
    Action,
    BlockTemplate,
    Channel,
    InputType,
    Origin,
    RiskLevel,
    ThreatType,
)
from app.services.detection.text_rules import ClassifierResult, ThreatClassifier
from app.services.detection.url_rules import UrlFinding, analyze_url

RED_THRESHOLD = 0.7
AMBER_THRESHOLD = 0.4
# ES: Reportes previos para considerar un indicador peligroso / sospechoso.
# EN: Prior reports to treat an indicator as dangerous / suspicious.
REPORTS_RED = 5
REPORTS_AMBER = 1
# ES: Rango 400 (desde el 17/10/2026): única numeración permitida para llamadas
#     comerciales en España (Ley de Servicios de Atención a la Clientela). Es
#     publicidad legal, no estafa: ámbar como spam, nunca rojo por sí solo.
# EN: 400 range (since 2026-10-17): the only numbering allowed for commercial
#     calls in Spain. Legal advertising, not fraud: amber spam, never red alone.
COMMERCIAL_PREFIX = "+34400"
COMMERCIAL_SCORE = 0.5


def is_commercial_number(e164: str | None) -> bool:
    """ES: +34 400 XXX XXX (9 cifras). EN: +34 400 XXX XXX (9 digits)."""
    return bool(e164) and e164.startswith(COMMERCIAL_PREFIX) and len(e164) == 12


@dataclass(frozen=True)
class FastDecision:
    risk_level: RiskLevel
    threat_type: ThreatType
    action: Action
    block_template: BlockTemplate | None
    confidence: float
    reasons: list[str] = field(default_factory=list)
    url_findings: list[UrlFinding] = field(default_factory=list)
    reputation_findings: list[UrlFinding] = field(default_factory=list)
    reputation_only: bool = False


def _level(score: float) -> RiskLevel:
    if score >= RED_THRESHOLD:
        return RiskLevel.RED
    if score >= AMBER_THRESHOLD:
        return RiskLevel.AMBER
    return RiskLevel.GREEN


def _reputation_score(reports: int) -> float:
    if reports >= REPORTS_RED:
        return 1.0
    if reports >= REPORTS_AMBER:
        return 0.5
    return 0.0


def decide_phone(
    origin: Origin, sender_reports: int, sender_phone: str | None = None
) -> FastDecision:
    """ES: Vishing: solo se mira el número, nunca la conversación.
    EN: Vishing: only the number is checked, never the conversation.
    """
    commercial = is_commercial_number(sender_phone)
    score = max(
        _reputation_score(sender_reports), COMMERCIAL_SCORE if commercial else 0.0
    )
    level = _level(score)
    reasons = (
        [f"Este número ya ha sido reportado {sender_reports} veces."]
        if sender_reports
        else []
    )
    if commercial:
        reasons.append("Es un número 400: solo se usa para llamadas comerciales.")
    if commercial and level == RiskLevel.AMBER:
        # ES: Regla fija, sin modelo ni API: seguro de que es publicidad.
        # EN: Fixed rule, no model or API: certain it is advertising.
        return FastDecision(
            level,
            ThreatType.SPAM,
            Action.ALLOW,
            BlockTemplate.SUSPICIOUS_CALL,
            0.95,
            reasons,
        )
    if level == RiskLevel.RED:
        return FastDecision(
            level,
            ThreatType.VISHING,
            Action.BLOCK_AND_ALERT,
            BlockTemplate.SUSPICIOUS_CALL,
            0.95,
            reasons,
        )
    if level == RiskLevel.AMBER:
        return FastDecision(
            level,
            ThreatType.VISHING,
            Action.ALLOW,
            BlockTemplate.SUSPICIOUS_CALL,
            0.6,
            reasons,
        )
    # ES: Sin reportes no decimos "es seguro": pedimos llamar al familiar si hay dudas.
    # EN: No reports does not mean "safe": ask to call family if in doubt.
    template = BlockTemplate.UNSURE_CALL_FAMILY if origin == Origin.MANUAL else None
    return FastDecision(level, ThreatType.NONE, Action.ALLOW, template, 0.5, reasons)


def _template_for(
    level: RiskLevel, result: ClassifierResult, has_bad_url: bool
) -> BlockTemplate | None:
    if level == RiskLevel.GREEN:
        return None
    if result.asks_bank_details:
        return BlockTemplate.ASKS_BANK_DETAILS
    if has_bad_url:
        return BlockTemplate.DANGEROUS_LINK
    return BlockTemplate.FAKE_DO_NOT_TOUCH


def decide_message(
    *,
    text: str,
    urls: list[str],
    channel: Channel,
    classifier: ThreatClassifier,
    sender_reports: int = 0,
    domain_reports: int = 0,
) -> FastDecision:
    result = classifier.predict(text, channel)
    findings = [analyze_url(url) for url in urls]
    url_score = max((f.score for f in findings), default=0.0)

    # ES: Un enlace malo empuja el riesgo, pero el texto también cuenta.
    # EN: A bad link raises the risk, but the text also counts.
    combined = max(
        result.score + url_score * 0.5,
        url_score,
        _reputation_score(sender_reports),
        _reputation_score(domain_reports),
    )
    level = _level(min(combined, 1.0))

    threat = result.threat_type
    if level != RiskLevel.GREEN and threat == ThreatType.NONE:
        threat = ThreatType.SMISHING if channel == Channel.SMS else ThreatType.PHISHING
    if level == RiskLevel.RED and threat == ThreatType.SPAM:
        threat = ThreatType.PHISHING

    action = {
        RiskLevel.GREEN: Action.ALLOW,
        RiskLevel.AMBER: Action.SILENT_BLOCK,
        RiskLevel.RED: Action.BLOCK_AND_ALERT,
    }[level]
    if level == RiskLevel.GREEN:
        threat = ThreatType.NONE

    reasons = result.reasons + [r for f in findings for r in f.reasons]
    if sender_reports:
        reasons.append(f"El remitente ya ha sido reportado {sender_reports} veces.")
    return FastDecision(
        risk_level=level,
        threat_type=threat,
        action=action,
        block_template=_template_for(level, result, url_score >= AMBER_THRESHOLD),
        confidence=round(
            min(combined, 1.0) if level != RiskLevel.GREEN else 1 - combined, 3
        ),
        reasons=reasons,
        url_findings=findings,
    )


def decide(
    *,
    input_type: InputType,
    origin: Origin,
    channel: Channel,
    text: str,
    urls: list[str],
    classifier: ThreatClassifier,
    sender_reports: int = 0,
    domain_reports: int = 0,
    sender_phone: str | None = None,
) -> FastDecision:
    if input_type == InputType.PHONE_NUMBER:
        return decide_phone(origin, sender_reports, sender_phone)
    decision = decide_message(
        text=text,
        urls=urls,
        channel=channel,
        classifier=classifier,
        sender_reports=sender_reports,
        domain_reports=domain_reports,
    )
    # ES: En un reenvío manual el Sénior espera una respuesta: siempre plantilla.
    #     Sin señales de riesgo no decimos "es seguro", sino "consulta a tu familiar".
    # EN: In a manual forward the senior expects an answer: always a template.
    #     With no risk signals we do not say "safe", but "ask your family".
    if origin == Origin.MANUAL and decision.block_template is None:
        return replace(decision, block_template=BlockTemplate.UNSURE_CALL_FAMILY)
    return decision


def apply_url_reputation(
    baseline: FastDecision, channel: Channel, findings: list[UrlFinding]
) -> FastDecision:
    """Positive evidence can raise risk, never downgrade the baseline.

    Scores are policy weights, not calibrated probabilities. Keep external
    evidence separate from local reports: an exact URL is not a bad domain.
    """
    findings = [f for f in findings if f.score >= AMBER_THRESHOLD]
    if not findings:
        return baseline
    score = max(f.score for f in findings)
    level = _level(score)
    order = {RiskLevel.GREEN: 0, RiskLevel.AMBER: 1, RiskLevel.RED: 2}
    reasons = list(dict.fromkeys(r for f in findings for r in f.reasons))
    if order[level] <= order[baseline.risk_level]:
        return replace(
            baseline,
            reasons=baseline.reasons + reasons,
            reputation_findings=findings,
        )
    threat = baseline.threat_type
    if threat in (ThreatType.NONE, ThreatType.SPAM):
        threat = ThreatType.SMISHING if channel == Channel.SMS else ThreatType.PHISHING
    template = (
        baseline.block_template
        if baseline.block_template == BlockTemplate.ASKS_BANK_DETAILS
        else BlockTemplate.DANGEROUS_LINK
    )
    return replace(
        baseline,
        risk_level=level,
        threat_type=threat,
        action=(
            Action.BLOCK_AND_ALERT if level == RiskLevel.RED else Action.SILENT_BLOCK
        ),
        block_template=template,
        confidence=round(score, 3),
        reasons=reasons + baseline.reasons,
        reputation_findings=findings,
        reputation_only=baseline.risk_level == RiskLevel.GREEN,
    )


def apply_phone_reputation(
    baseline: FastDecision, status: str, score: int, label: str
) -> FastDecision:
    """ES: Señal externa de un número (#168). Puede subir el riesgo, nunca bajarlo.
    Si solo la señal externa lo marca, reputation_only=True: no se crea reporte
    local del número (un tercero no cuenta como una persona de Avizor).
    EN: External number signal (#168). Can raise risk, never lower it. If only
    the external signal marks it, reputation_only=True: no local report is made.
    """
    if status not in ("malicious", "suspicious") or not 0 <= score <= 100:
        return baseline
    reason = f"{label} informa de reportes de la comunidad sobre este número."
    level = _level(score / 100)
    order = {RiskLevel.GREEN: 0, RiskLevel.AMBER: 1, RiskLevel.RED: 2}
    if order[level] <= order[baseline.risk_level]:
        if level == RiskLevel.GREEN:
            return baseline
        return replace(baseline, reasons=baseline.reasons + [reason])
    red = level == RiskLevel.RED
    return replace(
        baseline,
        risk_level=level,
        threat_type=ThreatType.VISHING,
        action=Action.BLOCK_AND_ALERT if red else Action.ALLOW,
        block_template=BlockTemplate.SUSPICIOUS_CALL,
        confidence=round(score / 100, 3),
        reasons=baseline.reasons + [reason],
        reputation_only=baseline.risk_level == RiskLevel.GREEN,
    )
