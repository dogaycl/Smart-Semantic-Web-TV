from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

# "check_failed" means the provider could not determine the state (quota exhausted, timeout,
# upstream 5xx). It is deliberately distinct from "offline"/"unavailable", which are real
# answers about the channel - callers must preserve the previous known state instead of
# downgrading a working channel because of a transient provider error.
LiveStatus = Literal["live", "upcoming", "offline", "unavailable", "check_failed", "unknown"]


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
    # True when the check itself could not complete (DNS failure, connection timeout,
    # upstream 5xx/429) rather than the stream giving a real "not playable" answer
    # (404, not-a-manifest, missing CORS). Callers keep the last known good status on a
    # check failure instead of marking a working channel dead because of a network blip.
    check_failed: bool = False


@dataclass(slots=True)
class ExternalEPGEntry:
    external_id: str
    title: str
    start_time: datetime
    end_time: datetime
    source: str
    description: str | None = None
    category: str | None = None
    image_url: str | None = None
    payload: dict[str, str] = field(default_factory=dict)
