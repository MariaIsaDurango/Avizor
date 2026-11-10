"""Señales de riesgo en enlaces, sin llamar a servicios externos (< 1 ms).
Link risk signals, without calling external services (< 1 ms).

ES: Las APIs de reputación externas (María) se añadirán en otra issue.
EN: External reputation APIs (María) will be added in another issue.
"""

import ipaddress
from dataclasses import dataclass, field
from urllib.parse import urlsplit

SUSPICIOUS_TLDS = {
    "top",
    "xyz",
    "click",
    "live",
    "icu",
    "buzz",
    "rest",
    "cfd",
    "sbs",
    "shop",
    "info",
    "online",
    "site",
    "support",
    "monster",
}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "cutt.ly", "is.gd", "ow.ly", "t.ly"}

# ES: Marca → dominios oficiales. Ampliable. EN: Brand → official domains.
OFFICIAL_DOMAINS = {
    "bbva": {"bbva.es", "bbva.com"},
    "santander": {"bancosantander.es", "santander.com"},
    "caixabank": {"caixabank.es", "caixabank.com"},
    "sabadell": {"bancsabadell.com"},
    "correos": {"correos.es", "correos.com"},
    "dgt": {"dgt.es", "dgt.gob.es"},
    "hacienda": {"agenciatributaria.gob.es", "agenciatributaria.es"},
    "seguridadsocial": {"seg-social.es", "seg-social.gob.es"},
    "amazon": {"amazon.es", "amazon.com"},
}


@dataclass(frozen=True)
class UrlFinding:
    domain: str
    score: float
    reasons: list[str] = field(default_factory=list)


def _is_subdomain_of(host: str, official: str) -> bool:
    return host == official or host.endswith("." + official)


def domain_of(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return host.removeprefix("www.")


def analyze_url(url: str) -> UrlFinding:
    parts = urlsplit(url)
    host = domain_of(url)
    score, reasons = 0.0, []

    official_hosts = {d for domains in OFFICIAL_DOMAINS.values() for d in domains}
    if any(_is_subdomain_of(host, d) for d in official_hosts):
        return UrlFinding(host, 0.0)

    for brand in OFFICIAL_DOMAINS:
        if brand in host.replace("-", "").replace(".", ""):
            score += 0.6
            reasons.append(f"Imita a {brand.upper()} en un dominio que no es oficial.")
            break
    if host.rsplit(".", 1)[-1] in SUSPICIOUS_TLDS:
        score += 0.3
        reasons.append("Usa una terminación de dominio muy usada en estafas.")
    if host.startswith("xn--") or ".xn--" in host:
        score += 0.4
        reasons.append("El dominio usa letras que imitan a otras.")
    try:
        ipaddress.ip_address(host)
        score += 0.4
        reasons.append("El enlace es una dirección IP, no un dominio.")
    except ValueError:
        pass
    if host in SHORTENERS:
        score += 0.2
        reasons.append("El enlace está acortado y oculta el destino.")
    if parts.scheme == "http":
        score += 0.1
        reasons.append("El enlace no es seguro (http).")
    return UrlFinding(host, min(score, 1.0), reasons)
