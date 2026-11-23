"""add phone to users.

ES: El Tutor puede guardar su teléfono en la cuenta (no solo en la vinculación).
    Así el campo está disponible antes de vincular un Sénior y se copia
    automáticamente al crear el código de pairing si no se indica otro.
    Las filas existentes quedan a NULL.
EN: The guardian can store their phone in their account (not only in the pairing).
    This makes the field available before linking a senior and it is copied
    automatically when creating a pairing code if no other phone is given.
    Existing rows stay NULL.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-23 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "phone")
