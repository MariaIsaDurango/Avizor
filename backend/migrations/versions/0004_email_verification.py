"""add email verification to users.

ES: El Tutor verifica su email con un código de 6 dígitos antes de poder
    iniciar sesión. Las cuentas que ya existían quedan verificadas para no
    bloquear a nadie.
EN: The guardian verifies their email with a 6-digit code before logging in.
    Existing accounts are marked as verified so nobody is locked out.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-18 10:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """ES: Añade las columnas; las filas existentes quedan verificadas.
    EN: Adds the columns; existing rows are left as verified.
    """
    op.add_column(
        "users",
        sa.Column(
            "is_verified", sa.Boolean(), server_default=sa.true(), nullable=False
        ),
    )
    # ES: A partir de ahora, las cuentas nuevas nacen sin verificar.
    # EN: From now on, new accounts start unverified.
    op.alter_column("users", "is_verified", server_default=sa.false())
    op.add_column("users", sa.Column("verification_code_hash", sa.Text()))
    op.add_column(
        "users", sa.Column("verification_code_expires_at", sa.DateTime(timezone=True))
    )
    op.add_column(
        "users",
        sa.Column(
            "verification_attempts", sa.Integer(), server_default="0", nullable=False
        ),
    )


def downgrade() -> None:
    """ES: Quita las columnas. EN: Removes the columns."""
    op.drop_column("users", "verification_attempts")
    op.drop_column("users", "verification_code_expires_at")
    op.drop_column("users", "verification_code_hash")
    op.drop_column("users", "is_verified")
