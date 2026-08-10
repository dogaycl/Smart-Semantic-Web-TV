from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.favorite import Favorite


class FavoriteRepository:
    def list_for_user(self, *, db: Session, user_id: int) -> list[Favorite]:
        statement = (
            select(Favorite)
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.added_at.desc(), Favorite.id.desc())
        )
        return list(db.scalars(statement).all())

    def get_for_user_and_content(self, *, db: Session, user_id: int, content_id: str) -> Favorite | None:
        statement = select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.content_id == content_id,
        )
        return db.scalar(statement)

    def create(self, *, user_id: int, content_id: str) -> Favorite:
        return Favorite(user_id=user_id, content_id=content_id)

    def delete(self, *, db: Session, favorite: Favorite) -> None:
        db.delete(favorite)
