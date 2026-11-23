"""Clasificador de IA (#38): modelo BETO de 3 clases exportado a ONNX int8.
AI classifier (#38): 3-class BETO model exported to ONNX int8.

ES: El modelo decide el nivel de riesgo (none / spam / fraud). Las reglas por
    palabras clave se siguen usando para lo que el modelo no da: el subtipo de
    amenaza (bancaria, smishing, identidad), si pide datos bancarios y los
    motivos para el Tutor. Los motivos son siempre textos fijos.
    No usa torch: onnxruntime + tokenizers. El texto llega ya anonimizado
    desde el móvil, con las mismas reglas con las que se entrenó el modelo.
    Si el modelo no se puede cargar, se usa KeywordClassifier (nunca se cae
    la vía rápida).
EN: The model decides the risk level (none / spam / fraud). Keyword rules are
    still used for what the model does not provide: the threat subtype (bank,
    smishing, identity), whether it asks for bank details and the reasons for
    the guardian. Reasons are always fixed texts.
    No torch: onnxruntime + tokenizers. Text arrives already anonymized from
    the phone, with the same rules used to train the model.
    If the model cannot be loaded, KeywordClassifier is used (the fast path
    never goes down).
"""

import json
import logging
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np

from app.schemas.enums import Channel, ThreatType
from app.services.detection.decision import AMBER_THRESHOLD, RED_THRESHOLD
from app.services.detection.text_rules import (
    ClassifierResult,
    KeywordClassifier,
    ThreatClassifier,
)

logger = logging.getLogger(__name__)

CONFIG_FILE = "avizor_classifier.json"
LABELS = ("none", "spam", "fraud")
FRAUD_SUBTYPES = (ThreatType.BANK_FRAUD, ThreatType.SMISHING, ThreatType.IDENTITY_THEFT)
REASON_FRAUD = "El análisis automático lo considera una posible estafa."
REASON_SPAM = "El análisis automático lo considera publicidad no deseada."

# ES: Devuelve [p_none, p_spam, p_fraud] para un texto.
# EN: Returns [p_none, p_spam, p_fraud] for one text.
ProbabilityFn = Callable[[str], Sequence[float]]


def _softmax(logits: np.ndarray) -> np.ndarray:
    exp = np.exp(logits - logits.max())
    return exp / exp.sum()


class MlClassifier:
    """ES: Cumple ThreatClassifier. EN: Implements ThreatClassifier."""

    def __init__(
        self,
        probabilities: ProbabilityFn,
        *,
        model_version: str,
        fraud_threshold: float,
        rules: KeywordClassifier | None = None,
    ):
        if not 0 < fraud_threshold < 1:
            raise ValueError("fraud_threshold must be between 0 and 1")
        self._probabilities = probabilities
        self.model_version = model_version
        self.fraud_threshold = fraud_threshold
        self._rules = rules or KeywordClassifier()

    def predict(self, text: str, channel: Channel) -> ClassifierResult:
        p_none, p_spam, p_fraud = (float(p) for p in self._probabilities(text))
        rules = self._rules.predict(text, channel)

        if p_fraud >= self.fraud_threshold:
            # ES: Estafa → rojo. Cuanto más segura, más alta la puntuación.
            # EN: Scam → red. The surer the model, the higher the score.
            score = RED_THRESHOLD + (1 - RED_THRESHOLD) * p_fraud
            if rules.threat_type in FRAUD_SUBTYPES:
                threat = rules.threat_type
            elif channel == Channel.SMS:
                threat = ThreatType.SMISHING
            else:
                threat = ThreatType.PHISHING
            reasons = [REASON_FRAUD, *rules.reasons]
        elif p_spam > p_none:
            # ES: Publicidad → ámbar, nunca rojo por sí sola.
            # EN: Advertising → amber, never red on its own.
            score = AMBER_THRESHOLD + (RED_THRESHOLD - AMBER_THRESHOLD - 0.01) * p_spam
            threat = ThreatType.SPAM
            reasons = [REASON_SPAM, *rules.reasons]
        else:
            # ES: Normal → verde. Un enlace o la reputación aún pueden subirlo.
            # EN: Normal → green. A link or reputation can still raise it.
            score = (AMBER_THRESHOLD - 0.01) * (1 - p_none)
            threat = ThreatType.NONE
            reasons = []

        return ClassifierResult(
            threat_type=threat,
            score=round(min(score, 1.0), 3),
            asks_bank_details=rules.asks_bank_details,
            reasons=reasons,
        )


def _onnx_probabilities(model_dir: Path, config: dict, threads: int) -> ProbabilityFn:
    # ES: Importes aquí: sin modelo no hace falta onnxruntime.
    # EN: Imports here: without a model onnxruntime is not needed.
    import onnxruntime as ort
    from tokenizers import Tokenizer

    options = ort.SessionOptions()
    options.intra_op_num_threads = threads
    session = ort.InferenceSession(
        str(model_dir / config["onnx_file"]),
        sess_options=options,
        providers=["CPUExecutionProvider"],
    )
    input_names = [item.name for item in session.get_inputs()]
    tokenizer = Tokenizer.from_file(str(model_dir / config["tokenizer_file"]))
    tokenizer.enable_truncation(int(config["max_length"]))

    def probabilities(text: str) -> Sequence[float]:
        encoding = tokenizer.encode(text)
        columns = {
            "input_ids": encoding.ids,
            "attention_mask": encoding.attention_mask,
            "token_type_ids": encoding.type_ids,
        }
        feed = {
            name: np.asarray([columns[name]], dtype=np.int64) for name in input_names
        }
        return _softmax(session.run(None, feed)[0][0]).tolist()

    return probabilities


def load_ml_classifier(
    model_dir: Path, *, fraud_threshold: float | None = None, threads: int = 1
) -> MlClassifier:
    config = json.loads((model_dir / CONFIG_FILE).read_text("utf-8"))
    if tuple(config["labels"]) != LABELS:
        raise ValueError(f"Unexpected labels: {config['labels']}")
    return MlClassifier(
        _onnx_probabilities(model_dir, config, threads),
        model_version=config["model_version"],
        fraud_threshold=(
            fraud_threshold
            if fraud_threshold is not None
            else float(config["fraud_threshold"])
        ),
    )


def build_classifier(
    provider: str,
    model_dir: str | None,
    *,
    fraud_threshold: float | None = None,
    threads: int = 1,
) -> ThreatClassifier:
    """ES: "keywords" (por defecto) o "ml". Si "ml" falla, vuelve a palabras clave.
    EN: "keywords" (default) or "ml". If "ml" fails, falls back to keywords.
    """
    if provider != "ml":
        return KeywordClassifier()
    try:
        if not model_dir:
            raise FileNotFoundError("ML_MODEL_DIR is not set")
        classifier = load_ml_classifier(
            Path(model_dir), fraud_threshold=fraud_threshold, threads=threads
        )
    except Exception:
        logger.exception("ML classifier could not be loaded; using keywords")
        return KeywordClassifier()
    logger.info(
        "ML classifier loaded: %s (fraud threshold %.2f)",
        classifier.model_version,
        classifier.fraud_threshold,
    )
    return classifier
