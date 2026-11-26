"""indicator_reports: manual reports, one per device and indicator (#170).

ES: Guarda qué dispositivo reportó cada indicador para contar personas y no
    detecciones (ADR 0005). El número nunca se guarda en claro: el indicador
    solo tiene su HMAC y la versión enmascarada. Se borra en cascada con el
    indicador (retención de 12 meses) o con el dispositivo.
EN: Stores which device reported each indicator, to count people rather than
    detections (ADR 0005). The number is never stored in clear text. Cascades
    with the indicator (12-month retention) or the device.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-26 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "indicator_reports",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("indicator_id", sa.UUID(), nullable=False),
        sa.Column("device_id", sa.UUID(), nullable=False),
        sa.Column(
            "threat_type",
            postgresql.ENUM(name="threat_type", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["indicator_id"], ["indicators.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("indicator_id", "device_id"),
    )
    op.create_index(
        "ix_indicator_reports_indicator_id", "indicator_reports", ["indicator_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_indicator_reports_indicator_id", table_name="indicator_reports")
    op.drop_table("indicator_reports")
