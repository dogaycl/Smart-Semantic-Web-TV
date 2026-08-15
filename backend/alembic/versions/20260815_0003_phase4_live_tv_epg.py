"""Add live TV channels and EPG tables"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260815_0003"
down_revision: str | None = "20260809_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("country", sa.String(length=8), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("iptv_org_channel_id", sa.String(length=120), nullable=True),
        sa.Column("youtube_handle", sa.String(length=120), nullable=True),
        sa.Column("youtube_channel_id", sa.String(length=120), nullable=True),
        sa.Column("youtube_video_id", sa.String(length=120), nullable=True),
        sa.Column("stream_url", sa.String(length=500), nullable=True),
        sa.Column("quality", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("stream_status", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("stream_error", sa.String(length=500), nullable=True),
        sa.Column("epg_channel_id", sa.String(length=255), nullable=True),
        sa.Column("epg_source_url", sa.String(length=500), nullable=True),
        sa.Column("live_status", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("live_title", sa.String(length=255), nullable=True),
        sa.Column("live_description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("scheduled_start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_channels_id", "channels", ["id"], unique=False)
    op.create_index("ix_channels_slug", "channels", ["slug"], unique=True)

    op.create_table(
        "epg_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("channel_id", "external_id", "source", name="uq_epg_entries_channel_external_source"),
    )
    op.create_index("ix_epg_entries_id", "epg_entries", ["id"], unique=False)
    op.create_index("ix_epg_entries_channel_id", "epg_entries", ["channel_id"], unique=False)
    op.create_index("ix_epg_entries_start_time", "epg_entries", ["start_time"], unique=False)
    op.create_index("ix_epg_entries_end_time", "epg_entries", ["end_time"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_epg_entries_end_time", table_name="epg_entries")
    op.drop_index("ix_epg_entries_start_time", table_name="epg_entries")
    op.drop_index("ix_epg_entries_channel_id", table_name="epg_entries")
    op.drop_index("ix_epg_entries_id", table_name="epg_entries")
    op.drop_table("epg_entries")
    op.drop_index("ix_channels_slug", table_name="channels")
    op.drop_index("ix_channels_id", table_name="channels")
    op.drop_table("channels")
