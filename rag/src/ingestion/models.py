"""Contract-compatible document records and chunk metadata."""

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import parse_qs, urlsplit

from .cleaner import clean_text, content_hash

SOURCES = {"incibe", "osi", "policia_nacional", "banco_espana"}
THREATS = {
    "phishing",
    "smishing",
    "vishing",
    "spam",
    "identity_theft",
    "bank_fraud",
    "other",
    "none",
}
MODEL_NAME = "multilingual-e5-base"


def official_url(source: str, url: str) -> bool:
    """Recognize canonical article URLs from #40, not arbitrary links."""
    try:
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or parts.username
            or parts.password
            or parts.port is not None
        ):
            return False
    except ValueError:
        return False
    if parts.fragment or re.search(r"%2f|%5c|%2e|%25|\\", parts.path, re.IGNORECASE):
        return False
    if source in {"incibe", "osi"}:
        section = "avisos" if source == "incibe" else "blog"
        return (
            parts.netloc == "www.incibe.es"
            and not parts.query
            and bool(re.fullmatch(rf"/ciudadania/{section}/[\w%-]+", parts.path))
        )
    if source == "banco_espana":
        return (
            parts.netloc == "clientebancario.bde.es"
            and not parts.query
            and bool(re.fullmatch(r"/pcb/es/blog/[\w%-]+\.html", parts.path))
            and not re.fullmatch(r"/pcb/es/blog/index\d*\.html", parts.path)
        )
    return (
        source == "policia_nacional"
        and parts.netloc == "www.policia.es"
        and parts.path == "/_es/comunicacion_prensa_detalle.php"
        and bool(re.fullmatch(r"ID=\d{1,10}", parts.query))
        and len(parse_qs(parts.query)) == 1
    )


def cutoff(today: date) -> date:
    try:
        return today.replace(year=today.year - 2)
    except ValueError:
        return today.replace(year=today.year - 2, day=28)


@dataclass(frozen=True)
class Notice:
    source: str
    url: str
    title: str
    published_at: str
    scraped_at: str
    text: str
    content_hash: str
    threat_type: str
    impersonated_entities: str = ""
    synthetic: bool = False

    @classmethod
    def from_record(
        cls, raw: dict, *, today: date, synthetic: bool, approval: dict | None = None
    ):
        if raw.get("source") not in SOURCES:
            raise ValueError("Invalid source")
        text = raw.get("text")
        if not isinstance(text, str) or not clean_text(text):
            raise ValueError("Missing document text")
        digest = content_hash(text)
        supplied = raw.get("content_hash")
        if supplied not in {digest, digest.removeprefix("sha256:")}:
            raise ValueError("Content hash mismatch")
        url = raw["url"]
        if synthetic:
            if raw.get("synthetic") is not True or not url.startswith(
                "https://example.invalid/"
            ):
                raise ValueError(
                    "Synthetic records must be explicitly marked and use example.invalid"
                )
            labels = raw
        else:
            if raw.get("synthetic") or not official_url(raw["source"], url):
                raise ValueError("Non-official URL")
            if not approval or approval.get("content_hash") != digest:
                raise ValueError("Missing approval for this exact document version")
            if (
                approval.get("rag_allowed") is not True
                or not str(approval.get("reference") or "").strip()
            ):
                raise ValueError("RAG permission not recorded")
            if not str(raw.get("reuse_reference") or "").strip():
                raise ValueError("Missing source reuse reference")
            labels = approval
        published = date.fromisoformat(raw["published_at"])
        if not cutoff(today) <= published <= today:
            raise ValueError("Publication outside 24-month window")
        scraped = datetime.fromisoformat(raw["scraped_at"])
        if scraped.tzinfo is None or scraped.date() < published:
            raise ValueError("Invalid scraping timestamp")
        threat = labels.get("threat_type")
        entities = labels.get("impersonated_entities", "")
        if threat not in THREATS or not isinstance(entities, str):
            raise ValueError("Invalid threat classification or entities")
        title = clean_text(raw["title"])
        if not title:
            raise ValueError("Missing title")
        return cls(
            raw["source"],
            url,
            title,
            published.isoformat(),
            raw["scraped_at"],
            clean_text(text),
            digest,
            threat,
            entities,
            synthetic,
        )

    def chunk_id(self, index: int) -> str:
        # URL-based slug plus digest prevents collisions, independent of title changes.
        path = urlsplit(self.url).path.rsplit("/", 1)[-1].removesuffix(".html")
        slug = re.sub(r"[^a-z0-9-]+", "-", path.lower()).strip("-")[:65] or "notice"
        suffix = hashlib.sha256(self.url.encode()).hexdigest()[:12]
        return f"{self.source}:{self.published_at}:{slug}-{suffix}:{index:04d}"

    def metadata(self) -> dict:
        return {
            "source": self.source,
            "url": self.url,
            "title": self.title,
            "published_at": self.published_at,
            "scraped_at": self.scraped_at,
            "threat_type": self.threat_type,
            "impersonated_entities": self.impersonated_entities,
            "content_hash": self.content_hash,
            "embedding_model": MODEL_NAME,
        }
