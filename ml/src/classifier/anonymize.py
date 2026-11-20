"""Anonimización igual a la de la app móvil (mobile/src/services/anonymize.ts).
Anonymization identical to the mobile app (mobile/src/services/anonymize.ts).

ES: En producción el texto llega al backend ya anonimizado por el móvil. Para
    que el modelo vea en el entrenamiento lo mismo que verá en producción,
    aquí se usan exactamente las mismas reglas y los mismos marcadores. Si
    cambian en el móvil, hay que cambiarlas aquí (y reentrenar).
    Las URLs NO se sustituyen: el móvil las deja en el texto y son una señal
    útil (dominios sospechosos).
EN: In production the text reaches the backend already anonymized by the
    phone. So the model sees the same text in training and in production,
    the exact same rules and markers are used here. If they change on the
    phone, they must change here too (and the model must be retrained).
    URLs are NOT replaced: the phone keeps them and they are a useful signal.
"""

import re

# ES: Mismo orden y mismos patrones que RULES en anonymize.ts. re.ASCII imita
#     \b y \w de JavaScript (sin flag "u").
# EN: Same order and patterns as RULES in anonymize.ts. re.ASCII mimics
#     JavaScript's \b and \w (no "u" flag).
_A = re.ASCII
_AI = re.ASCII | re.IGNORECASE

RULES: list[tuple[str, re.Pattern[str]]] = [
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){4,7}\b", _AI)),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b", _A)),
    ("ID_NUMBER", re.compile(r"\b(?:\d{8}|[XYZ]\d{7})[ -]?[A-Z]\b", _AI)),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", _A)),
    ("PHONE", re.compile(r"(?:\+\d{2}[ ]?)?\b[6-9]\d{2}[ ]?\d{3}[ ]?\d{3}\b", _A)),
    (
        "ADDRESS",
        re.compile(
            r"\b(?:Calle|Cl\.|C/|Avda?\.?|Avenida|Plaza|Pl\.|Paseo|Po\.|"
            r"Travesía|Ronda|Camino|Gran Vía)\s+[^\n,]{3,60}(?:,\s*\d+[a-zA-Z]?)?",
            _AI,
        ),
    ),
]

# ES: Debe coincidir con NER_MODEL_VERSION del móvil.
# EN: Must match the phone's NER_MODEL_VERSION.
NER_MODEL_VERSION = "regex-v0"


def anonymize(text: str) -> str:
    """ES: Sustituye los datos personales por [IBAN], [CARD], [PHONE]...
    EN: Replaces personal data with [IBAN], [CARD], [PHONE]...
    """
    result = text or ""
    for tag, pattern in RULES:
        result = pattern.sub(f"[{tag}]", result)
    return result
