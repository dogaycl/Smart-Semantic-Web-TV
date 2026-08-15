from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.channel import Channel


class ChannelRepository:
    def count(self, *, db: Session) -> int:
        return len(db.scalars(select(Channel.id)).all())

    def list_all(self, *, db: Session) -> list[Channel]:
        statement = select(Channel).options(selectinload(Channel.epg_entries)).order_by(Channel.name.asc())
        return list(db.scalars(statement).all())

    def list_active(self, *, db: Session) -> list[Channel]:
        statement = (
            select(Channel)
            .options(selectinload(Channel.epg_entries))
            .where(Channel.is_active.is_(True))
            .order_by(Channel.name.asc())
        )
        return list(db.scalars(statement).all())

    def get_by_id(self, *, db: Session, channel_id: int) -> Channel | None:
        statement = (
            select(Channel)
            .options(selectinload(Channel.epg_entries))
            .where(Channel.id == channel_id)
        )
        return db.scalar(statement)

    def get_by_slug(self, *, db: Session, slug: str) -> Channel | None:
        statement = select(Channel).where(Channel.slug == slug)
        return db.scalar(statement)

    def list_stale(self, *, db: Session, threshold: datetime) -> list[Channel]:
        statement = (
            select(Channel)
            .where(Channel.is_active.is_(True))
            .where((Channel.last_checked_at.is_(None)) | (Channel.last_checked_at < threshold))
            .order_by(Channel.name.asc())
        )
        return list(db.scalars(statement).all())

    def create(self, **kwargs) -> Channel:
        return Channel(**kwargs)

    def delete(self, *, db: Session, channel: Channel) -> None:
        db.delete(channel)
