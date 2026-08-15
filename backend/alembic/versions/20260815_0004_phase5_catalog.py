"""Add TMDB-backed movie and TV catalog tables"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260815_0004"
down_revision: str | None = "20260815_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catalog_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("content_type", sa.String(length=16), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("original_title", sa.String(length=255), nullable=True),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("runtime_minutes", sa.Integer(), nullable=True),
        sa.Column("poster_url", sa.String(length=500), nullable=True),
        sa.Column("backdrop_url", sa.String(length=500), nullable=True),
        sa.Column("vote_average", sa.Float(), nullable=True),
        sa.Column("popularity", sa.Float(), nullable=True),
        sa.Column("original_language", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=True),
        sa.Column("top_cast", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("top_crew", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("number_of_seasons", sa.Integer(), nullable=True),
        sa.Column("number_of_episodes", sa.Integer(), nullable=True),
        sa.Column("tmdb_url", sa.String(length=500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("content_type", "tmdb_id", name="uq_catalog_items_content_type_tmdb_id"),
    )
    op.create_index("ix_catalog_items_id", "catalog_items", ["id"], unique=False)
    op.create_index("ix_catalog_items_slug", "catalog_items", ["slug"], unique=True)
    op.create_index("ix_catalog_items_content_type", "catalog_items", ["content_type"], unique=False)
    op.create_index("ix_catalog_items_tmdb_id", "catalog_items", ["tmdb_id"], unique=False)

    op.create_table(
        "catalog_genres",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_item_id", sa.Integer(), sa.ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tmdb_genre_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("content_item_id", "tmdb_genre_id", name="uq_catalog_genres_item_tmdb_genre"),
    )
    op.create_index("ix_catalog_genres_id", "catalog_genres", ["id"], unique=False)
    op.create_index("ix_catalog_genres_content_item_id", "catalog_genres", ["content_item_id"], unique=False)
    op.create_index("ix_catalog_genres_name", "catalog_genres", ["name"], unique=False)

    op.create_table(
        "catalog_seasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_item_id", sa.Integer(), sa.ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tmdb_season_id", sa.Integer(), nullable=True),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("air_date", sa.Date(), nullable=True),
        sa.Column("episode_count", sa.Integer(), nullable=True),
        sa.Column("poster_url", sa.String(length=500), nullable=True),
        sa.UniqueConstraint("content_item_id", "season_number", name="uq_catalog_seasons_item_number"),
    )
    op.create_index("ix_catalog_seasons_id", "catalog_seasons", ["id"], unique=False)
    op.create_index("ix_catalog_seasons_content_item_id", "catalog_seasons", ["content_item_id"], unique=False)

    op.create_table(
        "catalog_videos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_item_id", sa.Integer(), sa.ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tmdb_video_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("site", sa.String(length=80), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("video_key", sa.String(length=255), nullable=False),
        sa.Column("official", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("country", sa.String(length=16), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("content_item_id", "tmdb_video_id", name="uq_catalog_videos_item_tmdb_video"),
    )
    op.create_index("ix_catalog_videos_id", "catalog_videos", ["id"], unique=False)
    op.create_index("ix_catalog_videos_content_item_id", "catalog_videos", ["content_item_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_catalog_videos_content_item_id", table_name="catalog_videos")
    op.drop_index("ix_catalog_videos_id", table_name="catalog_videos")
    op.drop_table("catalog_videos")
    op.drop_index("ix_catalog_seasons_content_item_id", table_name="catalog_seasons")
    op.drop_index("ix_catalog_seasons_id", table_name="catalog_seasons")
    op.drop_table("catalog_seasons")
    op.drop_index("ix_catalog_genres_name", table_name="catalog_genres")
    op.drop_index("ix_catalog_genres_content_item_id", table_name="catalog_genres")
    op.drop_index("ix_catalog_genres_id", table_name="catalog_genres")
    op.drop_table("catalog_genres")
    op.drop_index("ix_catalog_items_tmdb_id", table_name="catalog_items")
    op.drop_index("ix_catalog_items_content_type", table_name="catalog_items")
    op.drop_index("ix_catalog_items_slug", table_name="catalog_items")
    op.drop_index("ix_catalog_items_id", table_name="catalog_items")
    op.drop_table("catalog_items")
