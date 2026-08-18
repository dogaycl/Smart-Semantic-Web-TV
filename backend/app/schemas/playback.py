from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, HttpUrl

from app.schemas.catalog import CatalogVideoRead


PlaybackSourceType = Literal["hls", "mp4", "youtube", "external", "none"]
WatchActionType = Literal["watch_now", "watch_trailer", "not_available"]


class PlaybackCapabilitiesRead(BaseModel):
    can_play: bool
    can_pause: bool
    can_seek: bool
    can_report_progress: bool
    can_fullscreen: bool
    supports_seek: bool
    supports_state_tracking: bool


class PlaybackSourceRead(BaseModel):
    id: int
    name: str
    type: PlaybackSourceType
    playback_url: HttpUrl | None = None
    embed_url: HttpUrl | None = None
    external_video_id: str | None = None
    quality: str | None = None
    language: str | None = None
    is_primary: bool
    provider_name: str | None = None
    provider_url: HttpUrl | None = None
    license_note: str | None = None
    source_note: str | None = None
    last_checked_at: datetime | None = None
    error: str | None = None
    capabilities: PlaybackCapabilitiesRead


class PlaybackFallbackRead(BaseModel):
    type: Literal["watch_trailer", "not_available"]
    label: str
    message: str | None = None
    embed_url: HttpUrl | None = None


class PlaybackProgressRead(BaseModel):
    watch_position_seconds: int
    total_watched_duration_seconds: int
    is_completed: bool
    last_watched_at: datetime


class CatalogPlaybackResponse(BaseModel):
    content_id: int
    slug: str
    title: str
    playback_available: bool
    watch_action: WatchActionType
    message: str
    primary_source: PlaybackSourceRead | None = None
    sources: list[PlaybackSourceRead]
    trailer: CatalogVideoRead | None = None
    fallback: PlaybackFallbackRead | None = None
    watch_progress: PlaybackProgressRead | None = None
