"""add guardian phone to pairings.

ES: El Tutor puede indicar su teléfono al crear el código para que el Sénior
    le llame desde la app con un solo botón. Opcional: las filas existentes
    quedan a NULL.
EN: The guardian can add their phone number when creating the code so the
    senior can call them from the app with one button. Optional: existing
    rows stay NULL.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-19 09:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pairings", sa.Column("guardian_phone", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("pairings", "guardian_phone")
