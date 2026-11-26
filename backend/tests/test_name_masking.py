"""Tests de nombres en el texto extraído por el servidor (#193).
Tests for names in server-extracted text (#193).

ES: Datos inventados. Los tests con spaCy se saltan si el modelo no está; en CI
    se instala con requirements.txt.
EN: Fake data. spaCy tests are skipped when the model is missing; CI installs
    it from requirements.txt.
"""

import importlib.util
import json

import pytest

from app.core.config import settings
from app.schemas.enums import InputType
from app.services import manual_analysis as manual_service
from app.services.detection import names
from app.services.detection.anonymize import anonymize
from app.services.detection.names import NAME, mask_names
from app.services.extraction import IMAGE_ENGINE

ANALYSES = "/api/v1/analyses"
needs_model = pytest.mark.skipif(
    importlib.util.find_spec(settings.AVIZOR_NER_MODEL) is None,
    reason="Modelo spaCy no instalado / spaCy model not installed",
)


def clean(text):
    return mask_names(anonymize(text))


# ---------- Con modelo / With model ----------


@needs_model
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hola Carmen, tu cuenta ha sido bloqueada.", "Hola [NAME], tu cuenta"),
        ("Estimado José Martínez García: Correos le informa", "Estimado [NAME]:"),
        ("Estimada María de la Fuente: su BBVA ha caducado", "Estimada [NAME]:"),
        ("Hola abuela, soy Lucas, hazme un Bizum", "soy [NAME],"),
        (
            "Receta: paciente María López. Dr. Antonio Pérez.",
            "paciente [NAME]. Dr. [NAME].",
        ),
    ],
)
def test_person_names_are_masked(text, expected):
    assert expected in clean(text)


@needs_model
@pytest.mark.parametrize(
    "text",
    [
        "Mamá soy yo, se me ha roto el móvil, escríbeme por WhatsApp",
        "BBVA: su cuenta ha sido bloqueada. Verifique en https://bbva-seguro.top/login",
        "Agencia Tributaria: tiene un reembolso pendiente.",
        "Estimado cliente: su cuenta ha sido bloqueada",
    ],
)
def test_scam_signals_are_kept(text):
    """ES: Familia, bancos, organismos y enlaces son señales: no se tapan.
    EN: Family words, banks, agencies and links are signals: not masked.
    """
    assert clean(text) == text


@needs_model
def test_names_and_regex_markers_together():
    text = "Titular: Carmen Ruiz DNI 12345678Z\nIBAN ES91 2100 0418 4502 0005 1332"
    assert clean(text) == "Titular: [NAME] DNI [ID_NUMBER]\nIBAN [IBAN]"


# ---------- Sin modelo / Without model ----------


@pytest.fixture
def no_model(monkeypatch):
    monkeypatch.setattr(settings, "AVIZOR_NER_MODEL", "")


def test_title_rule_works_without_model(no_model):
    assert mask_names("CaixaBank: Sr. PEDRO GOMEZ, hemos detectado") == (
        "CaixaBank: Sr. [NAME], hemos detectado"
    )
    assert mask_names("Titular: Carmen Ruiz DNI [ID_NUMBER]") == (
        "Titular: [NAME] DNI [ID_NUMBER]"
    )


def test_title_rule_skips_family_words(no_model):
    assert mask_names("Querida Mamá: soy yo") == "Querida Mamá: soy yo"


def test_missing_model_is_not_an_error(monkeypatch):
    monkeypatch.setattr(settings, "AVIZOR_NER_MODEL", "modelo_que_no_existe")
    monkeypatch.setattr(names, "_loaded_name", None)
    assert mask_names("Hola Carmen") == "Hola Carmen"


# ---------- Endpoint multipart / Multipart endpoint ----------


@pytest.fixture
def jobs(monkeypatch):
    calls: list[manual_service.ManualJob] = []
    monkeypatch.setattr(manual_service, "run_manual_job", calls.append)
    return calls


def test_extracted_text_has_no_names(api_client, paired_senior, jobs, monkeypatch):
    monkeypatch.setitem(
        manual_service.SERVER_EXTRACTORS,
        InputType.IMAGE,
        (
            lambda _data: "Sr. PEDRO GOMEZ, su cuenta ES9121000418450200051332",
            IMAGE_ENGINE,
        ),
    )
    data = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    meta = {
        "device_id": str(paired_senior.device.id),
        "received_at": "2026-11-26T10:00:00Z",
        "anonymization": {"applied": True, "ner_model_version": "regex-v0"},
        "attachments": [
            {
                "file_field": "attachment_0",
                "type": "image",
                "mime": "image/png",
                "size_bytes": len(data),
            }
        ],
    }
    parts = {
        "metadata": (None, json.dumps(meta), "application/json"),
        "attachment_0": ("captura.png", data, "image/png"),
    }
    response = api_client.post(ANALYSES, files=parts, headers=paired_senior.headers)
    assert response.status_code == 202
    text = jobs[0].text
    assert NAME in text and "[IBAN]" in text
    assert "PEDRO" not in text and "GOMEZ" not in text
