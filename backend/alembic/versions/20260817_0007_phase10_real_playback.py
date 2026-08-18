"""Add legal playback source tables for real movie playback"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260817_0007"
down_revision: str | None = "20260815_0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "playback_sources" in inspector.get_table_names():
        return

    op.create_table(
        "playback_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_item_id", sa.Integer(), sa.ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("playback_url", sa.String(length=1000), nullable=True),
        sa.Column("external_video_id", sa.String(length=255), nullable=True),
        sa.Column("embed_url", sa.String(length=1000), nullable=True),
        sa.Column("quality", sa.String(length=32), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("supports_seek", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("supports_state_tracking", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("provider_name", sa.String(length=120), nullable=True),
        sa.Column("provider_url", sa.String(length=1000), nullable=True),
        sa.Column("license_note", sa.Text(), nullable=True),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("content_item_id", "name", name="uq_playback_sources_item_name"),
    )
    op.create_index("ix_playback_sources_id", "playback_sources", ["id"], unique=False)
    op.create_index("ix_playback_sources_content_item_id", "playback_sources", ["content_item_id"], unique=False)
    op.create_index("ix_playback_sources_source_type", "playback_sources", ["source_type"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "playback_sources" not in inspector.get_table_names():
        return

    op.drop_index("ix_playback_sources_source_type", table_name="playback_sources")
    op.drop_index("ix_playback_sources_content_item_id", table_name="playback_sources")
    op.drop_index("ix_playback_sources_id", table_name="playback_sources")
    op.drop_table("playback_sources")
