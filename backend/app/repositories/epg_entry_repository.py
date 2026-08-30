from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, distinct, func, or_, select
from sqlalchemy.orm import Session

from app.models.epg_entry import EPGEntry


@dataclass(slots=True)
class WindowCoverage:
    """How well a time window is already covered by stored EPG data."""

    entry_count: int
    channel_count: int
    newest_updated_at: datetime | None


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

    def window_coverage(
        self,
        *,
        db: Session,
        channel_ids: list[int] | None,
        start: datetime,
        end: datetime,
    ) -> WindowCoverage:
        """Aggregate freshness/coverage for a window without loading every row.

        Used to decide whether a requested EPG window needs re-syncing. Counting in SQL keeps
        this cheap enough to run on every read request.
        """
        statement = (
            select(
                func.count(EPGEntry.id),
                func.count(distinct(EPGEntry.channel_id)),
                func.max(EPGEntry.last_updated_at),
            )
            .where(EPGEntry.end_time > start)
            .where(EPGEntry.start_time < end)
        )
        if channel_ids:
            statement = statement.where(EPGEntry.channel_id.in_(channel_ids))
        entry_count, channel_count, newest = db.execute(statement).one()
        return WindowCoverage(
            entry_count=entry_count or 0,
            channel_count=channel_count or 0,
            newest_updated_at=newest,
        )

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
