"""Make the one-accepted-plan-per-date index partial on every backend

Revision 0009 created ``uq_viewing_plans_user_date_active`` on ``(user_id, plan_date)`` with
``unique=True`` and only a ``postgresql_where`` predicate. On PostgreSQL that is the intended
partial unique index (at most one ``is_accepted`` plan per user per date). On SQLite the
``postgresql_where`` is ignored, so it became a *full* unique index that blocks a user from ever
having more than one plan row for a date - including the draft/superseded history the feature is
designed to keep. Regenerating "My Channel" for a date that already had a plan raised
``IntegrityError`` and surfaced as a 500.

This migration recreates the index with an equivalent ``sqlite_where`` predicate so SQLite also
gets a real partial index. SQLite has supported partial indexes since 3.8.0.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260831_0011"
down_revision: str | None = "20260830_0010"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

INDEX_NAME = "uq_viewing_plans_user_date_active"


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).get_table_names().count("viewing_plans") == 0:
        return

    op.execute(sa.text(f"DROP INDEX IF EXISTS {INDEX_NAME}"))
    op.create_index(
        INDEX_NAME,
        "viewing_plans",
        ["user_id", "plan_date"],
        unique=True,
        postgresql_where=sa.text("is_accepted = true"),
        sqlite_where=sa.text("is_accepted = 1"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).get_table_names().count("viewing_plans") == 0:
        return

    op.execute(sa.text(f"DROP INDEX IF EXISTS {INDEX_NAME}"))
    op.create_index(
        INDEX_NAME,
        "viewing_plans",
        ["user_id", "plan_date"],
        unique=True,
        postgresql_where=sa.text("is_accepted = true"),
    )
