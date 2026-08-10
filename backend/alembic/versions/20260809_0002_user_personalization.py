"""Add favorites and watch history tables"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260809_0002"
down_revision: str | None = "20260809_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_id", sa.String(length=255), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "content_id", name="uq_favorites_user_content"),
    )
    op.create_index("ix_favorites_id", "favorites", ["id"], unique=False)
    op.create_index("ix_favorites_user_id", "favorites", ["user_id"], unique=False)

    op.create_table(
        "watch_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_id", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False, server_default="content"),
        sa.Column("watch_position_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_watched_duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_watched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "content_id", "content_type", name="uq_watch_history_user_content_type"),
    )
    op.create_index("ix_watch_history_id", "watch_history", ["id"], unique=False)
    op.create_index("ix_watch_history_user_id", "watch_history", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_watch_history_user_id", table_name="watch_history")
    op.drop_index("ix_watch_history_id", table_name="watch_history")
    op.drop_table("watch_history")
    op.drop_index("ix_favorites_user_id", table_name="favorites")
    op.drop_index("ix_favorites_id", table_name="favorites")
    op.drop_table("favorites")
