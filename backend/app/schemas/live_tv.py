from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


SourceType = Literal["youtube", "hls"]
PlaybackType = Literal["youtube", "hls", "unavailable"]
LiveStatus = Literal["live", "upcoming", "offline", "unavailable", "unknown"]


class ChannelProgramRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    title: str
    description: str | None = None
    category: str | None = None
    image_url: str | None = None
    start_time: datetime
    end_time: datetime
    source: str

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def normalize_program_datetimes(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class ChannelPlaybackRead(BaseModel):
    type: PlaybackType
    youtube_video_id: str | None = None
    embed_url: HttpUrl | None = None
    stream_url: HttpUrl | None = None


class ChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str | None = None
    category: str | None = None
    logo_url: HttpUrl | None = None
    country: str | None = None
    language: str | None = None
    source_type: SourceType
    youtube_channel_id: str | None = None
    youtube_video_id: str | None = None
    stream_url: HttpUrl | None = None
    quality: str | None = None
    is_active: bool
    stream_status: str
    stream_error: str | None = None
    epg_channel_id: str | None = None
    last_checked_at: datetime | None = None
    live_status: LiveStatus
    live_title: str | None = None
    live_description: str | None = None
    thumbnail_url: HttpUrl | None = None
    scheduled_start_time: datetime | None = None
    scheduled_end_time: datetime | None = None
    playback: ChannelPlaybackRead
    current_program: ChannelProgramRead | None = None
    next_program: ChannelProgramRead | None = None


class ChannelLiveRead(BaseModel):
    id: int
    slug: str
    name: str
    source_type: SourceType
    live_status: LiveStatus
    live_title: str | None = None
    live_description: str | None = None
    thumbnail_url: HttpUrl | None = None
    youtube_channel_id: str | None = None
    youtube_video_id: str | None = None
    stream_url: HttpUrl | None = None
    quality: str | None = None
    scheduled_start_time: datetime | None = None
    scheduled_end_time: datetime | None = None
    playback: ChannelPlaybackRead
    current_program: ChannelProgramRead | None = None
    next_program: ChannelProgramRead | None = None


class EPGEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel_id: int
    external_id: str
    title: str
    description: str | None = None
    category: str | None = None
    image_url: str | None = None
    start_time: datetime
    end_time: datetime
    source: str
    last_updated_at: datetime

    @field_validator("start_time", "end_time", "last_updated_at", mode="before")
    @classmethod
    def normalize_entry_datetimes(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class EPGChannelRead(BaseModel):
    channel: ChannelRead
    entries: list[EPGEntryRead] = Field(default_factory=list)


class EPGWindowResponse(BaseModel):
    start: datetime
    end: datetime
    slot_minutes: int = 60
    slots: list[datetime]
    channels: list[EPGChannelRead]

    @field_validator("start", "end")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
