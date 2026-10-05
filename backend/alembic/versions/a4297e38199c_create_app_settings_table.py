"""create_app_settings_table

Revision ID: a4297e38199c
Revises: cc0b65b49954
Create Date: 2026-10-05 08:26:25.350562

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4297e38199c"
down_revision: str | Sequence[str] | None = "cc0b65b49954"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("check_interval_seconds", sa.Integer(), nullable=True),
        sa.CheckConstraint("id = 1", name=op.f("ck_app_settings_id")),
        sa.CheckConstraint(
            "check_interval_seconds IS NULL OR "
            "(check_interval_seconds >= 10 AND check_interval_seconds <= 31536000)",
            name=op.f("ck_app_settings_check_interval_seconds"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_app_settings")),
    )

    app_settings = sa.table(
        "app_settings",
        sa.column("id", sa.Integer),
        sa.column("check_interval_seconds", sa.Integer),
    )
    op.bulk_insert(
        app_settings,
        [
            {
                "id": 1,
                "check_interval_seconds": None,
            }
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("app_settings")
