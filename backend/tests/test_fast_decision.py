"""Tests del motor de decisión de la vía rápida (sin base de datos).
Fast path decision engine tests (no database).
"""

import uuid
from datetime import UTC, datetime

import pytest

from app.schemas.enums import (
    Action,
    BlockTemplate,
    Channel,
    InputType,
    Origin,
    RiskLevel,
    ThreatType,
)
from app.schemas.verdict import Verdict
from app.services.detection.decision import decide
from app.services.detection.text_rules import KeywordClassifier, normalize_text
from app.services.detection.url_rules import analyze_url

CLASSIFIER = KeywordClassifier()

# ES: Mensajes inventados y ya anonimizados. EN: Fake, already anonymized messages.
CONTRACT_SMS = "BBVA: su cuenta [IBAN] ha sido bloqueada. Verifique en el enlace."
CONTRACT_URL = "https://bbva-seguro.top/login"
FAMILY_SMS = "Hola mamá, llego a las 8 para cenar. Un beso."
SPAM_SMS = "Has ganado un premio. Oferta exclusiva solo hoy."
DELIVERY_SMS = "Correos: su paquete está retenido. Pague 1,99 € para la entrega."


def sms(text, urls=(), **kwargs):
    return decide(
        input_type=InputType.TEXT,
        origin=Origin.AUTOMATIC,
        channel=Channel.SMS,
        text=text,
        urls=list(urls),
        classifier=CLASSIFIER,
        **kwargs,
    )


def phone(origin, reports):
    return decide(
        input_type=InputType.PHONE_NUMBER,
        origin=origin,
        channel=Channel.CALL,
        text="",
        urls=[],
        classifier=CLASSIFIER,
        sender_reports=reports,
    )


def as_verdict(decision):
    """ES: Toda decisión debe cumplir el schema Verdict del contrato.
    EN: Every decision must satisfy the contract Verdict schema.
    """
    return Verdict(
        analysis_id=uuid.uuid4(),
        phase="fast",
        risk_level=decision.risk_level,
        threat_type=decision.threat_type,
        action=decision.action,
        block_template=decision.block_template,
        confidence=decision.confidence,
        final=True,
        issued_at=datetime.now(UTC),
    )


# ---------- Mensajes / Messages ----------


def test_contract_sms_is_red_and_blocked():
    decision = sms(CONTRACT_SMS, [CONTRACT_URL])
    assert decision.risk_level == RiskLevel.RED
    assert decision.threat_type == ThreatType.SMISHING
    assert decision.action == Action.BLOCK_AND_ALERT
    assert decision.block_template == BlockTemplate.ASKS_BANK_DETAILS
    as_verdict(decision)


def test_family_message_is_green():
    decision = sms(FAMILY_SMS)
    assert decision.risk_level == RiskLevel.GREEN
    assert decision.action == Action.ALLOW
    assert decision.block_template is None
    as_verdict(decision)


def test_spam_is_amber_silent_block_never_red():
    decision = sms(SPAM_SMS)
    assert decision.risk_level == RiskLevel.AMBER
    assert decision.threat_type == ThreatType.SPAM
    assert decision.action == Action.SILENT_BLOCK
    as_verdict(decision)


def test_fake_delivery_with_link_is_red_dangerous_link():
    decision = sms(DELIVERY_SMS, ["https://correos-envio.top/pago"])
    assert decision.risk_level == RiskLevel.RED
    assert decision.block_template == BlockTemplate.DANGEROUS_LINK
    as_verdict(decision)


def test_official_link_alone_is_green():
    decision = sms("Consulta tu envío", ["https://www.correos.es/seguimiento"])
    assert decision.risk_level == RiskLevel.GREEN


def test_reported_sender_makes_it_red():
    decision = sms(FAMILY_SMS, sender_reports=5)
    assert decision.risk_level == RiskLevel.RED
    as_verdict(decision)


def test_reasons_are_fixed_texts():
    """ES: Los motivos van al Tutor: textos fijos, nunca generados.
    EN: Reasons go to the guardian: fixed texts, never generated.
    """
    decision = sms(CONTRACT_SMS, [CONTRACT_URL])
    assert "Imita a BBVA en un dominio que no es oficial." in decision.reasons


# ---------- Teléfonos / Phones ----------


@pytest.mark.parametrize(
    ("reports", "level", "template"),
    [
        (0, RiskLevel.GREEN, BlockTemplate.UNSURE_CALL_FAMILY),
        (2, RiskLevel.AMBER, BlockTemplate.SUSPICIOUS_CALL),
        (5, RiskLevel.RED, BlockTemplate.SUSPICIOUS_CALL),
    ],
)
def test_manual_phone_lookup(reports, level, template):
    decision = phone(Origin.MANUAL, reports)
    assert decision.risk_level == level
    assert decision.block_template == template
    as_verdict(decision)


def test_unknown_incoming_call_passes_silently():
    decision = phone(Origin.AUTOMATIC, 0)
    assert decision.action == Action.ALLOW
    assert decision.block_template is None


# ---------- Enlaces y texto / Links and text ----------


@pytest.mark.parametrize(
    "url",
    [
        "https://bbva-seguro.top/login",
        "http://192.168.1.10/banco",
        "https://xn--bva-xxa.com",
    ],
)
def test_suspicious_urls(url):
    assert analyze_url(url).score >= 0.4


def test_normalize_text_removes_accents():
    assert normalize_text("Verifíque su CONTRASEÑA") == "verifique su contrasena"


# ---------- Reenvío manual / Manual forward ----------


def manual_text(text, urls=()):
    return decide(
        input_type=InputType.TEXT,
        origin=Origin.MANUAL,
        channel=Channel.MANUAL,
        text=text,
        urls=list(urls),
        classifier=CLASSIFIER,
    )


def test_manual_green_text_never_says_safe():
    """ES: Contrato: los reenvíos manuales siempre llevan plantilla.
    EN: Contract: manual forwards always carry a template.
    """
    decision = manual_text(FAMILY_SMS)
    assert decision.risk_level == RiskLevel.GREEN
    assert decision.block_template == BlockTemplate.UNSURE_CALL_FAMILY
    as_verdict(decision)


def test_manual_red_text_keeps_its_template():
    decision = manual_text(CONTRACT_SMS, [CONTRACT_URL])
    assert decision.block_template == BlockTemplate.ASKS_BANK_DETAILS


def test_automatic_green_still_has_no_template():
    """ES: En automático no se muestra nada. EN: Automatic shows nothing."""
    assert sms(FAMILY_SMS).block_template is None
