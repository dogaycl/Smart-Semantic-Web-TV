from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.channel import Channel
from app.repositories.channel_repository import ChannelRepository
from app.repositories.epg_entry_repository import EPGEntryRepository
from app.services.epg.service import EPGService
from app.services.live_tv.catalog import LIVE_TV_CHANNEL_SEEDS, ChannelSeed, channel_seed_map
from app.services.live_tv.providers.hls_provider import HLSStreamProvider
from app.services.live_tv.providers.youtube_provider import YouTubeLiveProvider


class LiveTVSyncService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.channel_repository = ChannelRepository()
        self.epg_entry_repository = EPGEntryRepository()
        self.epg_service = EPGService()
        self.hls_provider = HLSStreamProvider()
        self.youtube_provider = YouTubeLiveProvider()

    def sync_channels(self, *, db: Session) -> list[Channel]:
        seeds = channel_seed_map()
        catalog_channels, catalog_streams = self._fetch_iptv_org_catalog()
        existing_channels = {channel.slug: channel for channel in self.channel_repository.list_all(db=db)}

        for slug, seed in seeds.items():
            channel = existing_channels.get(slug)
            metadata = catalog_channels.get(seed.iptv_org_channel_id or "", {})
            if channel is None:
                channel = self.channel_repository.create(
                    slug=seed.slug,
                    name=seed.name,
                    description=seed.description,
                    category=self._catalog_category(metadata) or seed.category,
                    logo_url=metadata.get("logo") or seed.logo_url,
                    country=metadata.get("country") or seed.country,
                    language=self._catalog_language(metadata) or seed.language,
                    source_type=seed.source_type,
                    iptv_org_channel_id=seed.iptv_org_channel_id,
                    youtube_handle=seed.youtube_handle,
                    is_active=seed.is_active,
                    epg_source_url=seed.epg_source_url,
                    epg_channel_id=seed.epg_channel_id,
                )
                db.add(channel)
                continue

            channel.name = seed.name
            channel.description = seed.description
            channel.category = self._catalog_category(metadata) or seed.category
            channel.logo_url = metadata.get("logo") or channel.logo_url or seed.logo_url
            channel.country = metadata.get("country") or seed.country
            channel.language = self._catalog_language(metadata) or seed.language
            channel.source_type = seed.source_type
            channel.iptv_org_channel_id = seed.iptv_org_channel_id
            channel.youtube_handle = seed.youtube_handle
            channel.is_active = seed.is_active
            channel.epg_source_url = seed.epg_source_url
            channel.epg_channel_id = seed.epg_channel_id

        db.commit()
        channels = self.channel_repository.list_active(db=db)
        for channel in channels:
            if channel.source_type == "hls":
                stream_candidates = self._stream_candidates_for_channel(channel, catalog_streams, seeds[channel.slug])
                channel.stream_url = channel.stream_url or (stream_candidates[0] if stream_candidates else None)
        db.commit()
        return channels

    def refresh_live_status(self, *, db: Session, channels: list[Channel] | None = None) -> list[Channel]:
        channels = channels or self.channel_repository.list_active(db=db)
        seeds = channel_seed_map()
        _, catalog_streams = self._fetch_iptv_org_catalog()

        for channel in channels:
            seed = seeds[channel.slug]
            if channel.source_type == "hls":
                candidates = self._stream_candidates_for_channel(channel, catalog_streams, seed)
                result = self.hls_provider.resolve_stream(candidates)
                channel.stream_url = result.stream_url
                channel.quality = channel.quality or self._quality_from_candidates(channel, catalog_streams)
                channel.stream_status = "healthy" if result.is_available else "unavailable"
                channel.stream_error = result.error
                channel.live_status = "live" if result.is_available else "unavailable"
                channel.last_checked_at = result.checked_at or datetime.now(timezone.utc)
                continue

            event = self.youtube_provider.get_live_event(
                youtube_handle=seed.youtube_handle,
                youtube_channel_id=channel.youtube_channel_id,
            )
            channel.youtube_handle = seed.youtube_handle
            channel.youtube_channel_id = event.channel_id or channel.youtube_channel_id
            channel.youtube_video_id = event.video_id
            channel.live_status = event.live_status
            channel.live_title = event.title
            channel.live_description = event.description
            channel.thumbnail_url = event.thumbnail_url
            channel.logo_url = channel.logo_url or event.channel_thumbnail_url
            channel.scheduled_start_time = event.scheduled_start_time or event.actual_start_time
            channel.scheduled_end_time = event.scheduled_end_time
            channel.stream_status = "healthy" if event.video_id and event.live_status in {"live", "upcoming"} else "unavailable"
            channel.stream_error = None if channel.stream_status == "healthy" else event.description
            channel.last_checked_at = datetime.now(timezone.utc)

        db.commit()
        return channels

    def sync_epg(
        self,
        *,
        db: Session,
        window_start: datetime,
        window_end: datetime,
    ) -> None:
        channels = self.channel_repository.list_active(db=db)
        self.epg_service.sync_epg(
            db=db,
            channels=channels,
            window_start=window_start,
            window_end=window_end,
        )

    def ensure_ready(
        self,
        *,
        db: Session,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
    ) -> None:
        expected = len(LIVE_TV_CHANNEL_SEEDS)
        if self.channel_repository.count(db=db) < expected:
            self.sync_channels(db=db)

        if not self.settings.live_tv_auto_sync:
            return

        threshold = datetime.now(timezone.utc) - timedelta(minutes=self.settings.live_tv_status_ttl_minutes)
        stale_channels = self.channel_repository.list_stale(db=db, threshold=threshold)
        if stale_channels:
            self.refresh_live_status(db=db, channels=stale_channels)

        if window_start is None or window_end is None:
            window_start, window_end = self.epg_service.default_window(hours=self.settings.live_tv_default_epg_window_hours)

        active_channels = self.channel_repository.list_active(db=db)
        entries = self.epg_entry_repository.list_for_window(
            db=db,
            channel_ids=[channel.id for channel in active_channels],
            start=window_start,
            end=window_end,
        )
        if not entries:
            self.sync_epg(db=db, window_start=window_start, window_end=window_end)

    def _stream_candidates_for_channel(self, channel: Channel, catalog_streams: dict[str, list[dict[str, Any]]], seed: ChannelSeed) -> list[str]:
        candidate_urls: list[str] = []
        candidate_urls.extend(seed.preferred_stream_urls)
        for stream in catalog_streams.get(seed.iptv_org_channel_id or "", []):
            url = stream.get("url")
            if not isinstance(url, str):
                continue
            if "m3u8" not in url:
                continue
            label = (stream.get("label") or "").lower()
            if "geo-blocked" in label:
                continue
            candidate_urls.append(url)
        deduped: list[str] = []
        for url in candidate_urls:
            if url not in deduped:
                deduped.append(url)
        return deduped

    def _quality_from_candidates(self, channel: Channel, catalog_streams: dict[str, list[dict[str, Any]]]) -> str | None:
        for stream in catalog_streams.get(channel.iptv_org_channel_id or "", []):
            quality = stream.get("quality")
            if isinstance(quality, str) and quality:
                return quality
        return channel.quality

    def _catalog_category(self, channel_data: dict[str, Any]) -> str | None:
        categories = channel_data.get("categories")
        if isinstance(categories, list) and categories:
            return str(categories[0]).replace("-", " ").title()
        return None

    def _catalog_language(self, channel_data: dict[str, Any]) -> str | None:
        languages = channel_data.get("languages")
        if isinstance(languages, list) and languages:
            return str(languages[0])
        return None

    @lru_cache(maxsize=1)
    def _fetch_iptv_org_catalog(self) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
        try:
            with httpx.Client(timeout=self.settings.live_tv_request_timeout_seconds * 3, follow_redirects=True) as client:
                channels = client.get("https://iptv-org.github.io/api/channels.json").json()
                streams = client.get("https://iptv-org.github.io/api/streams.json").json()
        except httpx.HTTPError:
            return {}, {}

        channel_map: dict[str, dict[str, Any]] = {
            channel["id"]: channel
            for channel in channels
            if isinstance(channel, dict) and isinstance(channel.get("id"), str)
        }
        stream_map: dict[str, list[dict[str, Any]]] = {}
        for stream in streams:
            channel_id = stream.get("channel")
            if not isinstance(channel_id, str):
                continue
            stream_map.setdefault(channel_id, []).append(stream)

        return channel_map, stream_map
