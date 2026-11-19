"""add token_version to users.

ES: Versión de sesión del Tutor. Sube al cambiar o recuperar la contraseña y
    los tokens con la versión anterior dejan de valer. Las filas existentes
    empiezan en 0, igual que los tokens ya emitidos (sin "tv").
EN: Guardian session version. It is bumped on password change or reset and
    tokens with the previous version stop working. Existing rows start at 0,
    the same as tokens already issued (no "tv").

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-19 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
