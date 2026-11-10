"""Indicadores de reputación y casos para administradores.
Reputation indicators and admin cases.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import TZ, created_at, pg_enum, uuid_pk
from app.schemas.enums import CaseStatus, IndicatorType


class Indicator(Base):
    __tablename__ = "indicators"
    __table_args__ = (UniqueConstraint("type", "value_hash"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    type: Mapped[IndicatorType] = mapped_column(
        pg_enum(IndicatorType, "indicator_type")
    )
    # ES: Teléfonos: solo hash. EN: Phones: hash only.
    value_hash: Mapped[str] = mapped_column(Text)
    # ES: Dominio en claro; teléfono enmascarado. EN: Plain domain; masked phone.
    public_value: Mapped[str] = mapped_column(Text)
    report_count: Mapped[int] = mapped_column(Integer, server_default="1")
    first_seen_at: Mapped[datetime] = mapped_column(TZ)
    last_seen_at: Mapped[datetime] = mapped_column(TZ)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = uuid_pk()
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("analyses.id")
    )
    indicator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("indicators.id")
    )
    status: Mapped[CaseStatus] = mapped_column(
        pg_enum(CaseStatus, "case_status"), server_default="open"
    )
    # ES: Administrador asignado. EN: Assigned admin.
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
    closed_at: Mapped[datetime | None] = mapped_column(TZ)
