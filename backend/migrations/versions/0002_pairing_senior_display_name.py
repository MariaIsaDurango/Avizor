"""add senior_display_name to pairings.

ES: El Tutor escribe el nombre del Sénior al crear el código; se guarda aquí
    hasta que el móvil canjea el código y se crea el usuario Sénior.
EN: The guardian types the senior's name when creating the code; it is kept
    here until the phone redeems the code and the senior user is created.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-09 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """ES: Añade la columna. EN: Adds the column."""
    op.add_column("pairings", sa.Column("senior_display_name", sa.Text()))
    # ES: Por si ya hubiera filas; luego se hace obligatoria.
    # EN: In case rows already exist; then it becomes required.
    op.execute(
        "UPDATE pairings SET senior_display_name = '' WHERE senior_display_name IS NULL"
    )
    op.alter_column("pairings", "senior_display_name", nullable=False)


def downgrade() -> None:
    """ES: Quita la columna. EN: Removes the column."""
    op.drop_column("pairings", "senior_display_name")
