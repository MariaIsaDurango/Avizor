"""Clasificador de IA (#38): reglas de mapeo, carga y respaldo.
AI classifier (#38): mapping rules, loading and fallback.

ES: Los tests de mapeo usan probabilidades fijas (sin modelo). El test con el
    modelo real solo se ejecuta si ML_MODEL_DIR apunta a un paquete exportado.
EN: Mapping tests use fixed probabilities (no model). The real-model test only
    runs if ML_MODEL_DIR points to an exported bundle.
"""

import json
import os
from pathlib import Path

import pytest

from app.schemas.enums import Channel, RiskLevel, ThreatType
from app.services.detection.decision import decide_message
from app.services.detection.ml_classifier import (
    REASON_FRAUD,
    REASON_SPAM,
    MlClassifier,
    build_classifier,
    load_ml_classifier,
)
from app.services.detection.text_rules import KeywordClassifier


def fixed(p_none: float, p_spam: float, p_fraud: float, threshold: float = 0.36):
    return MlClassifier(
        lambda _text: (p_none, p_spam, p_fraud),
        model_version="test-model",
        fraud_threshold=threshold,
    )


def level(classifier, text="Hola", channel=Channel.SMS) -> RiskLevel:
    return decide_message(
        text=text, urls=[], channel=channel, classifier=classifier
    ).risk_level


def test_fraud_above_threshold_is_red_even_if_not_most_likely():
    classifier = fixed(0.55, 0.05, 0.40)
    result = classifier.predict("Hola", Channel.SMS)
    assert result.threat_type == ThreatType.SMISHING
    assert REASON_FRAUD in result.reasons
    assert level(classifier) == RiskLevel.RED


def test_fraud_below_threshold_is_not_red():
    assert level(fixed(0.55, 0.05, 0.40, threshold=0.5)) == RiskLevel.GREEN


def test_fraud_by_email_is_phishing():
    result = fixed(0.1, 0.1, 0.8).predict("Hola", Channel.NOTIFICATION)
    assert result.threat_type == ThreatType.PHISHING


def test_fraud_keeps_subtype_and_bank_details_from_rules():
    text = "Su cuenta del banco ha sido bloqueada, envíe su [IBAN] y su PIN"
    result = fixed(0.1, 0.1, 0.8).predict(text, Channel.NOTIFICATION)
    assert result.threat_type == ThreatType.BANK_FRAUD
    assert result.asks_bank_details


def test_spam_is_amber_and_never_red_on_its_own():
    classifier = fixed(0.0, 1.0, 0.0)
    result = classifier.predict("Oferta exclusiva", Channel.SMS)
    assert result.threat_type == ThreatType.SPAM
    assert REASON_SPAM in result.reasons
    assert level(classifier) == RiskLevel.AMBER


def test_normal_message_is_green_without_reasons():
    result = fixed(0.97, 0.02, 0.01).predict("Llego a las ocho", Channel.SMS)
    assert result.threat_type == ThreatType.NONE
    assert result.reasons == []
    assert level(fixed(0.97, 0.02, 0.01)) == RiskLevel.GREEN


def test_normal_text_with_bad_link_can_still_be_flagged():
    decision = decide_message(
        text="Mira esto",
        urls=["http://192.168.1.10/login"],
        channel=Channel.SMS,
        classifier=fixed(0.97, 0.02, 0.01),
    )
    assert decision.risk_level != RiskLevel.GREEN


@pytest.mark.parametrize("threshold", [0, 1, -0.1, 1.5])
def test_invalid_threshold_is_rejected(threshold):
    with pytest.raises(ValueError):
        fixed(0.3, 0.3, 0.4, threshold=threshold)


def test_keywords_is_the_default():
    assert isinstance(build_classifier("keywords", None), KeywordClassifier)


def test_ml_without_model_falls_back_to_keywords(tmp_path):
    assert isinstance(build_classifier("ml", None), KeywordClassifier)
    assert isinstance(build_classifier("ml", str(tmp_path)), KeywordClassifier)


def test_bundle_with_other_labels_is_rejected(tmp_path):
    (tmp_path / "avizor_classifier.json").write_text(
        json.dumps({"labels": ["ham", "spam"]}), "utf-8"
    )
    with pytest.raises(ValueError):
        load_ml_classifier(tmp_path)
    assert isinstance(build_classifier("ml", str(tmp_path)), KeywordClassifier)


REAL_MODEL = os.environ.get("ML_MODEL_DIR")


@pytest.mark.skipif(
    not REAL_MODEL or not (Path(REAL_MODEL) / "avizor_classifier.json").exists(),
    reason="ML_MODEL_DIR no apunta a un modelo exportado / no exported model",
)
def test_real_model_loads_and_classifies():
    classifier = load_ml_classifier(Path(REAL_MODEL))
    assert classifier.model_version.endswith("onnx-int8")
    scam = "Su cuenta ha sido bloqueada. Verifique sus datos en este enlace hoy mismo."
    assert classifier.predict(scam, Channel.SMS).threat_type != ThreatType.NONE
