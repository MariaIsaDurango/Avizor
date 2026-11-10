"""Análisis, contenido temporal y metadatos de adjuntos.
Analyses, temporary content and attachment metadata.

ES: analyses NO guarda el texto del mensaje; el binario de los adjuntos nunca se guarda.
EN: analyses does NOT store the message text; attachment binaries are never stored.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import TZ, created_at, pg_enum, uuid_pk
from app.schemas.enums import (
    Action,
    Channel,
    InputType,
    Origin,
    RiskLevel,
    ThreatType,
    VerdictPhase,
)


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1", name="confidence_range"),
        Index("ix_analyses_created_at_threat_type", "created_at", "threat_type"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    device_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("devices.id"))
    channel: Mapped[Channel] = mapped_column(pg_enum(Channel, "channel"))
    origin: Mapped[Origin] = mapped_column(pg_enum(Origin, "origin"))
    # ES: Un reenvío puede mezclar texto, imagen y audio.
    # EN: A forward can mix text, image and audio.
    input_types: Mapped[list[InputType]] = mapped_column(
        ARRAY(pg_enum(InputType, "input_type"))
    )
    # ES: HMAC-SHA256 con clave del servidor. EN: HMAC-SHA256 with server key.
    sender_hash: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(TZ)
    risk_level: Mapped[RiskLevel] = mapped_column(pg_enum(RiskLevel, "risk_level"))
    threat_type: Mapped[ThreatType] = mapped_column(pg_enum(ThreatType, "threat_type"))
    action: Mapped[Action] = mapped_column(pg_enum(Action, "action"))
    block_template: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    phase: Mapped[VerdictPhase] = mapped_column(pg_enum(VerdictPhase, "verdict_phase"))
    model_version: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    server_processed: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = created_at()


class TempContent(Base):
    """ES: Texto anonimizado con borrado obligatorio (green 0 d, amber 7 d, red 30 d).
    EN: Anonymized text with mandatory deletion (green 0 d, amber 7 d, red 30 d).
    """

    __tablename__ = "temp_content"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("analyses.id", ondelete="CASCADE"), primary_key=True
    )
    anonymized_text: Mapped[str] = mapped_column(Text)
    urls: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    delete_at: Mapped[datetime] = mapped_column(TZ, index=True)


class AnalysisAttachment(Base):
    """ES: Solo metadatos: el archivo original nunca se guarda.
    EN: Metadata only: the original file is never stored.
    """

    __tablename__ = "analysis_attachments"
    __table_args__ = (
        CheckConstraint("type IN ('image', 'audio', 'video', 'document')", name="type"),
        CheckConstraint(
            "ner_applied_on IN ('device', 'server')", name="ner_applied_on"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("analyses.id", ondelete="CASCADE")
    )
    type: Mapped[InputType] = mapped_column(pg_enum(InputType, "input_type"))
    mime: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(Integer)
    # ES: Solo audio y vídeo. EN: Audio and video only.
    duration_s: Mapped[int | None] = mapped_column(Integer)
    local_preprocessing: Mapped[bool] = mapped_column(Boolean)
    # ES: 'mlkit-ocr', 'whisper-small'... EN: 'mlkit-ocr', 'whisper-small'...
    extraction_engine: Mapped[str] = mapped_column(Text)
    ner_applied_on: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
