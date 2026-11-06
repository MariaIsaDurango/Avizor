"""Schemas de entrada de análisis (Sénior → backend).
Analysis input schemas (Senior → backend).

POST /api/v1/analyses
  - JSON              → AnalysisRequest  (automático o número / automatic or phone)
  - multipart/form-data → ManualAnalysisMetadata + attachment_0..4 (reenvío manual)
"""

import re
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, HttpUrl, model_validator

from app.schemas.common import ContractModel
from app.schemas.enums import Channel, InputType, Origin, RedactedEntity

# ES: Teléfono en formato E.164 (+34612345612). EN: Phone number in E.164 format.
E164_PATTERN = r"^\+[1-9]\d{6,14}$"

# ES: La vía rápida automática solo acepta estos tipos.
# EN: The automatic fast path only accepts these types.
AUTOMATIC_INPUT_TYPES = {InputType.TEXT, InputType.URL, InputType.PHONE_NUMBER}


class Anonymization(ContractModel):
    """ES: Resultado del NER en el móvil. Si applied=false, el endpoint responde
    422 CONTENT_NOT_ANONYMIZED (lo comprueba el endpoint, no el schema).
    EN: On-device NER result. If applied=false, the endpoint returns
    422 CONTENT_NOT_ANONYMIZED (checked by the endpoint, not the schema).
    """

    applied: bool
    ner_model_version: str = Field(min_length=1, max_length=50)
    redacted_entities: list[RedactedEntity] = Field(default_factory=list)


class Sender(ContractModel):
    """ES: Remitente. El servidor guarda solo el HMAC y la versión enmascarada.
    EN: Sender. The server only stores the HMAC and the masked version.
    """

    type: Literal["phone", "alphanumeric_sender"]
    value: str = Field(min_length=1, max_length=20)
    masked: str | None = None

    @model_validator(mode="after")
    def check_phone_format(self) -> "Sender":
        if self.type == "phone" and not re.fullmatch(E164_PATTERN, self.value):
            raise ValueError("phone sender must be in E.164 format")
        return self


class Content(ContractModel):
    text: str = Field(max_length=5000)
    urls: list[HttpUrl] = Field(default_factory=list, max_length=10)
    language: str = Field(default="es", pattern=r"^[a-z]{2}$")
    anonymization: Anonymization
    server_processed: bool = False


class AppInfo(ContractModel):
    version: str = Field(min_length=1, max_length=20)
    android_api: int | None = Field(default=None, ge=21)


class AnalysisRequest(ContractModel):
    """ES: Intercepción automática (SMS, notificación, pantalla, llamada) o
    consulta manual de un número. Siempre por la vía rápida (< 800 ms).
    EN: Automatic interception (SMS, notification, screen, call) or manual
    phone lookup. Always goes through the fast path (< 800 ms).
    """

    device_id: UUID
    channel: Channel
    origin: Origin
    input_type: InputType
    received_at: AwareDatetime
    sender: Sender | None = None
    content: Content | None = None
    app: AppInfo | None = None

    @model_validator(mode="after")
    def check_rules(self) -> "AnalysisRequest":
        if self.input_type not in AUTOMATIC_INPUT_TYPES:
            raise ValueError("JSON requests only accept text, url or phone_number")

        if self.input_type == InputType.PHONE_NUMBER:
            # ES: Consulta de número: se analiza el número, nunca la conversación.
            # EN: Phone lookup: only the number is analysed, never the call.
            if self.sender is None or self.sender.type != "phone":
                raise ValueError("phone_number requires a phone sender")
        elif self.content is None:
            raise ValueError("text and url requests require content")

        if self.channel == Channel.CALL and self.input_type != InputType.PHONE_NUMBER:
            raise ValueError("call channel only accepts phone_number")
        return self


# ES: Límites por tipo de adjunto (tabla del contrato).
# EN: Per-attachment limits (contract table).
MB = 1024 * 1024
ATTACHMENT_RULES = {
    InputType.IMAGE: {
        "mimes": {"image/jpeg", "image/png", "image/webp", "image/heic"},
        "max_bytes": 10 * MB,
        "max_seconds": None,
    },
    InputType.AUDIO: {
        "mimes": {"audio/ogg", "audio/mp4", "audio/x-m4a", "audio/mpeg", "audio/wav"},
        "max_bytes": 25 * MB,
        "max_seconds": 300,
    },
    InputType.VIDEO: {
        "mimes": {"video/mp4"},
        "max_bytes": 50 * MB,
        "max_seconds": 60,
    },
    InputType.DOCUMENT: {
        "mimes": {"application/pdf"},
        "max_bytes": 10 * MB,
        "max_seconds": None,
    },
}


class LocalPreprocessing(ContractModel):
    """ES: OCR + NER hechos en el móvil. EN: OCR + NER done on the phone."""

    ocr: bool
    extracted_text: str = Field(max_length=5000)
    ner_applied: bool


class Attachment(ContractModel):
    file_field: str = Field(pattern=r"^attachment_[0-4]$")
    type: InputType
    mime: str
    size_bytes: int = Field(gt=0)
    duration_s: int | None = Field(default=None, ge=0)
    local_preprocessing: LocalPreprocessing | None = None

    @model_validator(mode="after")
    def check_limits(self) -> "Attachment":
        rules = ATTACHMENT_RULES.get(self.type)
        if rules is None:
            raise ValueError("attachment type must be image, audio, video or document")
        if self.mime not in rules["mimes"]:
            raise ValueError(f"mime {self.mime} not allowed for {self.type}")
        if self.size_bytes > rules["max_bytes"]:
            raise ValueError(f"{self.type} exceeds the size limit")
        max_seconds = rules["max_seconds"]
        if max_seconds and self.duration_s and self.duration_s > max_seconds:
            raise ValueError(f"{self.type} exceeds the duration limit")
        return self


class ManualAnalysisMetadata(ContractModel):
    """ES: Parte 'metadata' del reenvío manual multimodal (respuesta 202).
    EN: 'metadata' part of the multimodal manual forward (202 response).
    """

    device_id: UUID
    channel: Literal[Channel.MANUAL] = Channel.MANUAL
    origin: Literal[Origin.MANUAL] = Origin.MANUAL
    received_at: AwareDatetime
    text: str | None = Field(default=None, max_length=5000)
    anonymization: Anonymization
    attachments: list[Attachment] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def check_not_empty(self) -> "ManualAnalysisMetadata":
        if not self.text and not self.attachments:
            raise ValueError("send text or at least one attachment")
        fields = [a.file_field for a in self.attachments]
        if len(fields) != len(set(fields)):
            raise ValueError("file_field values must be unique")
        return self
