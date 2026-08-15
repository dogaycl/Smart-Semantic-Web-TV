from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class CatalogGenre(Base):
    __tablename__ = "catalog_genres"
    __table_args__ = (
        UniqueConstraint("content_item_id", "tmdb_genre_id", name="uq_catalog_genres_item_tmdb_genre"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content_item_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tmdb_genre_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    content_item = relationship("CatalogItem", back_populates="genres")
