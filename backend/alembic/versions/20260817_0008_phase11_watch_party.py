"""Add watch party room, participant, and message tables"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260817_0008"
down_revision: str | None = "20260817_0007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watch_rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_code", sa.String(length=12), nullable=False),
        sa.Column("host_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("content_slug", sa.String(length=180), nullable=True),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("channels.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title_snapshot", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("privacy", sa.String(length=24), nullable=False, server_default="invite_only"),
        sa.Column("current_position", sa.Float(), nullable=False, server_default="0"),
        sa.Column("playback_state", sa.String(length=24), nullable=False, server_default="paused"),
        sa.Column("host_last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("room_code", name="uq_watch_rooms_room_code"),
    )
    op.create_index("ix_watch_rooms_id", "watch_rooms", ["id"], unique=False)
    op.create_index("ix_watch_rooms_room_code", "watch_rooms", ["room_code"], unique=True)
    op.create_index("ix_watch_rooms_host_user_id", "watch_rooms", ["host_user_id"], unique=False)
    op.create_index("ix_watch_rooms_content_slug", "watch_rooms", ["content_slug"], unique=False)
    op.create_index("ix_watch_rooms_channel_id", "watch_rooms", ["channel_id"], unique=False)

    op.create_table(
        "watch_room_participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("watch_rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_host", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("room_id", "user_id", name="uq_watch_room_participants_room_user"),
    )
    op.create_index("ix_watch_room_participants_id", "watch_room_participants", ["id"], unique=False)
    op.create_index("ix_watch_room_participants_room_id", "watch_room_participants", ["room_id"], unique=False)
    op.create_index("ix_watch_room_participants_user_id", "watch_room_participants", ["user_id"], unique=False)

    op.create_table(
        "watch_room_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("watch_rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_watch_room_messages_id", "watch_room_messages", ["id"], unique=False)
    op.create_index("ix_watch_room_messages_room_id", "watch_room_messages", ["room_id"], unique=False)
    op.create_index("ix_watch_room_messages_user_id", "watch_room_messages", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_watch_room_messages_user_id", table_name="watch_room_messages")
    op.drop_index("ix_watch_room_messages_room_id", table_name="watch_room_messages")
    op.drop_index("ix_watch_room_messages_id", table_name="watch_room_messages")
    op.drop_table("watch_room_messages")

    op.drop_index("ix_watch_room_participants_user_id", table_name="watch_room_participants")
    op.drop_index("ix_watch_room_participants_room_id", table_name="watch_room_participants")
    op.drop_index("ix_watch_room_participants_id", table_name="watch_room_participants")
    op.drop_table("watch_room_participants")

    op.drop_index("ix_watch_rooms_channel_id", table_name="watch_rooms")
    op.drop_index("ix_watch_rooms_content_slug", table_name="watch_rooms")
    op.drop_index("ix_watch_rooms_host_user_id", table_name="watch_rooms")
    op.drop_index("ix_watch_rooms_room_code", table_name="watch_rooms")
    op.drop_index("ix_watch_rooms_id", table_name="watch_rooms")
    op.drop_table("watch_rooms")
