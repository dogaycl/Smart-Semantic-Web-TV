from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class CatalogVideo(Base):
    __tablename__ = "catalog_videos"
    __table_args__ = (
        UniqueConstraint("content_item_id", "tmdb_video_id", name="uq_catalog_videos_item_tmdb_video"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content_item_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tmdb_video_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    site: Mapped[str] = mapped_column(String(80), nullable=False)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    video_key: Mapped[str] = mapped_column(String(255), nullable=False)
    official: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="0")
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    country: Mapped[str | None] = mapped_column(String(16), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    content_item = relationship("CatalogItem", back_populates="videos")
