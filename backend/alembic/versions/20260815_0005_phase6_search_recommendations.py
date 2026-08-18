"""Add semantic search and recommendation index tables"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import exc as sa_exc
from sqlalchemy.types import UserDefinedType


class VectorType(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kwargs) -> str:
        return "vector"


# revision identifiers, used by Alembic.
revision: str = "20260815_0005"
down_revision: str | None = "20260815_0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    context = op.get_context()
    embedding_type: sa.types.TypeEngine = sa.JSON()

    try:
        with context.autocommit_block():
            bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        embedding_type = VectorType()
    except sa_exc.DBAPIError:
        # Local development may not have pgvector installed yet. In that case
        # we still create the search index table and rely on JSON-backed
        # fallback behavior until the extension is available.
        embedding_type = sa.JSON()

    op.create_table(
        "search_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("catalog_item_id", sa.Integer(), sa.ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=True),
        sa.Column("epg_entry_id", sa.Integer(), sa.ForeignKey("epg_entries.id", ondelete="CASCADE"), nullable=True),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=True),
        sa.Column("content_slug", sa.String(length=180), nullable=True),
        sa.Column("channel_slug", sa.String(length=100), nullable=True),
        sa.Column("channel_name", sa.String(length=150), nullable=True),
        sa.Column("channel_logo_url", sa.String(length=500), nullable=True),
        sa.Column("channel_source_type", sa.String(length=16), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_label", sa.String(length=120), nullable=True),
        sa.Column("genres", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("runtime_label", sa.String(length=64), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("popularity", sa.Float(), nullable=True),
        sa.Column("poster_url", sa.String(length=500), nullable=True),
        sa.Column("backdrop_url", sa.String(length=500), nullable=True),
        sa.Column("availability_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("availability_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("searchable_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", embedding_type, nullable=True),
        sa.Column("embedding_model", sa.String(length=80), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source_key", name="uq_search_documents_source_key"),
    )
    op.create_index("ix_search_documents_id", "search_documents", ["id"], unique=False)
    op.create_index("ix_search_documents_source_key", "search_documents", ["source_key"], unique=False)
    op.create_index("ix_search_documents_document_type", "search_documents", ["document_type"], unique=False)
    op.create_index("ix_search_documents_content_type", "search_documents", ["content_type"], unique=False)
    op.create_index("ix_search_documents_catalog_item_id", "search_documents", ["catalog_item_id"], unique=False)
    op.create_index("ix_search_documents_epg_entry_id", "search_documents", ["epg_entry_id"], unique=False)
    op.create_index("ix_search_documents_channel_id", "search_documents", ["channel_id"], unique=False)
    op.create_index("ix_search_documents_content_slug", "search_documents", ["content_slug"], unique=False)
    op.create_index("ix_search_documents_availability_start", "search_documents", ["availability_start"], unique=False)
    op.create_index("ix_search_documents_availability_end", "search_documents", ["availability_end"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_search_documents_availability_end", table_name="search_documents")
    op.drop_index("ix_search_documents_availability_start", table_name="search_documents")
    op.drop_index("ix_search_documents_content_slug", table_name="search_documents")
    op.drop_index("ix_search_documents_channel_id", table_name="search_documents")
    op.drop_index("ix_search_documents_epg_entry_id", table_name="search_documents")
    op.drop_index("ix_search_documents_catalog_item_id", table_name="search_documents")
    op.drop_index("ix_search_documents_content_type", table_name="search_documents")
    op.drop_index("ix_search_documents_document_type", table_name="search_documents")
    op.drop_index("ix_search_documents_source_key", table_name="search_documents")
    op.drop_index("ix_search_documents_id", table_name="search_documents")
    op.drop_table("search_documents")
