"""Tests de AnalysisRequest, ManualAnalysisMetadata y Verdict.
Tests for AnalysisRequest, ManualAnalysisMetadata and Verdict.
"""

import pytest
from pydantic import ValidationError

from app.schemas.analysis import AnalysisRequest, ManualAnalysisMetadata
from app.schemas.verdict import Verdict

DEVICE_ID = "c7e1a9b2-4d3f-4a8e-9b1c-0f2e3d4a5b6c"
ANALYSIS_ID = "a4b8c2d1-6e3f-4c9a-8b7d-1e2f3a4b5c6d"
ANONYMIZATION = {
    "applied": True,
    "ner_model_version": "ner-es-mobile-0.3.1",
    "redacted_entities": ["IBAN"],
}

# ES: Ejemplos copiados del contrato. EN: Examples copied from the contract.
SMS_REQUEST = {
    "device_id": DEVICE_ID,
    "channel": "sms",
    "origin": "automatic",
    "input_type": "text",
    "received_at": "2026-11-04T13:12:05Z",
    "sender": {"type": "phone", "value": "+34612345612", "masked": "+34 6** *** 12"},
    "content": {
        "text": "BBVA: su cuenta [IBAN] ha sido bloqueada.",
        "urls": ["https://bbva-seguro.top/login"],
        "language": "es",
        "anonymization": ANONYMIZATION,
        "server_processed": False,
    },
    "app": {"version": "0.4.0", "android_api": 34},
}

PHONE_LOOKUP = {
    "device_id": DEVICE_ID,
    "channel": "call",
    "origin": "manual",
    "input_type": "phone_number",
    "received_at": "2026-11-04T13:41:00Z",
    "sender": {"type": "phone", "value": "+34912345645"},
}

MANUAL_METADATA = {
    "device_id": DEVICE_ID,
    "received_at": "2026-11-04T13:30:00Z",
    "text": "Me han mandado esto, ¿es verdad?",
    "anonymization": ANONYMIZATION,
    "attachments": [
        {
            "file_field": "attachment_0",
            "type": "image",
            "mime": "image/jpeg",
            "size_bytes": 834221,
            "local_preprocessing": {
                "ocr": True,
                "extracted_text": "Correos: su paquete está retenido.",
                "ner_applied": True,
            },
        },
        {
            "file_field": "attachment_1",
            "type": "audio",
            "mime": "audio/ogg",
            "size_bytes": 612004,
            "duration_s": 42,
            "local_preprocessing": None,
        },
    ],
}

VERDICT_RED = {
    "analysis_id": ANALYSIS_ID,
    "phase": "fast",
    "risk_level": "red",
    "threat_type": "smishing",
    "action": "block_and_alert",
    "block_template": "FAKE_DO_NOT_TOUCH",
    "confidence": 0.97,
    "final": True,
    "retry_after_ms": None,
    "issued_at": "2026-11-04T13:12:05Z",
}


# ---------- AnalysisRequest ----------


def test_sms_contract_example_is_valid():
    assert AnalysisRequest.model_validate(SMS_REQUEST).content is not None


def test_phone_lookup_contract_example_is_valid():
    assert AnalysisRequest.model_validate(PHONE_LOOKUP).content is None


def test_text_over_5000_chars_fails():
    data = {**SMS_REQUEST, "content": {**SMS_REQUEST["content"], "text": "a" * 5001}}
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(data)


def test_more_than_10_urls_fails():
    urls = [f"https://example{i}.com" for i in range(11)]
    data = {**SMS_REQUEST, "content": {**SMS_REQUEST["content"], "urls": urls}}
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(data)


def test_unknown_redaction_tag_fails():
    anonymization = {**ANONYMIZATION, "redacted_entities": ["PASSWORD"]}
    content = {**SMS_REQUEST["content"], "anonymization": anonymization}
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate({**SMS_REQUEST, "content": content})


def test_image_not_allowed_in_json_request():
    """ES: Los archivos van por multipart. EN: Files go through multipart."""
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate({**SMS_REQUEST, "input_type": "image"})


def test_text_request_without_content_fails():
    data = {k: v for k, v in SMS_REQUEST.items() if k != "content"}
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(data)


def test_phone_lookup_requires_e164():
    data = {**PHONE_LOOKUP, "sender": {"type": "phone", "value": "912345645"}}
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(data)


def test_call_channel_only_accepts_phone_number():
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate({**SMS_REQUEST, "channel": "call"})


# ---------- ManualAnalysisMetadata ----------


def test_manual_contract_example_is_valid():
    metadata = ManualAnalysisMetadata.model_validate(MANUAL_METADATA)
    assert len(metadata.attachments) == 2


def test_more_than_5_attachments_fails():
    attachment = MANUAL_METADATA["attachments"][1]
    attachments = [{**attachment, "file_field": f"attachment_{i}"} for i in range(6)]
    with pytest.raises(ValidationError):
        ManualAnalysisMetadata.model_validate(
            {**MANUAL_METADATA, "attachments": attachments}
        )


@pytest.mark.parametrize(
    "change",
    [
        {"mime": "application/zip"},  # ES: mime no permitido / EN: mime not allowed
        {"size_bytes": 26 * 1024 * 1024},  # ES: > 25 MB / EN: > 25 MB
        {"duration_s": 301},  # ES: > 5 min / EN: > 5 min
    ],
)
def test_audio_limits(change):
    audio = {**MANUAL_METADATA["attachments"][1], **change}
    with pytest.raises(ValidationError):
        ManualAnalysisMetadata.model_validate(
            {**MANUAL_METADATA, "attachments": [audio]}
        )


def test_manual_without_text_or_attachments_fails():
    data = {**MANUAL_METADATA, "text": None, "attachments": []}
    with pytest.raises(ValidationError):
        ManualAnalysisMetadata.model_validate(data)


# ---------- Verdict ----------


def test_verdict_contract_example_is_valid():
    assert Verdict.model_validate(VERDICT_RED).final is True


@pytest.mark.parametrize(
    "change",
    [
        {"action": "allow"},  # ES: red debe bloquear / EN: red must block
        {"threat_type": "none"},  # ES: red sin amenaza / EN: red without threat
        {"confidence": 1.5},
        {"block_template": "LLM TEXT"},  # ES: solo plantillas / EN: templates only
        {"block_template": None},
    ],
)
def test_invalid_verdicts_fail(change):
    with pytest.raises(ValidationError):
        Verdict.model_validate({**VERDICT_RED, **change})


def test_green_verdict_allows_without_template():
    data = {
        **VERDICT_RED,
        "risk_level": "green",
        "threat_type": "none",
        "action": "allow",
        "block_template": None,
    }
    assert Verdict.model_validate(data).action == "allow"
