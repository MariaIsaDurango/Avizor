"""Configuration regression tests; no model, network or real corpus required."""

import json
import sys
from unittest.mock import Mock

import pytest

from rag.src.ingestion import pipeline


@pytest.fixture
def root(monkeypatch, tmp_path):
    monkeypatch.delenv("CHROMA_PATH", raising=False)
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(pipeline, "OFFICIAL_PATH", tmp_path / "rag/chroma_db")
    monkeypatch.setattr(pipeline, "DEMO_PATH", tmp_path / "rag/data/demo")
    return tmp_path


def test_default_path(root):
    assert pipeline.resolve_official_path() == root / "rag/chroma_db"


def test_relative_environment_path(root, monkeypatch, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    monkeypatch.setenv("CHROMA_PATH", "./custom/index")
    assert pipeline.resolve_official_path() == root / "custom/index"


def test_absolute_environment_path(root, monkeypatch):
    path = root / "external"
    monkeypatch.setenv("CHROMA_PATH", str(path))
    assert pipeline.resolve_official_path() == path


def test_root_dotenv_path(root, monkeypatch):
    (root / ".env").write_text("CHROMA_PATH=./dotenv/index\n", encoding="utf-8")
    monkeypatch.chdir(root.parent)
    assert pipeline.resolve_official_path() == root / "dotenv/index"


def test_environment_overrides_dotenv(root, monkeypatch):
    (root / ".env").write_text("CHROMA_PATH=./dotenv/index\n", encoding="utf-8")
    monkeypatch.setenv("CHROMA_PATH", "./env/index")
    assert pipeline.resolve_official_path() == root / "env/index"


def test_env_example_is_not_configuration(root):
    (root / ".env.example").write_text("CHROMA_PATH=./example\n", encoding="utf-8")
    assert pipeline.resolve_official_path() == root / "rag/chroma_db"


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_path_rejected(root, monkeypatch, value):
    monkeypatch.setenv("CHROMA_PATH", value)
    with pytest.raises(ValueError, match="must not be empty"):
        pipeline.resolve_official_path()


@pytest.mark.parametrize("value", ["rag/data/demo", "rag/data/demo/child", "rag/data"])
def test_overlapping_paths_rejected(root, monkeypatch, value):
    monkeypatch.setenv("CHROMA_PATH", value)
    with pytest.raises(ValueError, match="separate"):
        pipeline.resolve_official_path()


def test_symlink_to_demo_rejected(root, monkeypatch):
    pipeline.DEMO_PATH.mkdir(parents=True)
    alias = root / "alias"
    alias.symlink_to(pipeline.DEMO_PATH, target_is_directory=True)
    monkeypatch.setenv("CHROMA_PATH", str(alias))
    with pytest.raises(ValueError, match="separate"):
        pipeline.resolve_official_path()


@pytest.mark.parametrize("synthetic", [False, True])
def test_cli_uses_correct_path(root, monkeypatch, capsys, synthetic):
    custom = root / "custom"
    monkeypatch.setenv("CHROMA_PATH", str(custom))
    snapshot = root / "snapshot.json"
    snapshot.write_text("[]", encoding="utf-8")
    approvals = root / "approvals.json"
    approvals.write_text("{}", encoding="utf-8")
    args = ["pipeline", "--input", str(snapshot)]
    args += ["--synthetic"] if synthetic else ["--approvals", str(approvals)]
    monkeypatch.setattr(sys, "argv", args)
    embedder = Mock(revision="test-revision")
    store = Mock()
    monkeypatch.setattr(pipeline, "E5Embedder", Mock(return_value=embedder))
    factory = Mock(return_value=store)
    monkeypatch.setattr(pipeline, "ChromaStore", factory)
    monkeypatch.setattr(pipeline, "TokenChunker", Mock())
    monkeypatch.setattr(pipeline, "ingest", Mock(return_value={"stored_chunks": 0}))
    pipeline.main()
    expected = pipeline.DEMO_PATH if synthetic else custom
    factory.assert_called_once_with(
        expected, revision="test-revision", synthetic=synthetic
    )
    assert json.loads(capsys.readouterr().out)["database"] == str(expected)


def test_cli_rejects_collision_before_loading_model(root, monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", str(pipeline.DEMO_PATH))
    approvals = root / "approvals.json"
    approvals.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["pipeline", "--input", "absent.json", "--approvals", str(approvals)],
    )
    model = Mock()
    store = Mock()
    monkeypatch.setattr(pipeline, "E5Embedder", model)
    monkeypatch.setattr(pipeline, "ChromaStore", store)
    with pytest.raises(SystemExit) as exc:
        pipeline.main()
    assert exc.value.code == 2
    model.assert_not_called()
    store.assert_not_called()
