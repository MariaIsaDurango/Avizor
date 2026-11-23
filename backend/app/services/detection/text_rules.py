"""Clasificador de línea base por reglas (hasta que llegue el modelo de Laura).
Rule-based baseline classifier (until Laura's model is delivered).

ES: NO es el clasificador final. Implementa la misma interfaz (ThreatClassifier)
    para que el modelo de ML se pueda enchufar sin tocar el resto del backend.
EN: NOT the final classifier. It implements the same interface (ThreatClassifier)
    so the ML model can be plugged in without touching the rest of the backend.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Protocol

from app.schemas.enums import Channel, ThreatType


@dataclass(frozen=True)
class ClassifierResult:
    threat_type: ThreatType
    score: float  # ES: 0 = seguro, 1 = amenaza / EN: 0 = safe, 1 = threat
    asks_bank_details: bool = False
    reasons: list[str] = field(default_factory=list)


class ThreatClassifier(Protocol):
    """ES: Interfaz que debe cumplir el modelo de ML. EN: Interface for the ML model."""

    model_version: str

    def predict(self, text: str, channel: Channel) -> ClassifierResult: ...


def normalize_text(text: str) -> str:
    """ES: Minúsculas y sin tildes ("Verifíque" → "verifique").
    EN: Lowercase and without accents ("Verifíque" → "verifique").
    """
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


# ES: (patrón, peso, motivo). Los motivos son textos fijos, nunca del LLM.
# EN: (pattern, weight, reason). Reasons are fixed texts, never from the LLM.
Rule = tuple[str, float, str]

BANK_RULES: list[Rule] = [
    (
        r"\b(bbva|santander|caixabank|sabadell|bankinter|unicaja|ing|banco)\b",
        0.25,
        "Menciona un banco.",
    ),
    (
        r"cuenta .{0,20}(bloquead|suspendid|desactivad)",
        0.35,
        "Dice que la cuenta está bloqueada.",
    ),
    (r"\b(verifi|confirm|actualic|valid)\w*", 0.2, "Pide verificar o confirmar datos."),
]
BANK_DETAILS_RULES: list[Rule] = [
    (r"\[(iban|card)\]", 0.35, "Pide datos bancarios."),
    (
        r"\b(pin|clave|contrasena|codigo de (verificacion|seguridad)|cvv)\b",
        0.35,
        "Pide claves o códigos.",
    ),
]
DELIVERY_RULES: list[Rule] = [
    (
        r"\b(paquete|envio|entrega|correos|aduana|repartidor)\b",
        0.25,
        "Habla de un paquete o envío.",
    ),
    (
        r"\b(pague|abone|tasa|importe)\b|\d+[.,]\d{2} ?(€|eur)",
        0.3,
        "Pide un pago pequeño.",
    ),
]
IDENTITY_RULES: list[Rule] = [
    (
        r"\[id_number\]|\b(dni|nie|datos personales)\b",
        0.35,
        "Pide documentos de identidad.",
    ),
]
URGENCY_RULES: list[Rule] = [
    (
        r"\b(urgente|inmediatamente|ultimo aviso|24 ?h(oras)?|hoy mismo)\b",
        0.2,
        "Mete prisa.",
    ),
]
SPAM_RULES: list[Rule] = [
    (
        r"\b(gana|ganado|premio|sorteo|gratis|regalo)\b",
        0.3,
        "Promete premios o regalos.",
    ),
    (r"\b(oferta|exclusiv\w*|descuento|solo hoy|promocion)\b", 0.2, "Anuncia ofertas."),
]


def _apply(rules: list[Rule], text: str) -> tuple[float, list[str]]:
    score, reasons = 0.0, []
    for pattern, weight, reason in rules:
        if re.search(pattern, text):
            score += weight
            reasons.append(reason)
    return score, reasons


class KeywordClassifier:
    model_version = "keywords-baseline-0.1"

    def predict(self, text: str, channel: Channel) -> ClassifierResult:
        clean = normalize_text(text)
        bank, bank_r = _apply(BANK_RULES, clean)
        details, details_r = _apply(BANK_DETAILS_RULES, clean)
        delivery, delivery_r = _apply(DELIVERY_RULES, clean)
        identity, identity_r = _apply(IDENTITY_RULES, clean)
        urgency, urgency_r = _apply(URGENCY_RULES, clean)
        spam, spam_r = _apply(SPAM_RULES, clean)

        candidates = {
            ThreatType.BANK_FRAUD: bank + details,
            ThreatType.SMISHING: delivery,
            ThreatType.IDENTITY_THEFT: identity,
            ThreatType.SPAM: spam,
        }
        threat, best = max(candidates.items(), key=lambda item: item[1])
        if best == 0:
            return ClassifierResult(ThreatType.NONE, 0.0)

        # ES: Por SMS, el fraude bancario es smishing. EN: By SMS, bank fraud is smishing.
        if threat == ThreatType.BANK_FRAUD and channel == Channel.SMS:
            threat = ThreatType.SMISHING
        reasons = bank_r + details_r + delivery_r + identity_r + urgency_r + spam_r
        score = best + urgency + (details if threat != ThreatType.BANK_FRAUD else 0)
        if threat == ThreatType.SPAM:
            score = min(score, 0.6)  # ES: spam nunca es rojo / EN: spam is never red
        return ClassifierResult(
            threat_type=threat,
            score=min(score, 1.0),
            asks_bank_details=details > 0,
            reasons=reasons,
        )
