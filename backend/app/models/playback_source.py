from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class PlaybackSource(Base):
    __tablename__ = "playback_sources"
    __table_args__ = (
        UniqueConstraint("content_item_id", "name", name="uq_playback_sources_item_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content_item_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    playback_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    external_video_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embed_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    quality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="1")
    supports_seek: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="1")
    supports_state_tracking: Mapped[bool] = mapped_column(
        Boolean(),
        nullable=False,
        default=True,
        server_default="1",
    )
    provider_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    license_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    source_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
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

    content_item = relationship("CatalogItem", back_populates="playback_sources")
