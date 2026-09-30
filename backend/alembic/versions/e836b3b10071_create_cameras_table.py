"""create cameras table

Revision ID: e836b3b10071
Revises:
Create Date: 2026-09-30 08:39:41.956210

"""

from collections.abc import Sequence

import sqlalchemy as sa

import app.database
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e836b3b10071"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "cameras",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("camera_name", sa.String(length=100), nullable=False),
        sa.Column("location", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("ip_address", sa.String(length=15), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),
        sa.Column("last_checked", app.database.UTCDateTime(), nullable=True),
        sa.Column("last_online", app.database.UTCDateTime(), nullable=True),
        sa.Column(
            "consecutive_failures",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "alert_sent_for_current_outage",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("created_at", app.database.UTCDateTime(), nullable=False),
        sa.Column("updated_at", app.database.UTCDateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('unknown', 'online', 'offline')",
            name=op.f("ck_cameras_status"),
        ),
        sa.CheckConstraint(
            "consecutive_failures >= 0",
            name=op.f("ck_cameras_consecutive_failures"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cameras")),
        sa.UniqueConstraint("ip_address", name=op.f("uq_cameras_ip_address")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("cameras")
