"""Filtered, bounded retrieval; all inputs are already anonymized."""

import math
from dataclasses import dataclass
from datetime import date

from rag.src.ingestion.models import THREATS, cutoff, official_url


@dataclass(frozen=True)
class RetrievedNotice:
    chunk_id: str
    text: str
    source: str
    url: str
    title: str
    published_at: date
    distance: float
    synthetic: bool


def build_filter(threat_type: str, today: date) -> dict:
    """Match reviewed labels and an inclusive calendar-date range in Chroma."""
    if threat_type not in THREATS or threat_type == "none":
        raise ValueError("Retrieval requires a known threat")
    return {
        "$and": [
            {f"is_{threat_type}": {"$eq": True}},
            {"published_at_day": {"$gte": cutoff(today).toordinal()}},
            {"published_at_day": {"$lte": today.toordinal()}},
        ]
    }


class Retriever:
    def __init__(self, store, embedder, *, max_distance: float = 0.35, demo=False):
        if store.synthetic != demo:
            raise ValueError("Corpus mode mismatch")
        if not 0 <= max_distance <= 2:
            raise ValueError("Invalid cosine distance threshold")
        if store.collection.metadata.get("embedding_revision") != embedder.revision:
            raise ValueError("Embedding revision mismatch")
        self.store = store
        self.embedder = embedder
        self.max_distance = max_distance
        self.demo = demo

    def retrieve(self, text: str, threat_type: str, *, today: date | None = None):
        today = today or date.today()
        if not text.strip() or threat_type == "none":
            return []
        where = build_filter(threat_type, today)
        # E5 rejects overlength queries rather than silently truncating them.
        vector = self.embedder.encode([text], query=True)[0]
        result = self.store.query(vector, where=where, documents=True)
        notices = []
        for chunk_id, document, meta, distance in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
            strict=True,
        ):
            if not meta or not isinstance(document, str) or not document.strip():
                continue
            if not math.isfinite(distance) or not 0 <= distance <= self.max_distance:
                continue
            published = date.fromisoformat(meta["published_at"])
            if (
                not cutoff(today) <= published <= today
                or meta.get("published_at_day") != published.toordinal()
                or meta.get(f"is_{threat_type}") is not True
            ):
                continue
            source, url = meta["source"], meta["url"]
            if self.demo:
                if not url.startswith("https://example.invalid/"):
                    continue
            elif not official_url(source, url):
                continue
            notices.append(
                RetrievedNotice(
                    chunk_id,
                    document,
                    source,
                    url,
                    meta["title"],
                    published,
                    distance,
                    self.demo,
                )
            )
        return sorted(notices, key=lambda item: item.distance)[:5]
