"""Descarga el modelo de IA al construir la imagen (#38).
Downloads the AI model while building the image (#38).

ES: Lee ML_MODEL_URL y ML_MODEL_SHA256 del entorno (argumentos de build).
    Sin ML_MODEL_URL no hace nada: la API usará el clasificador por reglas.
    Si el SHA-256 no coincide, el build falla: nunca se usa un modelo alterado.
    Uso: python scripts/fetch_model.py <carpeta_destino>
EN: Reads ML_MODEL_URL and ML_MODEL_SHA256 from the environment (build args).
    Without ML_MODEL_URL it does nothing: the API uses the rule-based classifier.
    If the SHA-256 does not match, the build fails: a tampered model is never used.
    Usage: python scripts/fetch_model.py <target_folder>
"""

import hashlib
import io
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

REQUIRED_FILES = {"avizor_classifier.json", "model.int8.onnx", "tokenizer.json"}


def fetch(url: str, expected_sha256: str, target: Path) -> None:
    if not url.startswith("https://"):
        raise SystemExit("ML_MODEL_URL must use https://")
    if not expected_sha256:
        raise SystemExit("ML_MODEL_SHA256 is required when ML_MODEL_URL is set")
    with urllib.request.urlopen(url, timeout=300) as response:
        data = response.read()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256.strip().lower():
        raise SystemExit(f"Model checksum mismatch: got {actual}")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        missing = REQUIRED_FILES - set(archive.namelist())
        if missing:
            raise SystemExit(f"Model zip is missing: {sorted(missing)}")
        target.mkdir(parents=True, exist_ok=True)
        archive.extractall(target)
    print(f"Model ready in {target}: {sorted(p.name for p in target.iterdir())}")


def main() -> None:
    url = os.environ.get("ML_MODEL_URL", "").strip()
    if not url:
        print("ML_MODEL_URL not set: image without AI model (rule-based classifier).")
        return
    fetch(url, os.environ.get("ML_MODEL_SHA256", ""), Path(sys.argv[1]))


if __name__ == "__main__":
    main()
