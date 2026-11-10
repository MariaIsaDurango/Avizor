"""Decisión de la vía rápida: semáforo, acción y plantilla.
Fast path decision: traffic light, action and template.

ES: Combina clasificador + señales de enlaces + reputación. Sin LLM ni RAG.
    El texto de la pantalla del Sénior es SIEMPRE una plantilla fija.
EN: Combines classifier + link signals + reputation. No LLM or RAG.
    The senior's screen text is ALWAYS a fixed template.
"""

from dataclasses import dataclass, field

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


@dataclass(frozen=True)
class FastDecision:
    risk_level: RiskLevel
    threat_type: ThreatType
    action: Action
    block_template: BlockTemplate | None
    confidence: float
    reasons: list[str] = field(default_factory=list)
    url_findings: list[UrlFinding] = field(default_factory=list)


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


def decide_phone(origin: Origin, sender_reports: int) -> FastDecision:
    """ES: Vishing: solo se mira el número, nunca la conversación.
    EN: Vishing: only the number is checked, never the conversation.
    """
    level = _level(_reputation_score(sender_reports))
    reasons = (
        [f"Este número ya ha sido reportado {sender_reports} veces."]
        if sender_reports
        else []
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
) -> FastDecision:
    if input_type == InputType.PHONE_NUMBER:
        return decide_phone(origin, sender_reports)
    return decide_message(
        text=text,
        urls=urls,
        channel=channel,
        classifier=classifier,
        sender_reports=sender_reports,
        domain_reports=domain_reports,
    )
