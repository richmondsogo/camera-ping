"""create monitoring_state table

Revision ID: cc0b65b49954
Revises: 402937679932
Create Date: 2026-10-04 04:22:35.728301

"""

from collections.abc import Sequence

import sqlalchemy as sa

import app.database
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cc0b65b49954"
down_revision: str | Sequence[str] | None = "402937679932"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "monitoring_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("running", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_cycle_started_at", app.database.UTCDateTime(), nullable=True),
        sa.Column("last_cycle_finished_at", app.database.UTCDateTime(), nullable=True),
        sa.CheckConstraint("id = 1", name=op.f("ck_monitoring_state_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_monitoring_state")),
    )

    monitoring_state = sa.table(
        "monitoring_state",
        sa.column("id", sa.Integer),
        sa.column("running", sa.Boolean),
        sa.column("last_cycle_started_at", app.database.UTCDateTime),
        sa.column("last_cycle_finished_at", app.database.UTCDateTime),
    )
    op.bulk_insert(
        monitoring_state,
        [
            {
                "id": 1,
                "running": False,
                "last_cycle_started_at": None,
                "last_cycle_finished_at": None,
            }
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("monitoring_state")
