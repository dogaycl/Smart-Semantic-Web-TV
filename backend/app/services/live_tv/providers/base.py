from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

LiveStatus = Literal["live", "upcoming", "offline", "unavailable", "unknown"]


@dataclass(slots=True)
class ExternalLiveEvent:
    title: str | None = None
    description: str | None = None
    video_id: str | None = None
    thumbnail_url: str | None = None
    live_status: LiveStatus = "unknown"
    scheduled_start_time: datetime | None = None
    scheduled_end_time: datetime | None = None
    actual_start_time: datetime | None = None
    embed_url: str | None = None
    channel_id: str | None = None
    channel_thumbnail_url: str | None = None


@dataclass(slots=True)
class StreamHealthResult:
    stream_url: str | None
    is_available: bool
    quality: str | None = None
    error: str | None = None
    checked_at: datetime | None = None


@dataclass(slots=True)
class ExternalEPGEntry:
    external_id: str
    title: str
    start_time: datetime
    end_time: datetime
    source: str
    description: str | None = None
    category: str | None = None
    payload: dict[str, str] = field(default_factory=dict)
