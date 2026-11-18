"""Offline filter, provenance and regression tests for issue 43."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rag.src.agent.evidence import official_evidence
from rag.src.agent.retriever import Retriever, build_filter
from rag.src.ingestion.cleaner import content_hash
from rag.src.ingestion.models import Notice
from rag.src.vector_store.chroma_store import ChromaStore

TODAY = date(2026, 11, 18)
URL = "https://www.incibe.es/ciudadania/avisos/test-fixture"


def record(**kwargs):
    text = "Texto ficticio para pruebas, no es un aviso real."
    return {
        "source": "incibe",
        "url": URL,
        "title": "Fixture ficticia",
        "text": text,
        "content_hash": content_hash(text),
        "published_at": TODAY.isoformat(),
        "scraped_at": "2026-11-18T12:00:00Z",
        "reuse_reference": "Fixture only",
        **kwargs,
    }


def notice(**kwargs):
    raw = record()
    approval = {
        "content_hash": raw["content_hash"],
        "rag_allowed": True,
        "reference": "Fixture only",
        "threat_type": "smishing",
        **kwargs,
    }
    return Notice.from_record(raw, today=TODAY, synthetic=False, approval=approval)


def test_reviewed_secondary_labels():
    meta = notice(secondary_threats=["phishing", "bank_fraud"]).metadata()
    assert meta["threat_type"] == "smishing"
    assert meta["is_smishing"] and meta["is_phishing"] and meta["is_bank_fraud"]
    assert not meta["is_vishing"]
    assert meta["published_at_day"] == TODAY.toordinal()


@pytest.mark.parametrize("secondary", ["phishing", ["invalid"], ["none"], [{}]])
def test_bad_secondary_labels(secondary):
    with pytest.raises(ValueError, match="secondary"):
        notice(secondary_threats=secondary)


def test_filter_calendar_boundaries():
    assert build_filter("smishing", TODAY) == {
        "$and": [
            {"is_smishing": {"$eq": True}},
            {"published_at_day": {"$gte": date(2024, 11, 18).toordinal()}},
            {"published_at_day": {"$lte": TODAY.toordinal()}},
        ]
    }


def runtime(rows, *, demo=False):
    store = Mock()
    store.synthetic = demo
    store.collection.metadata = {"embedding_revision": "fixture"}
    store.query.return_value = {
        "ids": [[str(i) for i in range(len(rows))]],
        "documents": [["Fixture" for _ in rows]],
        "metadatas": [[m for m, _ in rows]],
        "distances": [[d for _, d in rows]],
    }
    embedder = Mock()
    embedder.revision = "fixture"
    embedder.encode.return_value = [[1.0] + [0.0] * 767]
    return Retriever(store, embedder, demo=demo), store, embedder


def test_filter_and_evidence_use_metadata():
    meta = notice().metadata()
    retriever, store, embedder = runtime([(meta, 0.1), (meta, 0.2)])
    hits = retriever.retrieve("SMS ficticio", "smishing", today=TODAY)
    embedder.encode.assert_called_once_with(["SMS ficticio"], query=True)
    assert store.query.call_args.kwargs == {
        "where": build_filter("smishing", TODAY),
        "documents": True,
    }
    assert official_evidence(hits) == [
        {"type": "official_notice", "source": "incibe", "url": URL}
    ]


@pytest.mark.parametrize(
    "changes,distance",
    [
        ({"is_smishing": False}, 0.1),
        (
            {
                "published_at": "2024-11-17",
                "published_at_day": date(2024, 11, 17).toordinal(),
            },
            0.1,
        ),
        (
            {
                "published_at": "2026-11-19",
                "published_at_day": date(2026, 11, 19).toordinal(),
            },
            0.1,
        ),
        ({"url": "https://evil.invalid/test"}, 0.1),
        ({}, 0.9),
        ({}, float("nan")),
    ],
)
def test_revalidate_results(changes, distance):
    meta = notice().metadata() | changes
    retriever, _, _ = runtime([(meta, distance)])
    assert retriever.retrieve("SMS", "smishing", today=TODAY) == []


def test_top_five_and_no_query_for_none():
    retriever, store, _ = runtime([(notice().metadata(), 0.1)] * 8)
    assert retriever.retrieve("SMS", "none", today=TODAY) == []
    store.query.assert_not_called()
    assert len(retriever.retrieve("SMS", "smishing", today=TODAY)) == 5


def test_demo_never_generates_official_evidence():
    meta = notice().metadata() | {"url": "https://example.invalid/test"}
    retriever, _, _ = runtime([(meta, 0.1)], demo=True)
    hits = retriever.retrieve("SMS", "smishing", today=TODAY)
    assert len(hits) == 1
    assert official_evidence(hits) == []


def test_revision_and_mode_mismatch():
    retriever, store, embedder = runtime([])
    with pytest.raises(ValueError, match="mode"):
        Retriever(store, embedder, demo=True)
    embedder.revision = "other"
    with pytest.raises(ValueError, match="revision"):
        Retriever(retriever.store, embedder)


def test_chroma_query_passes_filter_and_documents():
    store = ChromaStore.__new__(ChromaStore)
    store.collection = Mock()
    store.collection.count.return_value = 10
    vector = [1.0] + [0.0] * 767
    where = build_filter("smishing", TODAY)
    store.query(vector, limit=99, where=where, documents=True)
    store.collection.query.assert_called_once_with(
        query_embeddings=[vector],
        n_results=5,
        include=["metadatas", "distances", "documents"],
        where=where,
    )


def test_actual_chroma_filters(tmp_path):
    pytest.importorskip("chromadb")
    store = ChromaStore(tmp_path / "test", revision="fixture", synthetic=True)
    vector = [1.0] + [0.0] * 767
    meta = notice().metadata() | {"url": "https://example.invalid/test"}
    store.collection.upsert(
        ids=["match", "old", "other"],
        documents=["fixture"] * 3,
        embeddings=[vector] * 3,
        metadatas=[
            meta,
            meta
            | {
                "published_at": "2024-11-17",
                "published_at_day": date(2024, 11, 17).toordinal(),
            },
            meta | {"is_smishing": False},
        ],
    )
    embedder = SimpleNamespace(revision="fixture", encode=lambda *a, **k: [vector])
    hits = Retriever(store, embedder, demo=True).retrieve(
        "SMS", "smishing", today=TODAY
    )
    assert [hit.chunk_id for hit in hits] == ["match"]
    assert official_evidence(hits) == []
