from datetime import datetime

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.models.epg_entry import EPGEntry


class EPGEntryRepository:
    def get_by_id(self, *, db: Session, entry_id: int) -> EPGEntry | None:
        statement = select(EPGEntry).where(EPGEntry.id == entry_id)
        return db.scalar(statement)

    def list_for_window(
        self,
        *,
        db: Session,
        channel_ids: list[int] | None,
        start: datetime,
        end: datetime,
    ) -> list[EPGEntry]:
        statement = (
            select(EPGEntry)
            .where(EPGEntry.end_time > start)
            .where(EPGEntry.start_time < end)
            .order_by(EPGEntry.channel_id.asc(), EPGEntry.start_time.asc())
        )
        if channel_ids:
            statement = statement.where(EPGEntry.channel_id.in_(channel_ids))
        return list(db.scalars(statement).all())

    def get_by_external_id(
        self,
        *,
        db: Session,
        channel_id: int,
        external_id: str,
        source: str,
    ) -> EPGEntry | None:
        statement = (
            select(EPGEntry)
            .where(EPGEntry.channel_id == channel_id)
            .where(EPGEntry.external_id == external_id)
            .where(EPGEntry.source == source)
        )
        return db.scalar(statement)

    def create(self, **kwargs) -> EPGEntry:
        return EPGEntry(**kwargs)

    def delete_outside_window(
        self,
        *,
        db: Session,
        channel_id: int,
        source: str,
        keep_after: datetime,
        keep_before: datetime,
    ) -> None:
        statement = delete(EPGEntry).where(
            EPGEntry.channel_id == channel_id,
            EPGEntry.source == source,
            or_(EPGEntry.end_time <= keep_after, EPGEntry.start_time >= keep_before),
        )
        db.execute(statement)
