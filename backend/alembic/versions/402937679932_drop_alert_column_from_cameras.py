"""drop alert column from cameras

Revision ID: 402937679932
Revises: e836b3b10071
Create Date: 2026-10-04 04:14:32.670713

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "402937679932"
down_revision: str | Sequence[str] | None = "e836b3b10071"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("cameras", schema=None) as batch_op:
        batch_op.drop_column("alert_sent_for_current_outage")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("cameras", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "alert_sent_for_current_outage",
                sa.Boolean(),
                server_default=sa.text("0"),
                nullable=False,
            )
        )
