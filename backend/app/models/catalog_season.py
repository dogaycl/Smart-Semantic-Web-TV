from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class CatalogSeason(Base):
    __tablename__ = "catalog_seasons"
    __table_args__ = (
        UniqueConstraint("content_item_id", "season_number", name="uq_catalog_seasons_item_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content_item_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tmdb_season_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    overview: Mapped[str | None] = mapped_column(Text(), nullable=True)
    air_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    episode_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    content_item = relationship("CatalogItem", back_populates="seasons")
