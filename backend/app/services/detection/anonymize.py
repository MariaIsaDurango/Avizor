"""Anonimización en el servidor, igual a la del móvil (regex-v0).
Server-side anonymization, identical to the phone's (regex-v0).

ES: Se usa solo cuando el servidor extrae texto de un adjunto (#164): ese texto
    no pasó por el móvil, así que se anonimiza aquí, en memoria, antes de
    clasificarlo, enviarlo al agente o guardarlo. Mismas reglas y marcadores
    que mobile/src/services/anonymize.ts y ml/src/classifier/anonymize.py
    (test de paridad en tests/test_attachment_text.py).
EN: Used only when the server extracts text from an attachment (#164): that
    text never went through the phone, so it is anonymized here, in memory,
    before classifying, sending it to the agent or storing it. Same rules and
    markers as the phone and the ML copy (parity test in the tests).
"""

import re

# ES: re.ASCII imita \b y \w de JavaScript. EN: re.ASCII mimics JavaScript.
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

NER_MODEL_VERSION = "regex-v0"


def anonymize(text: str) -> str:
    """ES: Sustituye los datos personales por [IBAN], [CARD], [PHONE]...
    EN: Replaces personal data with [IBAN], [CARD], [PHONE]...
    """
    result = text or ""
    for tag, pattern in RULES:
        result = pattern.sub(f"[{tag}]", result)
    return result
