from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    iptv_org_channel_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    youtube_handle: Mapped[str | None] = mapped_column(String(120), nullable=True)
    youtube_channel_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    youtube_video_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    stream_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="1")
    stream_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="unknown",
        server_default="unknown",
    )
    stream_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    epg_channel_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    epg_source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    live_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="unknown",
        server_default="unknown",
    )
    live_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    live_description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scheduled_start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    epg_entries = relationship(
        "EPGEntry",
        back_populates="channel",
        cascade="all, delete-orphan",
    )
    watch_rooms = relationship(
        "WatchRoom",
        back_populates="channel",
    )
