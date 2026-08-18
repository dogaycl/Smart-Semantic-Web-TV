from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
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
from app.services.live_tv.catalog import ChannelSeed, enabled_channel_seed_map
from app.services.live_tv.providers.hls_provider import HLSStreamProvider
from app.services.live_tv.providers.youtube_provider import YouTubeLiveProvider

DEMO_PREFERRED_COUNTRIES = ("US", "GB", "CA", "AU", "NZ", "TR")
LANGUAGE_CODE_ALIASES: dict[str, set[str]] = {
    "en": {"en", "eng"},
    "tr": {"tr", "tur"},
}


@dataclass(slots=True)
class IPTVOrgCatalog:
    channels: dict[str, dict[str, Any]] = field(default_factory=dict)
    feeds: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    streams: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    logos: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    guides: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    countries: dict[str, dict[str, Any]] = field(default_factory=dict)


class LiveTVSyncService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.channel_repository = ChannelRepository()
        self.epg_entry_repository = EPGEntryRepository()
        self.epg_service = EPGService()
        self.hls_provider = HLSStreamProvider()
        self.youtube_provider = YouTubeLiveProvider()

    def sync_channels(self, *, db: Session) -> list[Channel]:
        seeds = self._enabled_seed_map()
        catalog = self._fetch_iptv_org_catalog()
        existing_channels = {channel.slug: channel for channel in self.channel_repository.list_all(db=db)}

        for slug, channel in existing_channels.items():
            if slug not in seeds:
                channel.is_active = False

        for slug, seed in seeds.items():
            channel = existing_channels.get(slug)
            channel_id = seed.iptv_org_channel_id or ""
            metadata = catalog.channels.get(channel_id, {})
            language = seed.language or self._catalog_language(channel_id=channel_id, seed=seed, catalog=catalog)
            logo_url = self._catalog_logo(channel_id=channel_id, seed=seed, catalog=catalog) or seed.logo_url
            country = self._catalog_country(metadata=metadata, seed=seed)
            category = seed.category or self._catalog_category(metadata)

            if channel is None:
                channel = self.channel_repository.create(
                    slug=seed.slug,
                    name=seed.name,
                    description=seed.description,
                    category=category,
                    logo_url=logo_url,
                    country=country,
                    language=language,
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
            channel.category = category
            channel.logo_url = logo_url or channel.logo_url
            channel.country = country
            channel.language = language
            channel.source_type = seed.source_type
            channel.iptv_org_channel_id = seed.iptv_org_channel_id
            channel.youtube_handle = seed.youtube_handle
            channel.is_active = seed.is_active
            channel.epg_source_url = seed.epg_source_url
            channel.epg_channel_id = seed.epg_channel_id

        db.commit()

        channels = self.channel_repository.list_active(db=db)
        for channel in channels:
            if channel.source_type != "hls":
                continue
            candidates = self._stream_candidates_for_channel(channel=channel, catalog=catalog, seed=seeds[channel.slug])
            channel.stream_url = channel.stream_url or self._first_candidate_url(candidates)
            channel.quality = channel.quality or self._quality_from_candidates(candidates)

        db.commit()
        return channels

    def refresh_live_status(self, *, db: Session, channels: list[Channel] | None = None) -> list[Channel]:
        channels = channels or self.channel_repository.list_active(db=db)
        seeds = self._enabled_seed_map()
        catalog = self._fetch_iptv_org_catalog()

        checkable: list[tuple[Channel, ChannelSeed]] = []
        for channel in channels:
            seed = seeds.get(channel.slug)
            if seed is None:
                channel.is_active = False
                continue
            checkable.append((channel, seed))

        # Each channel's real stream/live-status check is an independent network round trip
        # (HLS 3-stage manifest verification, or a YouTube Data API lookup) with no shared
        # mutable state, so they are checked concurrently instead of one at a time - with the
        # curated catalog now spanning 20+ channels, a sequential sweep was slow enough to trip
        # the frontend's request timeout whenever the staleness TTL expired mid-session.
        outcomes = self._check_channels_concurrently(checkable, catalog=catalog)

        now = datetime.now(timezone.utc)
        for channel, seed, outcome in outcomes:
            if channel.source_type == "hls":
                candidates, result = outcome
                channel.stream_url = result.stream_url
                channel.quality = self._quality_from_candidates(candidates) or channel.quality
                channel.stream_status = "healthy" if result.is_available else "unavailable"
                channel.stream_error = result.error or (
                    "No browser-playable HLS stream candidate is currently available."
                    if not candidates
                    else None
                )
                channel.live_status = "live" if result.is_available else "unavailable"
                channel.last_checked_at = result.checked_at or now
                continue

            event = outcome
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
            channel.last_checked_at = now

        db.commit()
        return channels

    def _check_channels_concurrently(
        self,
        checkable: list[tuple[Channel, ChannelSeed]],
        *,
        catalog: IPTVOrgCatalog,
    ) -> list[tuple[Channel, ChannelSeed, Any]]:
        if not checkable:
            return []

        def check_one(item: tuple[Channel, ChannelSeed]) -> Any:
            channel, seed = item
            if channel.source_type == "hls":
                candidates = self._stream_candidates_for_channel(channel=channel, catalog=catalog, seed=seed)
                result = self.hls_provider.resolve_stream([candidate["url"] for candidate in candidates])
                return candidates, result
            return self.youtube_provider.get_live_event(
                youtube_handle=seed.youtube_handle,
                youtube_channel_id=channel.youtube_channel_id,
            )

        max_workers = min(10, len(checkable))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            outcomes = list(executor.map(check_one, checkable))
        return [(channel, seed, outcome) for (channel, seed), outcome in zip(checkable, outcomes)]

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
        seeds = self._enabled_seed_map()
        existing_channels = self.channel_repository.list_all(db=db)
        existing_slugs = {channel.slug for channel in existing_channels}
        if self._requires_channel_resync(existing_channels=existing_channels, seeds=seeds, existing_slugs=existing_slugs):
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

    def _requires_channel_resync(
        self,
        *,
        existing_channels: list[Channel],
        seeds: dict[str, ChannelSeed],
        existing_slugs: set[str],
    ) -> bool:
        if len(existing_channels) < len(seeds) or not set(seeds).issubset(existing_slugs):
            return True

        for channel in existing_channels:
            seed = seeds.get(channel.slug)
            if seed is None and channel.is_active:
                return True
            if seed is not None and channel.is_active != seed.is_active:
                return True
        return False

    def _enabled_seed_map(self) -> dict[str, ChannelSeed]:
        return enabled_channel_seed_map(youtube_enabled=bool(self.settings.youtube_api_key))

    def _stream_candidates_for_channel(
        self,
        *,
        channel: Channel,
        catalog: IPTVOrgCatalog,
        seed: ChannelSeed,
    ) -> list[dict[str, Any]]:
        candidate_streams: list[dict[str, Any]] = []

        for url in seed.preferred_stream_urls:
            candidate_streams.append(
                {
                    "url": url,
                    "quality": None,
                    "feed": None,
                    "label": None,
                    "source": "seed",
                }
            )

        channel_id = seed.iptv_org_channel_id or ""
        ranked_streams = sorted(
            catalog.streams.get(channel_id, []),
            key=lambda stream: self._stream_sort_key(channel_id=channel_id, seed=seed, stream=stream, catalog=catalog),
        )

        for stream in ranked_streams:
            url = stream.get("url")
            if not isinstance(url, str) or "m3u8" not in url.lower():
                continue
            if stream.get("referrer") or stream.get("user_agent"):
                continue
            label = str(stream.get("label") or "").lower()
            if "geo-blocked" in label or "geo blocked" in label or "drm" in label:
                continue
            candidate_streams.append(stream)

        deduped: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for candidate in candidate_streams:
            url = candidate.get("url")
            if not isinstance(url, str) or url in seen_urls:
                continue
            seen_urls.add(url)
            deduped.append(candidate)
        return deduped

    def _stream_sort_key(
        self,
        *,
        channel_id: str,
        seed: ChannelSeed,
        stream: dict[str, Any],
        catalog: IPTVOrgCatalog,
    ) -> tuple[int, int, int, int, int, int, str, str]:
        feed = self._feed_for_stream(channel_id=channel_id, stream=stream, catalog=catalog)
        guide_languages = self._guide_languages(channel_id=channel_id, feed_id=stream.get("feed"), catalog=catalog)
        target_language = (seed.language or "en").lower()
        accepted_languages = LANGUAGE_CODE_ALIASES.get(target_language, {target_language})
        url = str(stream.get("url") or "")
        quality = self._quality_rank(stream.get("quality"))
        return (
            0 if self._feed_matches_seed_language(feed, catalog=catalog, seed=seed) else 1,
            0 if self._feed_matches_seed_country(feed, seed) else 1,
            0 if guide_languages & accepted_languages else 1,
            0 if bool(feed.get("is_main")) else 1,
            0 if self._is_preferred_demo_country(feed) else 1,
            0 if url.startswith("https://") else 1,
            -quality,
            url,
        )

    def _quality_from_candidates(self, candidates: list[dict[str, Any]]) -> str | None:
        for candidate in candidates:
            quality = candidate.get("quality")
            if isinstance(quality, str) and quality:
                return quality
        return None

    def _first_candidate_url(self, candidates: list[dict[str, Any]]) -> str | None:
        for candidate in candidates:
            url = candidate.get("url")
            if isinstance(url, str) and url:
                return url
        return None

    def _catalog_category(self, channel_data: dict[str, Any]) -> str | None:
        categories = channel_data.get("categories")
        if isinstance(categories, list) and categories:
            return str(categories[0]).replace("-", " ").title()
        return None

    def _catalog_country(self, *, metadata: dict[str, Any], seed: ChannelSeed) -> str | None:
        country = metadata.get("country")
        if isinstance(country, str) and country:
            return country
        return seed.country

    def _catalog_language(self, *, channel_id: str, seed: ChannelSeed, catalog: IPTVOrgCatalog) -> str | None:
        for feed in self._sorted_feeds_for_seed(channel_id=channel_id, seed=seed, catalog=catalog):
            normalized_languages = [
                self._normalize_language_code(language)
                for language in feed.get("languages") or []
            ]
            if "en" in normalized_languages:
                return "en"
            for language in normalized_languages:
                if language:
                    return language

        country = catalog.countries.get(seed.country or "")
        normalized_country_languages = [
            self._normalize_language_code(language)
            for language in country.get("languages") or []
        ]
        if "en" in normalized_country_languages:
            return "en"
        for language in normalized_country_languages:
            if language:
                return language

        return self._normalize_language_code(seed.language)

    def _catalog_logo(self, *, channel_id: str, seed: ChannelSeed, catalog: IPTVOrgCatalog) -> str | None:
        logos = catalog.logos.get(channel_id, [])
        if not logos:
            return seed.logo_url

        preferred_feed_ids = [feed.get("id") for feed in self._sorted_feeds_for_seed(channel_id=channel_id, seed=seed, catalog=catalog)]
        for feed_id in preferred_feed_ids:
            matched = [logo for logo in logos if logo.get("feed") == feed_id]
            choice = self._pick_logo(matched)
            if choice:
                return choice

        return self._pick_logo(logos) or seed.logo_url

    def _pick_logo(self, logos: list[dict[str, Any]]) -> str | None:
        if not logos:
            return None
        ranked = sorted(
            logos,
            key=lambda logo: (
                0 if logo.get("in_use") else 1,
                -(int(logo.get("width") or 0) * int(logo.get("height") or 0)),
                str(logo.get("url") or ""),
            ),
        )
        for logo in ranked:
            url = logo.get("url")
            if isinstance(url, str) and url:
                return url
        return None

    def _sorted_feeds_for_seed(self, *, channel_id: str, seed: ChannelSeed, catalog: IPTVOrgCatalog) -> list[dict[str, Any]]:
        feeds = catalog.feeds.get(channel_id, [])
        return sorted(
            feeds,
            key=lambda feed: (
                0 if self._feed_matches_seed_language(feed, catalog=catalog, seed=seed) else 1,
                0 if self._feed_matches_seed_country(feed, seed) else 1,
                0 if bool(feed.get("is_main")) else 1,
                0 if self._is_preferred_demo_country(feed) else 1,
                str(feed.get("id") or ""),
            ),
        )

    def _feed_for_stream(self, *, channel_id: str, stream: dict[str, Any], catalog: IPTVOrgCatalog) -> dict[str, Any]:
        feed_id = stream.get("feed")
        for feed in catalog.feeds.get(channel_id, []):
            if feed.get("id") == feed_id:
                return feed
        return {}

    def _feed_matches_seed_language(self, feed: dict[str, Any], *, catalog: IPTVOrgCatalog, seed: ChannelSeed) -> bool:
        target_language = (seed.language or "en").lower()
        accepted_languages = LANGUAGE_CODE_ALIASES.get(target_language, {target_language})
        languages = {str(language).lower() for language in feed.get("languages") or []}
        if languages & accepted_languages:
            return True
        if seed.country:
            country = catalog.countries.get(seed.country, {})
            official_languages = {str(language).lower() for language in country.get("languages") or []}
            return bool(official_languages & accepted_languages)
        return False

    def _feed_matches_seed_country(self, feed: dict[str, Any], seed: ChannelSeed) -> bool:
        if not seed.country:
            return False
        return seed.country.upper() in self._broadcast_countries(feed)

    def _broadcast_countries(self, feed: dict[str, Any]) -> set[str]:
        countries: set[str] = set()
        for area in feed.get("broadcast_area") or []:
            if not isinstance(area, str):
                continue
            if area.startswith("c/") and len(area) >= 4:
                countries.add(area[2:].upper())
        return countries

    def _guide_languages(self, *, channel_id: str, feed_id: Any, catalog: IPTVOrgCatalog) -> set[str]:
        guide_languages: set[str] = set()
        guides = catalog.guides.get(channel_id, [])
        filtered = [guide for guide in guides if guide.get("feed") == feed_id] if feed_id else []
        relevant_guides = filtered or guides
        for guide in relevant_guides:
            language = self._normalize_language_code(guide.get("lang"))
            if language:
                guide_languages.add(language)
        return guide_languages

    def _is_preferred_demo_country(self, feed: dict[str, Any]) -> bool:
        return bool(self._broadcast_countries(feed) & set(DEMO_PREFERRED_COUNTRIES))

    def _normalize_language_code(self, value: Any) -> str | None:
        if not isinstance(value, str) or not value:
            return None
        normalized = value.strip().lower()
        if normalized == "eng":
            return "en"
        if len(normalized) >= 2:
            return normalized[:2]
        return normalized

    def _quality_rank(self, quality: Any) -> int:
        if not isinstance(quality, str) or not quality:
            return 0
        digits = "".join(character for character in quality if character.isdigit())
        if digits:
            return int(digits)
        if quality.lower() == "hd":
            return 720
        return 0

    @lru_cache(maxsize=1)
    def _fetch_iptv_org_catalog(self) -> IPTVOrgCatalog:
        try:
            with httpx.Client(timeout=self.settings.live_tv_request_timeout_seconds * 3, follow_redirects=True) as client:
                channels = client.get("https://iptv-org.github.io/api/channels.json").json()
                feeds = client.get("https://iptv-org.github.io/api/feeds.json").json()
                streams = client.get("https://iptv-org.github.io/api/streams.json").json()
                logos = client.get("https://iptv-org.github.io/api/logos.json").json()
                guides = client.get("https://iptv-org.github.io/api/guides.json").json()
                countries = client.get("https://iptv-org.github.io/api/countries.json").json()
        except httpx.HTTPError:
            return IPTVOrgCatalog()

        channel_map = {
            channel["id"]: channel
            for channel in channels
            if isinstance(channel, dict) and isinstance(channel.get("id"), str)
        }

        def build_multimap(items: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
            mapping: dict[str, list[dict[str, Any]]] = {}
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_key = item.get(key)
                if not isinstance(item_key, str):
                    continue
                mapping.setdefault(item_key, []).append(item)
            return mapping

        country_map = {
            country["code"]: country
            for country in countries
            if isinstance(country, dict) and isinstance(country.get("code"), str)
        }

        return IPTVOrgCatalog(
            channels=channel_map,
            feeds=build_multimap(feeds, "channel"),
            streams=build_multimap(streams, "channel"),
            logos=build_multimap(logos, "channel"),
            guides=build_multimap(guides, "channel"),
            countries=country_map,
        )
