"""add final flag to analyses.

ES: Un reenvío manual se guarda primero con un veredicto provisional
    (final = false) y el agente lo completa después (final = true).
    Los análisis de la vía rápida nacen ya finales.
EN: A manual forward is first stored with a provisional verdict
    (final = false) and the agent completes it later (final = true).
    Fast path analyses are final from the start.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-16 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """ES: Añade la columna (las filas existentes quedan como finales).
    EN: Adds the column (existing rows become final).
    """
    op.add_column(
        "analyses",
        sa.Column("final", sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade() -> None:
    """ES: Quita la columna. EN: Removes the column."""
    op.drop_column("analyses", "final")
