"""Tests de extracción de texto de PDF adjuntos (#164).
PDF attachment text extraction tests (#164).

ES: Los PDF se generan aquí a mano (sin dependencias extra). Datos inventados.
EN: PDFs are built here by hand (no extra dependencies). Fake data.
"""

import importlib.util
import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.analysis import AnalysisAttachment
from app.services import manual_analysis as manual_service
from app.services.detection import anonymize as server_anonymize
from app.services.extraction import (
    MAX_TEXT_CHARS,
    PDF_ENGINE,
    extract_pdf_text,
    is_pdf,
)
from app.services.manual_analysis import finish_manual_analysis

ANALYSES = "/api/v1/analyses"
SCAM_PDF_LINES = [
    "Factura pendiente de pago",
    "Pague hoy en ES9121000418450200051332",
    "o llame al 612 345 678",
    "https://pago-facturas.top/abonar",
]


def make_pdf(lines: list[str]) -> bytes:
    """ES: PDF mínimo válido con una página de texto (Helvetica).
    EN: Minimal valid PDF with one text page (Helvetica).
    """
    ops = ["BT", "/F1 12 Tf", "14 TL", "50 750 Td"]
    for line in lines:
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        ops.append(f"({safe}) Tj T*")
    ops.append("ET")
    stream = "\n".join(ops).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    out += b"startxref\n%d\n%%%%EOF\n" % xref
    return bytes(out)


# ---------- Extracción / Extraction ----------


def test_extracts_pdf_text():
    text = extract_pdf_text(make_pdf(SCAM_PDF_LINES))
    for line in SCAM_PDF_LINES:
        assert line in text


def test_detects_real_pdf_signature():
    assert is_pdf(make_pdf(["Hola"]))
    assert not is_pdf(b"\xff\xd8\xff" + b"0" * 100)  # JPEG with pdf mime


def test_broken_pdf_returns_empty():
    assert extract_pdf_text(b"%PDF-1.4\nesto no es un pdf") == ""


def test_text_is_capped():
    text = extract_pdf_text(make_pdf(["x" * 90] * 60 + ["y" * 90] * 60))
    assert len(text) <= MAX_TEXT_CHARS


# ---------- Anonimización / Anonymization ----------


def test_server_anonymizer_replaces_personal_data():
    text = server_anonymize.anonymize("\n".join(SCAM_PDF_LINES))
    assert "[IBAN]" in text and "[PHONE]" in text
    assert "ES9121000418450200051332" not in text
    assert "612 345 678" not in text
    # ES/EN: links are kept (useful signal, same as the phone)
    assert "https://pago-facturas.top/abonar" in text


def test_server_anonymizer_matches_ml_copy():
    """ES: Mismas reglas que ml/src/classifier/anonymize.py (paridad con el móvil).
    EN: Same rules as the ML copy (parity with the phone).
    """
    path = Path(__file__).resolve().parents[2] / "ml/src/classifier/anonymize.py"
    if not path.exists():
        pytest.skip("ml/ no está en este entorno / ml/ not available")
    spec = importlib.util.spec_from_file_location("ml_anonymize", path)
    ml = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ml)
    assert [(t, p.pattern, p.flags) for t, p in server_anonymize.RULES] == [
        (t, p.pattern, p.flags) for t, p in ml.RULES
    ]
    assert server_anonymize.NER_MODEL_VERSION == ml.NER_MODEL_VERSION


# ---------- Endpoint multipart / Multipart endpoint ----------


@pytest.fixture
def jobs(monkeypatch):
    calls: list[manual_service.ManualJob] = []
    monkeypatch.setattr(manual_service, "run_manual_job", calls.append)
    return calls


def send_pdf(client, senior, data, text=None, local=None):
    meta = {
        "device_id": str(senior.device.id),
        "received_at": "2026-11-26T10:00:00Z",
        "text": text,
        "anonymization": {"applied": True, "ner_model_version": "regex-v0"},
        "attachments": [
            {
                "file_field": "attachment_0",
                "type": "document",
                "mime": "application/pdf",
                "size_bytes": len(data),
                "local_preprocessing": local,
            }
        ],
    }
    parts = {
        "metadata": (None, json.dumps(meta), "application/json"),
        "attachment_0": ("factura.pdf", data, "application/pdf"),
    }
    return client.post(ANALYSES, files=parts, headers=senior.headers)


def test_pdf_text_is_extracted_anonymized_and_analyzed(
    api_client, db_session, paired_senior, jobs
):
    response = send_pdf(api_client, paired_senior, make_pdf(SCAM_PDF_LINES))
    assert response.status_code == 202
    job = jobs[0]
    # ES/EN: the agent and classifier only get anonymized text
    assert "Factura pendiente de pago" in job.text
    assert "[IBAN]" in job.text and "[PHONE]" in job.text
    assert "ES9121000418450200051332" not in job.text
    assert "https://pago-facturas.top/abonar" in job.urls

    row = db_session.scalars(
        select(AnalysisAttachment).where(
            AnalysisAttachment.analysis_id == uuid.UUID(response.json()["analysis_id"])
        )
    ).one()
    assert row.extraction_engine == PDF_ENGINE
    assert row.ner_applied_on == "server"


def test_pdf_text_is_joined_with_body(api_client, paired_senior, jobs):
    send_pdf(api_client, paired_senior, make_pdf(["Adjunto la factura"]), text="Hola")
    assert jobs[0].text.startswith("Hola")
    assert "Adjunto la factura" in jobs[0].text


def test_scam_pdf_gets_risky_verdict(api_client, db_session, paired_senior, jobs):
    response = send_pdf(api_client, paired_senior, make_pdf(SCAM_PDF_LINES))
    finish_manual_analysis(db_session, jobs[0])
    verdict = api_client.get(
        f"{ANALYSES}/{response.json()['analysis_id']}/verdict",
        headers=paired_senior.headers,
    ).json()
    assert verdict["risk_level"] in ("amber", "red")


def test_fake_pdf_is_rejected(api_client, paired_senior, jobs):
    response = send_pdf(api_client, paired_senior, b"\xff\xd8\xff" + b"0" * 100)
    assert response.status_code == 422
    assert jobs == []


def test_device_text_wins_over_server_extraction(api_client, paired_senior, jobs):
    """ES: Si el móvil ya extrajo y anonimizó, el servidor no lee el PDF.
    EN: If the phone already extracted and anonymized, the server skips the PDF.
    """
    local = {"ocr": False, "extracted_text": "Texto del móvil", "ner_applied": True}
    send_pdf(api_client, paired_senior, make_pdf(SCAM_PDF_LINES), local=local)
    assert jobs[0].text == "Texto del móvil"
