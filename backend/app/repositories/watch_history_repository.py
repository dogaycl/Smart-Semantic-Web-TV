from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.watch_history import WatchHistory


class WatchHistoryRepository:
    def list_for_user(self, *, db: Session, user_id: int) -> list[WatchHistory]:
        statement = (
            select(WatchHistory)
            .where(WatchHistory.user_id == user_id)
            .order_by(WatchHistory.last_watched_at.desc(), WatchHistory.updated_at.desc(), WatchHistory.id.desc())
        )
        return list(db.scalars(statement).all())

    def get_for_user_content(
        self,
        *,
        db: Session,
        user_id: int,
        content_id: str,
        content_type: str,
    ) -> WatchHistory | None:
        statement = select(WatchHistory).where(
            WatchHistory.user_id == user_id,
            WatchHistory.content_id == content_id,
            WatchHistory.content_type == content_type,
        )
        return db.scalar(statement)

    def create(
        self,
        *,
        user_id: int,
        content_id: str,
        content_type: str,
        watch_position_seconds: int,
        total_watched_duration_seconds: int,
        is_completed: bool,
        last_watched_at,
    ) -> WatchHistory:
        return WatchHistory(
            user_id=user_id,
            content_id=content_id,
            content_type=content_type,
            watch_position_seconds=watch_position_seconds,
            total_watched_duration_seconds=total_watched_duration_seconds,
            is_completed=is_completed,
            last_watched_at=last_watched_at,
        )
