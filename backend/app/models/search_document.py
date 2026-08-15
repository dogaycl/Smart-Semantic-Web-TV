from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.types import EmbeddingVector


class SearchDocument(Base):
    __tablename__ = "search_documents"
    __table_args__ = (
        UniqueConstraint("source_key", name="uq_search_documents_source_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    catalog_item_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=True, index=True)
    epg_entry_id: Mapped[int | None] = mapped_column(ForeignKey("epg_entries.id", ondelete="CASCADE"), nullable=True, index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"), nullable=True, index=True)
    content_slug: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    channel_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    channel_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    channel_logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    channel_source_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    category_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    genres: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    runtime_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float(), nullable=True)
    popularity: Mapped[float | None] = mapped_column(Float(), nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    backdrop_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    availability_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    availability_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    searchable_text: Mapped[str] = mapped_column(Text(), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingVector(), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="1")
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    embedding_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
