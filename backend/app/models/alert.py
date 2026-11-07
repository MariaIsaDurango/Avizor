"""Alertas para el Tutor y solicitudes de desbloqueo.
Guardian alerts and unlock requests.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import TZ, created_at, pg_enum, uuid_pk
from app.schemas.enums import AlertStatus, UnlockStatus


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index(
            "ix_alerts_guardian_id_status_created_at",
            "guardian_id",
            "status",
            text("created_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    analysis_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("analyses.id"))
    guardian_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"))
    summary: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'"))
    status: Mapped[AlertStatus] = mapped_column(
        pg_enum(AlertStatus, "alert_status"), server_default="new"
    )
    created_at: Mapped[datetime] = created_at()


class Unlock(Base):
    __tablename__ = "unlocks"

    id: Mapped[uuid.UUID] = uuid_pk()
    analysis_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("analyses.id"))
    status: Mapped[UnlockStatus] = mapped_column(
        pg_enum(UnlockStatus, "unlock_status"), server_default="pending_guardian"
    )
    requested_at: Mapped[datetime] = mapped_column(TZ, server_default=text("now()"))
    expires_at: Mapped[datetime] = mapped_column(TZ)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(TZ)
