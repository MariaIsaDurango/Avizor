"""Offline unit and adapter integration tests, with optional real Chroma/E5."""

import itertools
import json
from datetime import date
from types import SimpleNamespace

import pytest

from rag.src.ingestion.chunker import TokenChunker
from rag.src.ingestion.cleaner import clean_text, content_hash
from rag.src.ingestion.models import Notice, official_url
from rag.src.ingestion.pipeline import SAMPLE, ingest, load_notices
from rag.src.vector_store.chroma_store import ChromaStore
from rag.src.vector_store.embeddings import E5Embedder

TODAY = date(2026, 11, 17)


class WordTokenizer:
    """Deterministic fake, not a substitute for E5 tokenizer verification."""

    def __call__(self, text, **kwargs):
        import re

        return {"offset_mapping": [m.span() for m in re.finditer(r"\S+", text)]}

    def encode(self, text, *, add_special_tokens, **kwargs):
        return list(range(len(text.split()) + (2 if add_special_tokens else 0)))


class FakeEmbedder:
    def encode(self, texts, **kwargs):
        return [[1.0] + [0.0] * 767 for _ in texts]


class MemoryCollection:
    def __init__(self):
        self.rows = {}

    def get(self, *, where, include):
        key, value = next(iter(where.items()))
        matches = {i: r for i, r in self.rows.items() if r["metadata"][key] == value}
        return {
            "ids": list(matches),
            "metadatas": [r["metadata"] for r in matches.values()],
        }

    def upsert(self, *, ids, documents, embeddings, metadatas):
        for i, d, e, m in zip(ids, documents, embeddings, metadatas, strict=True):
            self.rows[i] = {"document": d, "embedding": e, "metadata": m}

    def delete(self, *, ids):
        for item in ids:
            self.rows.pop(item)

    def count(self):
        return len(self.rows)


def memory_store():
    store = ChromaStore.__new__(ChromaStore)
    store.synthetic = True
    store.collection = MemoryCollection()
    return store


def raw_record(text="texto sintético", *, url="https://example.invalid/a"):
    return {
        "source": "incibe",
        "url": url,
        "title": "[SINTÉTICO] aviso",
        "published_at": "2026-11-17",
        "scraped_at": "2026-11-17T00:00:00Z",
        "text": text,
        "content_hash": content_hash(text),
        "synthetic": True,
        "threat_type": "smishing",
        "impersonated_entities": "Entidad ficticia",
    }


def notice(text="texto sintético", **kwargs):
    return Notice.from_record(raw_record(text, **kwargs), today=TODAY, synthetic=True)


def long_text(n):
    return " ".join(f"palabra{i}" for i in range(n))


def test_clean_html():
    assert (
        clean_text(
            "<nav>menú</nav><p> cafe\u0301  válido </p><script>x</script>", is_html=True
        )
        == "café válido"
    )


def test_clean_plain_does_not_parse_markup():
    assert clean_text("importe < 100  euros") == "importe < 100 euros"


def test_hash_matches_whitespace_nfc():
    assert content_hash(" cafe\u0301 ") == content_hash("café")


@pytest.mark.parametrize(
    "n,expected", [(20, 1), (480, 1), (481, 2), (880, 2), (881, 3), (1600, 4)]
)
def test_chunk_lengths_and_overlap(n, expected):
    chunks = TokenChunker(WordTokenizer()).split(long_text(n))
    assert len(chunks) == expected
    assert chunks[0].start == 0
    assert chunks[-1].end == n
    assert all(450 <= c.token_count <= 480 for c in chunks[:-1])
    assert all(c.input_token_count <= 512 for c in chunks)
    for a, b in itertools.pairwise(chunks):
        assert a.end - b.start == 80
        assert a.text.split()[-80:] == b.text.split()[:80]


def test_empty_and_invalid_parameters():
    assert TokenChunker(WordTokenizer()).split(" ") == []
    with pytest.raises(ValueError, match="Invalid chunk"):
        TokenChunker(WordTokenizer(), overlap=480)


def test_reject_corrupted_snapshot():
    record = raw_record()
    record["text"] += " alterado"
    with pytest.raises(ValueError, match="hash mismatch"):
        Notice.from_record(record, today=TODAY, synthetic=True)


@pytest.mark.parametrize("published", ["2024-11-16", "2026-11-18"])
def test_reject_outside_window(published):
    record = raw_record()
    record["published_at"] = published
    with pytest.raises(ValueError, match="24-month"):
        Notice.from_record(record, today=TODAY, synthetic=True)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.incibe.es/ciudadania/avisos/test",
        "https://www.incibe.es.evil.invalid/ciudadania/avisos/test",
        "https://www.incibe.es/ciudadania/avisos/%2e%2e",
        "https://www.incibe.es@evil.invalid/ciudadania/avisos/test",
    ],
)
def test_reject_noncanonical_url(url):
    assert not official_url("incibe", url)


def test_require_approval_for_exact_hash():
    record = raw_record(url="https://www.incibe.es/ciudadania/avisos/test")
    record.update(synthetic=False, reuse_reference="Test only")
    with pytest.raises(ValueError, match="Missing approval"):
        Notice.from_record(record, today=TODAY, synthetic=False)
    approval = {
        "content_hash": record["content_hash"],
        "rag_allowed": True,
        "reference": "Synthetic unit test only",
        "threat_type": "smishing",
    }
    result = Notice.from_record(record, today=TODAY, synthetic=False, approval=approval)
    assert result.threat_type == "smishing"
    approval["rag_allowed"] = False
    with pytest.raises(ValueError, match="permission"):
        Notice.from_record(record, today=TODAY, synthetic=False, approval=approval)


def test_synthetic_cannot_enter_official_mode():
    with pytest.raises(ValueError, match="Non-official"):
        Notice.from_record(raw_record(), today=TODAY, synthetic=False)


def test_sample_load():
    rows = load_notices([SAMPLE], synthetic=True, approvals={}, today=TODAY)
    assert len(rows) == 3
    assert all(row.synthetic for row in rows)


def test_pipeline_idempotent_update_and_stale_chunks():
    store = memory_store()
    chunker = TokenChunker(WordTokenizer())
    original = notice(long_text(1200))
    first = ingest([original], chunker, FakeEmbedder(), store)
    second = ingest([original], chunker, FakeEmbedder(), store)
    assert first["inserted"] == second["updated"] == 1
    assert first["stored_chunks"] == second["stored_chunks"] == 3
    updated = ingest([notice("texto nuevo")], chunker, FakeEmbedder(), store)
    assert updated["stored_chunks"] == 1
    assert list(store.collection.rows) == [original.chunk_id(0)]
    assert store.collection.rows[original.chunk_id(0)]["document"] == "texto nuevo"


def test_duplicate_body_across_urls():
    store = memory_store()
    report = ingest(
        [notice(), notice(url="https://example.invalid/b")],
        TokenChunker(WordTokenizer()),
        FakeEmbedder(),
        store,
    )
    assert report["duplicate"] == 1
    assert report["stored_chunks"] == 1


def test_snapshot_conflicting_versions(tmp_path):
    path = tmp_path / "sample.json"
    path.write_text(json.dumps([raw_record(), raw_record("changed")]), encoding="utf-8")
    with pytest.raises(ValueError, match="Conflicting versions"):
        load_notices([path], synthetic=True, approvals={}, today=TODAY)


def test_e5_rejects_overlength_before_encoding():
    model = E5Embedder.__new__(E5Embedder)
    model.tokenizer = WordTokenizer()
    model.model = SimpleNamespace()
    with pytest.raises(ValueError, match="512"):
        model.encode([long_text(512)])


def test_actual_chroma_persistence(tmp_path):
    pytest.importorskip("chromadb")
    store = ChromaStore(tmp_path / "chroma", revision="test-fake", synthetic=True)
    chunker = TokenChunker(WordTokenizer())
    first = ingest([notice(long_text(900))], chunker, FakeEmbedder(), store)
    reopened = ChromaStore(tmp_path / "chroma", revision="test-fake", synthetic=True)
    second = ingest([notice("texto actualizado")], chunker, FakeEmbedder(), reopened)
    assert first["stored_chunks"] == 3
    assert second["stored_chunks"] == 1
    assert (
        reopened.query([1.0] + [0.0] * 767)["metadatas"][0][0]["threat_type"]
        == "smishing"
    )
    with pytest.raises(ValueError, match="configuration differs"):
        ChromaStore(tmp_path / "chroma", revision="different", synthetic=True)


def test_actual_e5_tokenizer_cached():
    hub = pytest.importorskip("huggingface_hub")
    transformers = pytest.importorskip("transformers")
    try:
        path = hub.snapshot_download(
            "intfloat/multilingual-e5-base", local_files_only=True
        )
    except hub.errors.LocalEntryNotFoundError:
        pytest.skip("E5 not cached")
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        path, use_fast=True, local_files_only=True
    )
    rows = load_notices([SAMPLE], synthetic=True, approvals={}, today=TODAY)
    for row in rows:
        chunks = TokenChunker(tokenizer).split(row.text)
        assert all(c.input_token_count <= 512 for c in chunks)
        assert all(450 <= c.token_count <= 480 for c in chunks[:-1])
        assert all(a.end - b.start == 80 for a, b in itertools.pairwise(chunks))
