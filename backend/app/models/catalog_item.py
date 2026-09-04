from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class CatalogItem(Base):
    __tablename__ = "catalog_items"
    __table_args__ = (
        UniqueConstraint("content_type", "tmdb_id", name="uq_catalog_items_content_type_tmdb_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    overview: Mapped[str | None] = mapped_column(Text(), nullable=True)
    release_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    backdrop_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    vote_average: Mapped[float | None] = mapped_column(Float, nullable=True)
    popularity: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    top_cast: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    top_crew: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    number_of_seasons: Mapped[int | None] = mapped_column(Integer, nullable=True)
    number_of_episodes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tmdb_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="1")
    # Pinned items are curator-added (bulk TMDB import, wired-up playable titles) and are exempt
    # from the bucket-sync reconciliation sweep that deactivates anything outside CATALOG_BUCKETS.
    is_pinned: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="0")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    genres = relationship(
        "CatalogGenre",
        back_populates="content_item",
        cascade="all, delete-orphan",
        order_by="CatalogGenre.name.asc()",
    )
    seasons = relationship(
        "CatalogSeason",
        back_populates="content_item",
        cascade="all, delete-orphan",
        order_by="CatalogSeason.season_number.asc()",
    )
    videos = relationship(
        "CatalogVideo",
        back_populates="content_item",
        cascade="all, delete-orphan",
        order_by="CatalogVideo.official.desc(), CatalogVideo.published_at.desc()",
    )
    playback_sources = relationship(
        "PlaybackSource",
        back_populates="content_item",
        cascade="all, delete-orphan",
        order_by="PlaybackSource.is_primary.desc(), PlaybackSource.name.asc()",
    )
