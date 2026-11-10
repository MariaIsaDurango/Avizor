"""Usuarios, dispositivos, vinculaciones y consentimientos.
Users, devices, pairings and consents.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import TZ, created_at, pg_enum, uuid_pk
from app.schemas.enums import Channel, ConsentType, UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    role: Mapped[UserRole] = mapped_column(pg_enum(UserRole, "user_role"))
    # ES: Solo el nombre, sin apellidos. EN: First name only, no surnames.
    display_name: Mapped[str] = mapped_column(Text)
    # ES: Solo guardian/admin. EN: Only guardian/admin.
    email: Mapped[str | None] = mapped_column(CITEXT, unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
    # ES: Borrado lógico, purga a los 30 días. EN: Soft delete, purged after 30 days.
    deleted_at: Mapped[datetime | None] = mapped_column(TZ)


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint("platform IN ('android', 'ios')", name="platform"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"))
    platform: Mapped[str] = mapped_column(Text)
    push_token: Mapped[str | None] = mapped_column(Text)
    app_version: Mapped[str] = mapped_column(Text)
    last_seen_at: Mapped[datetime | None] = mapped_column(TZ)


class Pairing(Base):
    __tablename__ = "pairings"
    __table_args__ = (UniqueConstraint("guardian_id", "senior_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    guardian_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"))
    # ES: Se rellena al canjear el código. EN: Filled in when the code is redeemed.
    senior_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("users.id"))
    code: Mapped[str] = mapped_column(String(6))
    # ES: Nombre que escribe el Tutor; se copia al usuario Sénior al canjear.
    # EN: Name typed by the guardian; copied to the senior user on redeem.
    senior_display_name: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(TZ)
    redeemed_at: Mapped[datetime | None] = mapped_column(TZ)
    active: Mapped[bool] = mapped_column(Boolean, server_default="true")


class Consent(Base):
    __tablename__ = "consents"
    __table_args__ = (
        # ES: La tutela legal exige evidencia. EN: Legal guardianship needs evidence.
        CheckConstraint(
            "type = 'self' OR evidence IS NOT NULL", name="evidence_required"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    senior_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"))
    type: Mapped[ConsentType] = mapped_column(pg_enum(ConsentType, "consent_type"))
    scope: Mapped[list[Channel]] = mapped_column(ARRAY(pg_enum(Channel, "channel")))
    text_version: Mapped[str] = mapped_column(Text)
    granted_by: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"))
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    granted_at: Mapped[datetime] = mapped_column(TZ)
    revoked_at: Mapped[datetime | None] = mapped_column(TZ)
