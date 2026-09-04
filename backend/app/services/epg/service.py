from datetime import datetime, timedelta, timezone
from collections import defaultdict

import httpx
from sqlalchemy.orm import Session

from app.models.channel import Channel
from app.repositories.channel_repository import ChannelRepository
from app.repositories.epg_entry_repository import EPGEntryRepository
from app.schemas.live_tv import EPGChannelRead, EPGEntryRead, EPGWindowResponse
from app.services.epg.providers.tr_synopsis_provider import TRSynopsisProvider, normalize_title
from app.services.epg.providers.xmltv_provider import XMLTVProvider
from app.services.epg.providers.youtube_schedule_provider import YouTubeScheduleProvider
from app.services.live_tv.catalog import channel_seed_map
from app.services.live_tv.service import LiveTVService


class EPGService:
    def __init__(self) -> None:
        self.channel_repository = ChannelRepository()
        self.epg_entry_repository = EPGEntryRepository()
        self.xmltv_provider = XMLTVProvider()
        self.youtube_schedule_provider = YouTubeScheduleProvider()
        self.tr_synopsis_provider = TRSynopsisProvider()
        self.live_tv_service = LiveTVService()

    def sync_epg(
        self,
        *,
        db: Session,
        channels: list[Channel],
        window_start: datetime,
        window_end: datetime,
    ) -> None:
        # Any channel with a real XMLTV mapping gets its schedule from XMLTV, regardless of how
        # it is played back. Restricting this to source_type == "hls" previously meant a channel
        # streamed via YouTube could never show a published schedule even when the broadcaster
        # publishes one (NTV, for example, has hundreds of real programmes in the TR feed).
        channels_by_source: dict[str, list[Channel]] = defaultdict(list)
        for channel in channels:
            if channel.epg_source_url and channel.epg_channel_id:
                channels_by_source[channel.epg_source_url].append(channel)

        xmltv_mapped_ids: set[int] = set()
        for source_url, source_channels in channels_by_source.items():
            try:
                matched = self.xmltv_provider.fetch_entries(
                    source_url=source_url,
                    channel_ids={channel.epg_channel_id for channel in source_channels if channel.epg_channel_id},
                    window_start=window_start,
                    window_end=window_end,
                )
            except httpx.HTTPError:
                # A failed download must not be read as "the schedule is now empty", or the
                # prune below would wipe good data. Skip this source and keep what we have.
                continue
            for channel in source_channels:
                if not channel.epg_channel_id:
                    continue
                xmltv_mapped_ids.add(channel.id)
                self._replace_channel_entries(
                    db=db,
                    channel=channel,
                    entries=matched.get(channel.epg_channel_id, []),
                    source="xmltv",
                    # The provider filters incoming entries to exactly this window, so the
                    # authoritative range is the window - NOT a fixed 7-day span. Pruning wider
                    # than the fetched range deletes other days' schedules whenever a single day
                    # is synced, which breaks EPG date navigation and orphans saved plan links.
                    prune_start=window_start,
                    prune_end=window_end,
                )

        # YouTube schedules are only a fallback for channels with no published XMLTV listing.
        # Each lookup costs ~200 YouTube quota units, so this also keeps the daily quota intact.
        youtube_channels = [
            channel
            for channel in channels
            if channel.source_type == "youtube" and channel.id not in xmltv_mapped_ids
        ]
        now = datetime.now(timezone.utc)
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
                # This provider ignores the window and returns the whole forward schedule, so
                # incoming really is authoritative across a wide range.
                prune_start=now - timedelta(hours=2),
                prune_end=now + timedelta(days=7),
            )

        # The free XMLTV feeds carry no <desc> for Turkish channels (and do not list a few of
        # them at all). Pull descriptions - and, where there is no feed entry, whole schedules -
        # from the broadcaster's own "yayın akışı" page.
        self._apply_broadcaster_schedules(
            db=db,
            channels=channels,
            window_start=window_start,
            window_end=window_end,
        )

        db.commit()

    def _apply_broadcaster_schedules(
        self,
        *,
        db: Session,
        channels: list[Channel],
        window_start: datetime,
        window_end: datetime,
    ) -> None:
        seeds = channel_seed_map()
        synopsis_cache: dict[str, dict[str, str]] = {}
        now = datetime.now(timezone.utc)
        for channel in channels:
            seed = seeds.get(channel.slug)
            synopsis_url = seed.synopsis_url if seed else None
            if not synopsis_url:
                continue

            if not channel.epg_channel_id:
                # No XMLTV listing for this channel - the broadcaster page is the whole source.
                broadcaster_entries = self.tr_synopsis_provider.fetch_entries(
                    source_url=synopsis_url,
                    window_start=window_start,
                    window_end=window_end,
                )
                if broadcaster_entries:
                    self._replace_channel_entries(
                        db=db,
                        channel=channel,
                        entries=broadcaster_entries,
                        source="broadcaster",
                        prune_start=window_start,
                        prune_end=window_end,
                    )
                continue

            # XMLTV-mapped channel: keep the feed's times, add the missing descriptions.
            if synopsis_url not in synopsis_cache:
                synopsis_cache[synopsis_url] = self.tr_synopsis_provider.fetch_synopses(source_url=synopsis_url)
            synopses = synopsis_cache[synopsis_url]
            if not synopses:
                continue
            for entry in self.epg_entry_repository.list_for_window(
                db=db,
                channel_ids=[channel.id],
                start=window_start,
                end=window_end,
            ):
                # A synopsis describes the programme, so it applies to every airing of that title.
                match = synopses.get(normalize_title(entry.title))
                if match and (entry.description or "") != match:
                    entry.description = match
                    entry.last_updated_at = now

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

    def _replace_channel_entries(
        self,
        *,
        db: Session,
        channel: Channel,
        entries,
        source: str,
        prune_start: datetime,
        prune_end: datetime,
    ) -> None:
        """Upsert `entries` for one channel, pruning only within [prune_start, prune_end).

        The prune range must match the range the caller's provider actually fetched, otherwise
        syncing one day silently deletes the schedule for every other day.
        """
        existing = {
            entry.external_id: entry
            for entry in self.epg_entry_repository.list_for_window(
                db=db,
                channel_ids=[channel.id],
                start=prune_start,
                end=prune_end,
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
                    image_url=getattr(entry, "image_url", None),
                    start_time=entry.start_time,
                    end_time=entry.end_time,
                    source=entry.source,
                )
                db.add(existing_entry)
                continue

            existing_entry.title = entry.title
            existing_entry.description = entry.description
            existing_entry.category = entry.category
            existing_entry.image_url = getattr(entry, "image_url", None)
            existing_entry.start_time = entry.start_time
            existing_entry.end_time = entry.end_time
            existing_entry.last_updated_at = datetime.now(timezone.utc)
