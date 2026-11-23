"""Descarga del modelo en el build (#38). Model download at build time (#38)."""

import hashlib
import importlib.util
import io
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fetch_model.py"
spec = importlib.util.spec_from_file_location("fetch_model", SCRIPT)
fetch_model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_model)


def make_zip(names) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, "{}")
    return buffer.getvalue()


@pytest.fixture
def serve(monkeypatch):
    def _serve(data: bytes):
        monkeypatch.setattr(
            fetch_model.urllib.request, "urlopen", lambda *_a, **_k: io.BytesIO(data)
        )
        return hashlib.sha256(data).hexdigest()

    return _serve


def test_without_url_does_nothing(monkeypatch, tmp_path):
    monkeypatch.delenv("ML_MODEL_URL", raising=False)
    monkeypatch.setattr("sys.argv", ["fetch_model.py", str(tmp_path / "model")])
    fetch_model.main()
    assert not (tmp_path / "model").exists()


def test_valid_zip_is_extracted(serve, tmp_path):
    sha = serve(make_zip(fetch_model.REQUIRED_FILES))
    fetch_model.fetch("https://example.org/model.zip", sha, tmp_path)
    assert {p.name for p in tmp_path.iterdir()} == fetch_model.REQUIRED_FILES


def test_wrong_checksum_fails(serve, tmp_path):
    serve(make_zip(fetch_model.REQUIRED_FILES))
    with pytest.raises(SystemExit, match="checksum"):
        fetch_model.fetch("https://example.org/model.zip", "0" * 64, tmp_path)
    assert not any(tmp_path.iterdir())


def test_incomplete_zip_fails(serve, tmp_path):
    sha = serve(make_zip(["tokenizer.json"]))
    with pytest.raises(SystemExit, match="missing"):
        fetch_model.fetch("https://example.org/model.zip", sha, tmp_path)


@pytest.mark.parametrize("url", ["http://example.org/m.zip", "file:///etc/passwd"])
def test_only_https_is_allowed(url, tmp_path):
    with pytest.raises(SystemExit, match="https"):
        fetch_model.fetch(url, "0" * 64, tmp_path)
