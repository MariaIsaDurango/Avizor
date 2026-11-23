"""add senior accessibility profile.

ES: El Tutor indica al crear el código de vinculación qué necesidades de
    accesibilidad tiene el Sénior. Se guarda en la vinculación y se copia al
    usuario Sénior al canjear el código. Las filas existentes quedan a NULL
    (sin perfil = interfaz por defecto).
EN: The guardian sets the senior's accessibility needs when creating the
    pairing code. It is stored on the pairing and copied to the senior user
    on redeem. Existing rows stay NULL (no profile = default interface).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-18 17:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("accessibility_profile", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "pairings",
        sa.Column("senior_accessibility_profile", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pairings", "senior_accessibility_profile")
    op.drop_column("users", "accessibility_profile")
