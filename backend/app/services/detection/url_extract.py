"""Extracción de enlaces del texto anonimizado (#151).
Link extraction from the anonymized text (#151).

ES: El móvil solo envía `content.urls` cuando se analiza un enlace suelto. En un SMS
    o email pegado el enlace va dentro del texto y no se revisaba. Aquí se sacan esos
    enlaces para pasarlos a las reglas locales y a la reputación que ya existen.
    El texto ya llega anonimizado: no se procesa ningún dato nuevo del usuario.
EN: The app only sends `content.urls` for a standalone link. In a pasted SMS or email
    the link is inside the text and was never checked. This extracts those links for
    the existing local rules and reputation. The text is already anonymized.
"""

import re

from pydantic import HttpUrl, TypeAdapter, ValidationError

MAX_URLS = 10  # ES/EN: same limit as Content.urls in the contract

# ES: Terminaciones aceptadas para dominios escritos sin "http" ni "www"
#     (ej. "correos-envio.top/pago"). Lista cerrada para no confundir texto normal.
# EN: TLDs accepted for bare domains. Closed list to avoid matching plain text.
BARE_TLDS = (
    "es|com|net|org|eu|info|biz|io|me|co|app|online|site|top|xyz|click|live|icu"
    "|buzz|rest|cfd|sbs|shop|support|monster|link|club|vip"
)
_PATH = r"[^\s<>\"'\[\]{}|\\^`]*"
_URL = re.compile(
    r"(?<![\w@./-])"
    r"(?:"
    rf"https?://{_PATH}"
    rf"|www\.{_PATH}"
    r"|(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    rf"(?:{BARE_TLDS})(?![\w-])(?:/{_PATH})?"
    r")",
    re.IGNORECASE,
)
_TRAILING = ".,;:!?»”’'\""
_HTTP_URL = TypeAdapter(HttpUrl)


def _clean(candidate: str) -> str:
    url = candidate.rstrip(_TRAILING)
    # ES: Quita ")" final salvo si se abrió dentro del enlace.
    # EN: Drop a trailing ")" unless it was opened inside the link.
    while url.endswith(")") and url.count("(") < url.count(")"):
        url = url[:-1].rstrip(_TRAILING)
    return url


def _normalize(candidate: str) -> str | None:
    url = _clean(candidate)
    bare = not re.match(r"https?://|www\.", url, re.IGNORECASE)
    if not re.match(r"https?://", url, re.IGNORECASE):
        url = "https://" + url
    try:
        parsed = _HTTP_URL.validate_python(url)
    except ValidationError:
        return None
    host = parsed.host or ""
    # ES: Sin punto no es un dominio público (ej. "https://s" cortado).
    # EN: No dot means no public domain (e.g. a truncated "https://s").
    if "." not in host.strip("."):
        return None
    # ES: Sin "http" ni "www" el nombre debe tener letras (no "3.es" ni "v1.com").
    # EN: A bare domain name must contain letters.
    if bare and not re.search(r"[a-z]{2}", host.rsplit(".", 1)[0]):
        return None
    return str(parsed)


def extract_urls(text: str, limit: int = MAX_URLS) -> list[str]:
    """Enlaces normalizados como `HttpUrl`, sin repetir y en orden de aparición.
    Normalized links like `HttpUrl`, unique and in order of appearance.
    """
    found: list[str] = []
    for match in _URL.finditer(text or ""):
        url = _normalize(match.group(0))
        if url and url not in found:
            found.append(url)
            if len(found) == limit:
                break
    return found


def merge_urls(given: list[str], text: str) -> list[str]:
    """`content.urls` primero; después los del texto. Máximo MAX_URLS.
    `content.urls` first, then those in the text. At most MAX_URLS.
    """
    return list(dict.fromkeys([*given, *extract_urls(text)]))[:MAX_URLS]
