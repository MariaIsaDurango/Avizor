"""Tests del OCR de imágenes en el servidor (#192).
Server-side image OCR tests (#192).

ES: tests/fixtures/ocr_scam.png es una captura inventada (datos falsos). Los
    tests con Tesseract real se saltan si no está instalado; en CI sí está.
EN: tests/fixtures/ocr_scam.png is a made-up screenshot (fake data). Tests with
    real Tesseract are skipped when it is not installed; CI installs it.
"""

import json
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.alert import Alert
from app.models.analysis import AnalysisAttachment
from app.schemas.enums import InputType
from app.services import extraction
from app.services import manual_analysis as manual_service
from app.services.extraction import IMAGE_ENGINE, extract_image_text, is_image
from app.services.manual_analysis import finish_manual_analysis

ANALYSES = "/api/v1/analyses"
SCAM_PNG = (Path(__file__).parent / "fixtures" / "ocr_scam.png").read_bytes()
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
needs_tesseract = pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="Tesseract no está instalado / Tesseract is not installed",
)


@pytest.fixture
def jobs(monkeypatch):
    calls: list[manual_service.ManualJob] = []
    monkeypatch.setattr(manual_service, "run_manual_job", calls.append)
    return calls


@pytest.fixture
def fake_ocr(monkeypatch):
    """ES: OCR simulado, para no depender de Tesseract.
    EN: Simulated OCR, so the test does not depend on Tesseract.
    """

    def use(text: str) -> None:
        monkeypatch.setitem(
            manual_service.SERVER_EXTRACTORS,
            InputType.IMAGE,
            (lambda _data: text, IMAGE_ENGINE),
        )

    return use


def send_image(client, senior, data=SCAM_PNG, text=None, mime="image/png"):
    meta = {
        "device_id": str(senior.device.id),
        "received_at": "2026-11-26T10:00:00Z",
        "text": text,
        "anonymization": {"applied": True, "ner_model_version": "regex-v0"},
        "attachments": [
            {
                "file_field": "attachment_0",
                "type": "image",
                "mime": mime,
                "size_bytes": len(data),
            }
        ],
    }
    parts = {
        "metadata": (None, json.dumps(meta), "application/json"),
        "attachment_0": ("captura.png", data, mime),
    }
    return client.post(ANALYSES, files=parts, headers=senior.headers)


def verdict_of(client, senior, response):
    return client.get(
        f"{ANALYSES}/{response.json()['analysis_id']}/verdict",
        headers=senior.headers,
    ).json()


# ---------- extraction.py ----------


def test_detects_real_image_signatures():
    assert is_image(SCAM_PNG)
    assert is_image(b"\xff\xd8\xff\xe0" + b"0" * 20)  # JPEG
    assert is_image(b"RIFF\x00\x00\x00\x00WEBPVP8 ")  # WebP
    assert is_image(b"\x00\x00\x00\x18ftypheic")  # HEIC
    assert not is_image(b"%PDF-1.4\n")
    assert not is_image(b"<html>no es una imagen</html>")


@needs_tesseract
def test_tesseract_reads_the_screenshot():
    text = extract_image_text(SCAM_PNG)
    assert "bloqueada" in text
    assert "banco-seguro.top/login" in text


def test_missing_tesseract_returns_empty(monkeypatch):
    monkeypatch.setattr(extraction.shutil, "which", lambda _name: None)
    assert extract_image_text(SCAM_PNG) == ""


def test_slow_ocr_returns_empty(monkeypatch):
    def slow(*_args, **kwargs):
        raise subprocess.TimeoutExpired("tesseract", kwargs["timeout"])

    monkeypatch.setattr(extraction.shutil, "which", lambda _name: "/bin/tesseract")
    monkeypatch.setattr(extraction.subprocess, "run", slow)
    assert extract_image_text(SCAM_PNG) == ""


def test_unreadable_format_returns_empty(monkeypatch):
    failed = subprocess.CompletedProcess([], 1, stdout=b"", stderr=b"error")
    monkeypatch.setattr(extraction.shutil, "which", lambda _name: "/bin/tesseract")
    monkeypatch.setattr(extraction.subprocess, "run", lambda *_a, **_k: failed)
    assert extract_image_text(b"\x00\x00\x00\x18ftypheic") == ""


def test_ocr_uses_stdin_and_stdout_only(monkeypatch):
    """ES: La imagen va por stdin y el texto vuelve por stdout: nada a disco.
    EN: The image goes through stdin and the text comes back on stdout.
    """
    seen = {}

    def run(args, **kwargs):
        seen.update(args=args, input=kwargs["input"])
        return subprocess.CompletedProcess(args, 0, stdout=b"Hola\n\n\n\nadios")

    monkeypatch.setattr(extraction.shutil, "which", lambda _name: "/bin/tesseract")
    monkeypatch.setattr(extraction.subprocess, "run", run)
    assert extract_image_text(SCAM_PNG) == "Hola\n\nadios"
    assert seen["args"][1:3] == ["stdin", "stdout"]
    assert seen["input"] == SCAM_PNG


# ---------- Endpoint multipart / Multipart endpoint ----------


def test_image_text_is_extracted_anonymized_and_analyzed(
    api_client, db_session, paired_senior, jobs, fake_ocr
):
    fake_ocr("Su IBAN ES9121000418450200051332 está bloqueado. https://pago.top/x")
    response = send_image(api_client, paired_senior)
    assert response.status_code == 202
    job = jobs[0]
    # ES/EN: the agent and classifier only get anonymized text
    assert "[IBAN]" in job.text
    assert "ES9121000418450200051332" not in job.text
    assert "https://pago.top/x" in job.urls

    row = db_session.scalars(
        select(AnalysisAttachment).where(
            AnalysisAttachment.analysis_id == uuid.UUID(response.json()["analysis_id"])
        )
    ).one()
    assert row.extraction_engine == IMAGE_ENGINE
    assert row.ner_applied_on == "server"


@needs_tesseract
def test_real_scam_screenshot_is_not_green(api_client, db_session, paired_senior, jobs):
    response = send_image(api_client, paired_senior)
    job = jobs[0]
    assert "[ID_NUMBER]" in job.text and "[IBAN]" in job.text
    assert "12345678Z" not in job.text
    finish_manual_analysis(db_session, job)
    assert verdict_of(api_client, paired_senior, response)["risk_level"] in (
        "amber",
        "red",
    )


def test_fake_image_is_rejected(api_client, paired_senior, jobs):
    response = send_image(api_client, paired_senior, data=b"%PDF-1.4\n" + b"0" * 100)
    assert response.status_code == 422
    assert jobs == []


def test_unreadable_image_is_amber_not_safe(
    api_client, db_session, paired_senior, jobs, fake_ocr, monkeypatch
):
    """ES: Si no se pudo leer nada no decimos "seguro" y no se llama al agente.
    EN: If nothing could be read we do not say "safe" and skip the agent.
    """
    fake_ocr("")
    monkeypatch.setattr(
        manual_service,
        "run_agent",
        lambda *_a, **_k: pytest.fail("the agent must not run without text"),
    )
    response = send_image(api_client, paired_senior)
    finish_manual_analysis(db_session, jobs[0])
    verdict = verdict_of(api_client, paired_senior, response)
    assert verdict["risk_level"] == "amber"
    assert verdict["block_template"] == "UNSURE_CALL_FAMILY"
    assert verdict["confidence"] == manual_service.UNREADABLE_CONFIDENCE
    # ES/EN: amber never alerts the guardian
    assert db_session.scalars(select(Alert)).all() == []


def test_unreadable_image_with_body_uses_the_body(
    api_client, db_session, paired_senior, jobs, fake_ocr
):
    fake_ocr("")
    send_image(api_client, paired_senior, text="Hola, ¿comemos el domingo?")
    assert jobs[0].text == "Hola, ¿comemos el domingo?"
    assert jobs[0].fast.confidence != manual_service.UNREADABLE_CONFIDENCE
