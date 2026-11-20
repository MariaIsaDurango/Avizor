"""Small deterministic contextual tie-breaker; never changes cosine distances."""

import re
import unicodedata

# Broad subjects, not threat classifications or proof of fraud.
TOPICS = {
    "bank": r"\b(?:banco(?:s)?|bancari[oa]s?|entidades financieras|servicio financiero|oney)\b",
    "parcel": r"\b(?:paquete(?:s)?|paqueteria|envio(?:s)?|mensajeria)\b",
    "tax": r"\b(?:aeat|agencia tributaria|hacienda|dehu)\b",
    "social_security": r"\b(?:tgss|seguridad social)\b",
    "traffic": r"\b(?:dgt|multas?|trafico)\b",
    "family": r"\b(?:hij[oa]s?|madre|padre|familiares?|familia)\b",
    "bizum": r"\bbizum\b",
    "crypto": r"\b(?:criptomonedas?|cripto|bitcoin)\b",
    "spam": r"\b(?:spam|publicidad|publicitarios?|no solicitad[oa]s?)\b",
}
BONUS = 0.02
WINDOW = 0.025


def topics(text: str) -> set[str]:
    normalized = "".join(
        c
        for c in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(c)
    )
    return {name for name, pattern in TOPICS.items() if re.search(pattern, normalized)}


def rerank(text, notices):
    """Promote topic matches only among close, already validated candidates."""
    candidates = sorted(notices, key=lambda item: item.distance)[:5]
    wanted = topics(text)
    if not candidates or not wanted:
        return candidates
    best = candidates[0].distance

    def score(item):
        matched = wanted & topics(f"{item.title} {item.impersonated_entities}")
        bonus = (
            BONUS * len(matched) / len(wanted) if item.distance <= best + WINDOW else 0
        )
        return item.distance - bonus

    return sorted(candidates, key=score)
