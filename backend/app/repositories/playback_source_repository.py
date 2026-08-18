from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.playback_source import PlaybackSource


class PlaybackSourceRepository:
    def count_active(self, *, db: Session) -> int:
        statement = select(func.count(PlaybackSource.id)).where(PlaybackSource.is_active.is_(True))
        return int(db.scalar(statement) or 0)

    def list_for_content(self, *, db: Session, content_item_id: int, active_only: bool = True) -> list[PlaybackSource]:
        statement = (
            select(PlaybackSource)
            .where(PlaybackSource.content_item_id == content_item_id)
            .order_by(
                PlaybackSource.is_primary.desc(),
                PlaybackSource.source_type.asc(),
                PlaybackSource.name.asc(),
            )
        )
        if active_only:
            statement = statement.where(PlaybackSource.is_active.is_(True))
        return list(db.scalars(statement).all())

    def create(self, **kwargs) -> PlaybackSource:
        return PlaybackSource(**kwargs)
