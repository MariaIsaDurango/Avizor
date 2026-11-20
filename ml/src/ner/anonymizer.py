from __future__ import annotations

import re
from dataclasses import dataclass, field

# Bump when regex patterns or the spaCy model change so backends can track
# which anonymization pass was applied to each message.
NER_MODEL_VERSION = "hybrid-regex-spacy-es-sm-1.0"

# Order matters: IBAN before CARD to avoid partial overlaps.
_REGEX_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b", re.IGNORECASE), "[EMAIL]"),
    (re.compile(r"https?://\S+", re.IGNORECASE), "[URL]"),
    (re.compile(r"\b[A-Z]{2}\d{2}[\s]?(?:\d{4}[\s]?){3,6}\b"), "[IBAN]"),
    (re.compile(r"\b(?:\d{4}[\s\-]?){3}\d{4}\b"), "[CARD]"),
    (re.compile(r"\b(?:\+?34[\s\-]?)?[6789]\d{2}[\s\-]?\d{3}[\s\-]?\d{3}\b"), "[PHONE]"),
    (re.compile(r"\b\d{8}[A-Z]\b"), "[ID_NUMBER]"),   # DNI
    (re.compile(r"\b[XYZ]\d{7}[A-Z]\b"), "[ID_NUMBER]"),  # NIE
]

_nlp = None


def _load_spacy():
    global _nlp
    if _nlp is None:
        try:
            import spacy  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "spaCy is required for NER: pip install spacy"
            ) from exc
        try:
            _nlp = spacy.load("es_core_news_sm")
        except OSError as exc:
            raise OSError(
                "Spanish spaCy model not found — run: "
                "python -m spacy download es_core_news_sm"
            ) from exc
    return _nlp


@dataclass
class AnonymizationResult:
    text: str
    entities_found: list[str] = field(default_factory=list)


def anonymize(text: str, *, use_ner: bool = True) -> AnonymizationResult:
    """Replace sensitive entities with bracketed placeholders.

    Args:
        text: Raw input text (email body, SMS, push notification content).
        use_ner: If True, also run spaCy NER for NAME and ADDRESS detection.
                 Set to False when the model is not installed (e.g. CI).

    Returns:
        AnonymizationResult with the censored text and detected entity types.
    """
    entities: list[str] = []

    # --- Regex pass (structured entities) ---
    for pattern, placeholder in _REGEX_PATTERNS:
        if pattern.search(text):
            label = placeholder.strip("[]")
            if label not in entities:
                entities.append(label)
            text = pattern.sub(placeholder, text)

    # --- spaCy NER pass (NAME, ADDRESS) ---
    if use_ner:
        nlp = _load_spacy()
        doc = nlp(text)
        replacements: list[tuple[int, int, str]] = []
        for ent in doc.ents:
            if ent.label_ == "PER":
                replacements.append((ent.start_char, ent.end_char, "[NAME]"))
                if "NAME" not in entities:
                    entities.append("NAME")
            elif ent.label_ in ("LOC", "GPE"):
                replacements.append((ent.start_char, ent.end_char, "[ADDRESS]"))
                if "ADDRESS" not in entities:
                    entities.append("ADDRESS")
        # Apply in reverse order to preserve character offsets
        for start, end, placeholder in sorted(replacements, key=lambda x: x[0], reverse=True):
            text = text[:start] + placeholder + text[end:]

    return AnonymizationResult(text=text, entities_found=entities)
