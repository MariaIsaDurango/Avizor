"""add senior_solo to user_role.

ES: Sénior sin Tutor (#174). Se registra con email y contraseña y tiene su propio
    dispositivo. ADD VALUE no puede usarse en la misma transacción en la que se
    crea, por eso va en un bloque autocommit. PostgreSQL no permite quitar un
    valor de un ENUM: el downgrade no hace nada (el valor sin usar no molesta).
EN: Senior without a guardian (#174). Signs up with email and password and owns
    their device. ADD VALUE cannot be used in the transaction that adds it, so it
    runs in an autocommit block. PostgreSQL cannot drop an ENUM value: downgrade
    is a no-op (an unused value is harmless).

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-24 17:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'senior_solo'")


def downgrade() -> None:
    pass
