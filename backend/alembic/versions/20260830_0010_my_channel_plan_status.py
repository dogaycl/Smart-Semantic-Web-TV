"""Add plan status history to accepted My Channel plans"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260830_0010"
down_revision: str | None = "20260830_0009"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Record *why* a plan is not accepted.

    Revision 0009 added the `is_accepted` boolean, which cannot distinguish a plan that was
    never accepted from one that was accepted and later replaced. Accepting a plan for a date
    must supersede the previously active plan for that same date while keeping it as history,
    so the lifecycle needs an explicit status.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "viewing_plans" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("viewing_plans")}
    if "status" not in columns:
        op.add_column(
            "viewing_plans",
            sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        )
    if "superseded_at" not in columns:
        op.add_column("viewing_plans", sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True))

    # Backfill: rows already accepted by revision 0009 are the active plans for their date.
    op.execute(sa.text("UPDATE viewing_plans SET status = 'active' WHERE is_accepted = true"))

    indexes = {index["name"] for index in inspector.get_indexes("viewing_plans")}
    if "ix_viewing_plans_user_date_status" not in indexes:
        op.create_index(
            "ix_viewing_plans_user_date_status",
            "viewing_plans",
            ["user_id", "plan_date", "status"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "viewing_plans" not in inspector.get_table_names():
        return

    indexes = {index["name"] for index in inspector.get_indexes("viewing_plans")}
    if "ix_viewing_plans_user_date_status" in indexes:
        op.drop_index("ix_viewing_plans_user_date_status", table_name="viewing_plans")

    columns = {column["name"] for column in inspector.get_columns("viewing_plans")}
    for column_name in ("superseded_at", "status"):
        if column_name in columns:
            op.drop_column("viewing_plans", column_name)
