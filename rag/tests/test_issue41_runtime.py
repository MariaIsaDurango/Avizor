"""Offline coverage of E5 adapter and ingestion CLI boundaries."""

import json
import math
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

from rag.src.ingestion import pipeline
from rag.src.vector_store.embeddings import DIMENSIONS, MODEL_ID, E5Embedder


@pytest.fixture
def e5_dependencies(monkeypatch, tmp_path):
    """Replace imports only inside tests; never download model weights."""
    snapshot = tmp_path / "revision-test"
    hub = ModuleType("huggingface_hub")
    hub.snapshot_download = Mock(return_value=str(snapshot))
    tokenizer = Mock()
    tokenizer.encode.side_effect = lambda text, **_: text.split() + [0, 1]
    transformers = ModuleType("transformers")
    transformers.AutoTokenizer = SimpleNamespace(
        from_pretrained=Mock(return_value=tokenizer)
    )
    model = Mock(spec=["get_embedding_dimension", "max_seq_length", "encode"])
    model.get_embedding_dimension.return_value = DIMENSIONS
    model.encode.return_value = SimpleNamespace(tolist=lambda: [[1.0] + [0.0] * 767])
    sentence = ModuleType("sentence_transformers")
    sentence.SentenceTransformer = Mock(return_value=model)
    for name, module in (
        ("huggingface_hub", hub),
        ("transformers", transformers),
        ("sentence_transformers", sentence),
    ):
        monkeypatch.setitem(sys.modules, name, module)
    return SimpleNamespace(
        hub=hub,
        transformers=transformers,
        sentence=sentence,
        model=model,
        tokenizer=tokenizer,
        snapshot=snapshot,
    )


def test_e5_initializes_local_cpu(e5_dependencies):
    deps = e5_dependencies
    embedder = E5Embedder("test-ref")
    deps.hub.snapshot_download.assert_called_once_with(
        MODEL_ID, revision="test-ref", local_files_only=True
    )
    deps.transformers.AutoTokenizer.from_pretrained.assert_called_once_with(
        str(deps.snapshot), use_fast=True, local_files_only=True
    )
    deps.sentence.SentenceTransformer.assert_called_once_with(
        str(deps.snapshot), device="cpu", local_files_only=True
    )
    assert embedder.revision == "revision-test"
    assert deps.model.max_seq_length == 512


def test_e5_legacy_dimension_api(e5_dependencies):
    legacy = Mock(spec=["get_sentence_embedding_dimension", "max_seq_length"])
    legacy.get_sentence_embedding_dimension.return_value = DIMENSIONS
    e5_dependencies.sentence.SentenceTransformer.return_value = legacy
    E5Embedder()
    legacy.get_sentence_embedding_dimension.assert_called_once_with()


def test_e5_wrong_dimension(e5_dependencies):
    e5_dependencies.model.get_embedding_dimension.return_value = 384
    with pytest.raises(ValueError, match="dimensions"):
        E5Embedder()


@pytest.mark.parametrize("query,prefix", [(False, "passage: "), (True, "query: ")])
def test_e5_prefix_and_encoding_options(e5_dependencies, query, prefix):
    embedder = E5Embedder()
    vectors = embedder.encode(["texto de prueba"], query=query)
    e5_dependencies.model.encode.assert_called_once_with(
        [prefix + "texto de prueba"],
        normalize_embeddings=True,
        batch_size=8,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    e5_dependencies.tokenizer.encode.assert_called_once_with(
        prefix + "texto de prueba",
        add_special_tokens=True,
        truncation=False,
        verbose=False,
    )
    assert len(vectors[0]) == DIMENSIONS
    assert math.isclose(sum(x * x for x in vectors[0]), 1.0)


def test_e5_empty_batch_does_not_encode(e5_dependencies):
    assert E5Embedder().encode([]) == []
    e5_dependencies.model.encode.assert_not_called()


@pytest.mark.parametrize(
    "kind,message",
    [
        ("short", "Invalid embedding"),
        ("nan", "Invalid embedding"),
        ("infinite", "Invalid embedding"),
        ("zero", "not L2 normalized"),
        ("large", "not L2 normalized"),
    ],
)
def test_e5_invalid_vectors(e5_dependencies, kind, message):
    vectors = {
        "short": [1.0],
        "nan": [math.nan] + [0.0] * 767,
        "infinite": [math.inf] + [0.0] * 767,
        "zero": [0.0] * 768,
        "large": [2.0] + [0.0] * 767,
    }
    e5_dependencies.model.encode.return_value = SimpleNamespace(
        tolist=lambda: [vectors[kind]]
    )
    with pytest.raises(ValueError, match=message):
        E5Embedder().encode(["texto"])


def test_e5_exact_input_limit(e5_dependencies):
    embedder = E5Embedder()
    assert embedder.encode(["palabra " * 509])
    with pytest.raises(ValueError, match="512"):
        embedder.encode(["palabra " * 510])
    assert e5_dependencies.model.encode.call_count == 1


@pytest.fixture
def cli(monkeypatch, tmp_path):
    embedder = Mock()
    embedder.revision = "test-revision"
    embedder.encode.return_value = [[1.0] + [0.0] * 767]
    store = Mock()
    store.query.return_value = {
        "metadatas": [[{"title": "[SINTÉTICO] prueba"}]],
        "distances": [[0.15]],
    }
    mocks = SimpleNamespace(
        embedder=Mock(return_value=embedder),
        store=Mock(return_value=store),
        ingest=Mock(return_value={"stored_chunks": 9}),
        chunker=Mock(),
    )
    monkeypatch.setattr(pipeline, "E5Embedder", mocks.embedder)
    monkeypatch.setattr(pipeline, "ChromaStore", mocks.store)
    monkeypatch.setattr(pipeline, "ingest", mocks.ingest)
    monkeypatch.setattr(pipeline, "TokenChunker", mocks.chunker)
    monkeypatch.setattr(pipeline, "DEMO_PATH", tmp_path / "demo")
    monkeypatch.setattr(pipeline, "OFFICIAL_PATH", tmp_path / "official")
    return mocks


def test_cli_synthetic_query(monkeypatch, cli, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["pipeline", "--synthetic", "--query", "SMS falso", "--revision", "ref"],
    )
    pipeline.main()
    output = capsys.readouterr().out
    report, _, result = output.partition("\nSYNTHETIC |")
    assert json.loads(report)["stored_chunks"] == 9
    assert json.loads(report)["mode"] == "synthetic"
    assert "distance=0.1500" in result
    cli.embedder.assert_called_once_with("ref")
    cli.store.assert_called_once_with(
        pipeline.DEMO_PATH, revision="test-revision", synthetic=True
    )
    cli.embedder.return_value.encode.assert_called_once_with(["SMS falso"], query=True)
    assert len(cli.ingest.call_args.args[0]) == 3


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--synthetic", "--approvals", "a.json"],
        ["--input", "a.json"],
        ["--approvals", "a.json"],
        ["--input", "a.json", "--approvals", "b.json", "--query", "test"],
    ],
)
def test_cli_rejects_invalid_modes(monkeypatch, cli, args):
    monkeypatch.setattr(sys, "argv", ["pipeline", *args])
    with pytest.raises(SystemExit) as error:
        pipeline.main()
    assert error.value.code == 2
    cli.embedder.assert_not_called()
    cli.store.assert_not_called()


def test_cli_official_requires_validated_input(monkeypatch, cli, tmp_path):
    snapshot = tmp_path / "invalid.json"
    snapshot.write_text("{}", encoding="utf-8")
    approvals = tmp_path / "approvals.json"
    approvals.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["pipeline", "--input", str(snapshot), "--approvals", str(approvals)],
    )
    with pytest.raises(TypeError, match="JSON list"):
        pipeline.main()
    cli.embedder.assert_not_called()
    cli.store.assert_not_called()


def test_cli_official_uses_separate_collection_path(monkeypatch, cli, tmp_path, capsys):
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text("[]", encoding="utf-8")
    approvals = tmp_path / "approvals.json"
    approvals.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["pipeline", "--input", str(snapshot), "--approvals", str(approvals)],
    )
    pipeline.main()
    assert json.loads(capsys.readouterr().out)["mode"] == "official"
    cli.store.assert_called_once_with(
        pipeline.OFFICIAL_PATH, revision="test-revision", synthetic=False
    )
    cli.store.return_value.query.assert_not_called()
