"""Build official evidence from retrieved metadata, never from model output."""

from rag.src.ingestion.models import official_url

from .retriever import RetrievedNotice


def official_evidence(notices: list[RetrievedNotice]) -> list[dict[str, str]]:
    evidence = []
    seen = set()
    for notice in notices[:5]:
        key = (notice.source, notice.url)
        if notice.synthetic or key in seen or not official_url(*key):
            continue
        seen.add(key)
        evidence.append({"type": "official_notice", "source": key[0], "url": key[1]})
    return evidence
