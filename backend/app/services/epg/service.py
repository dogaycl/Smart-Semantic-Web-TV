from datetime import datetime, timedelta, timezone
from collections import defaultdict

import httpx
from sqlalchemy.orm import Session

from app.models.channel import Channel
from app.repositories.channel_repository import ChannelRepository
from app.repositories.epg_entry_repository import EPGEntryRepository
from app.schemas.live_tv import EPGChannelRead, EPGEntryRead, EPGWindowResponse
from app.services.epg.providers.xmltv_provider import XMLTVProvider
from app.services.epg.providers.youtube_schedule_provider import YouTubeScheduleProvider
from app.services.live_tv.service import LiveTVService


class EPGService:
    def __init__(self) -> None:
        self.channel_repository = ChannelRepository()
        self.epg_entry_repository = EPGEntryRepository()
        self.xmltv_provider = XMLTVProvider()
        self.youtube_schedule_provider = YouTubeScheduleProvider()
        self.live_tv_service = LiveTVService()

    def sync_epg(
        self,
        *,
        db: Session,
        channels: list[Channel],
        window_start: datetime,
        window_end: datetime,
    ) -> None:
        hls_channels_by_source: dict[str, list[Channel]] = defaultdict(list)
        for channel in channels:
            if channel.source_type == "hls" and channel.epg_source_url and channel.epg_channel_id:
                hls_channels_by_source[channel.epg_source_url].append(channel)

        for source_url, source_channels in hls_channels_by_source.items():
            try:
                matched = self.xmltv_provider.fetch_entries(
                    source_url=source_url,
                    channel_ids={channel.epg_channel_id for channel in source_channels if channel.epg_channel_id},
                    window_start=window_start,
                    window_end=window_end,
                )
            except httpx.HTTPError:
                matched = {}
            for channel in source_channels:
                if not channel.epg_channel_id:
                    continue
                self._replace_channel_entries(
                    db=db,
                    channel=channel,
                    entries=matched.get(channel.epg_channel_id, []),
                    source="xmltv",
                    delete_from=window_start - timedelta(hours=2),
                )

        youtube_channels = [channel for channel in channels if channel.source_type == "youtube"]
        for channel in youtube_channels:
            _, thumbnail_url, entries = self.youtube_schedule_provider.fetch_entries(
                youtube_handle=channel.youtube_handle,
                youtube_channel_id=channel.youtube_channel_id,
            )
            if thumbnail_url and not channel.logo_url:
                channel.logo_url = thumbnail_url
            self._replace_channel_entries(
                db=db,
                channel=channel,
                entries=entries,
                source="youtube",
                delete_from=window_start - timedelta(hours=2),
            )

        db.commit()

    def get_window(
        self,
        *,
        db: Session,
        channels: list[Channel],
        start: datetime,
        end: datetime,
        slot_minutes: int = 60,
    ) -> EPGWindowResponse:
        entries = self.epg_entry_repository.list_for_window(
            db=db,
            channel_ids=[channel.id for channel in channels],
            start=start,
            end=end,
        )
        entries_by_channel: dict[int, list] = defaultdict(list)
        for entry in entries:
            entries_by_channel[entry.channel_id].append(entry)

        slots: list[datetime] = []
        cursor = start
        while cursor < end:
            slots.append(cursor)
            cursor += timedelta(minutes=slot_minutes)

        return EPGWindowResponse(
            start=start,
            end=end,
            slot_minutes=slot_minutes,
            slots=slots,
            channels=[
                EPGChannelRead(
                    channel=self.live_tv_service.build_channel_read(channel),
                    entries=[EPGEntryRead.model_validate(entry) for entry in entries_by_channel.get(channel.id, [])],
                )
                for channel in channels
            ],
        )

    def default_window(self, *, hours: int) -> tuple[datetime, datetime]:
        start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=hours)
        return start, end

    def _replace_channel_entries(self, *, db: Session, channel: Channel, entries, source: str, delete_from: datetime) -> None:
        existing = {
            entry.external_id: entry
            for entry in self.epg_entry_repository.list_for_window(
                db=db,
                channel_ids=[channel.id],
                start=delete_from,
                end=delete_from + timedelta(days=7),
            )
            if entry.source == source
        }
        incoming_ids = {entry.external_id for entry in entries}
        for external_id, existing_entry in existing.items():
            if external_id not in incoming_ids:
                db.delete(existing_entry)

        for entry in entries:
            existing_entry = self.epg_entry_repository.get_by_external_id(
                db=db,
                channel_id=channel.id,
                external_id=entry.external_id,
                source=entry.source,
            )
            if existing_entry is None:
                existing_entry = self.epg_entry_repository.create(
                    channel_id=channel.id,
                    external_id=entry.external_id,
                    title=entry.title,
                    description=entry.description,
                    category=entry.category,
                    start_time=entry.start_time,
                    end_time=entry.end_time,
                    source=entry.source,
                )
                db.add(existing_entry)
                continue

            existing_entry.title = entry.title
            existing_entry.description = entry.description
            existing_entry.category = entry.category
            existing_entry.start_time = entry.start_time
            existing_entry.end_time = entry.end_time
            existing_entry.last_updated_at = datetime.now(timezone.utc)
