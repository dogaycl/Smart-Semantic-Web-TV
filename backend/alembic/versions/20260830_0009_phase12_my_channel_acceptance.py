"""Add accepted My Channel plan persistence

Revision ID: 20260830_0009
Revises: 20260817_0008
Create Date: 2026-08-30 02:10:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260830_0009"
down_revision = "20260817_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "viewing_plans",
        sa.Column("is_accepted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "viewing_plans",
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_viewing_plans_is_accepted", "viewing_plans", ["is_accepted"], unique=False)
    op.create_index(
        "uq_viewing_plans_user_date_active",
        "viewing_plans",
        ["user_id", "plan_date"],
        unique=True,
        postgresql_where=sa.text("is_accepted = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_viewing_plans_user_date_active", table_name="viewing_plans")
    op.drop_index("ix_viewing_plans_is_accepted", table_name="viewing_plans")
    op.drop_column("viewing_plans", "accepted_at")
    op.drop_column("viewing_plans", "is_accepted")
