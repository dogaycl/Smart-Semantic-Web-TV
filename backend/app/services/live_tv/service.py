from datetime import datetime, timezone

from app.models.channel import Channel
from app.models.epg_entry import EPGEntry
from app.schemas.live_tv import (
    ChannelLiveRead,
    ChannelPlaybackRead,
    ChannelProgramRead,
    ChannelRead,
)


class LiveTVService:
    def build_channel_read(self, channel: Channel) -> ChannelRead:
        current_program, next_program = self._get_current_and_next(channel.epg_entries)
        return ChannelRead(
            id=channel.id,
            slug=channel.slug,
            name=channel.name,
            description=channel.description,
            category=channel.category,
            logo_url=channel.logo_url,
            country=channel.country,
            language=channel.language,
            source_type=channel.source_type,
            youtube_channel_id=channel.youtube_channel_id,
            youtube_video_id=channel.youtube_video_id,
            stream_url=channel.stream_url,
            quality=channel.quality,
            is_active=channel.is_active,
            stream_status=channel.stream_status,
            stream_error=channel.stream_error,
            epg_channel_id=channel.epg_channel_id,
            last_checked_at=channel.last_checked_at,
            live_status=channel.live_status,
            live_title=channel.live_title,
            live_description=channel.live_description,
            thumbnail_url=channel.thumbnail_url,
            scheduled_start_time=channel.scheduled_start_time,
            scheduled_end_time=channel.scheduled_end_time,
            playback=self._build_playback(channel),
            current_program=current_program,
            next_program=next_program,
        )

    def build_channel_live_read(self, channel: Channel) -> ChannelLiveRead:
        current_program, next_program = self._get_current_and_next(channel.epg_entries)
        return ChannelLiveRead(
            id=channel.id,
            slug=channel.slug,
            name=channel.name,
            source_type=channel.source_type,
            live_status=channel.live_status,
            live_title=channel.live_title,
            live_description=channel.live_description,
            thumbnail_url=channel.thumbnail_url,
            youtube_channel_id=channel.youtube_channel_id,
            youtube_video_id=channel.youtube_video_id,
            stream_url=channel.stream_url,
            quality=channel.quality,
            scheduled_start_time=channel.scheduled_start_time,
            scheduled_end_time=channel.scheduled_end_time,
            playback=self._build_playback(channel),
            current_program=current_program,
            next_program=next_program,
        )

    def _build_playback(self, channel: Channel) -> ChannelPlaybackRead:
        if channel.source_type == "youtube" and channel.youtube_video_id and channel.live_status in {"live", "upcoming"}:
            return ChannelPlaybackRead(
                type="youtube",
                youtube_video_id=channel.youtube_video_id,
                embed_url=f"https://www.youtube.com/embed/{channel.youtube_video_id}?autoplay=1&playsinline=1&rel=0",
            )

        if channel.source_type == "hls" and channel.stream_url and channel.stream_status == "healthy":
            return ChannelPlaybackRead(
                type="hls",
                stream_url=channel.stream_url,
            )

        return ChannelPlaybackRead(type="unavailable")

    def _get_current_and_next(self, entries: list[EPGEntry]) -> tuple[ChannelProgramRead | None, ChannelProgramRead | None]:
        now = datetime.now(timezone.utc)
        upcoming = sorted(entries, key=lambda entry: self._normalize_datetime(entry.start_time))
        current_program: ChannelProgramRead | None = None
        next_program: ChannelProgramRead | None = None

        for entry in upcoming:
            normalized = ChannelProgramRead.model_validate(entry)
            start_time = self._normalize_datetime(entry.start_time)
            end_time = self._normalize_datetime(entry.end_time)
            if start_time <= now < end_time and current_program is None:
                current_program = normalized
                continue
            if start_time > now:
                next_program = normalized
                break

        if current_program is None and upcoming:
            next_program = next_program or ChannelProgramRead.model_validate(upcoming[0])

        return current_program, next_program

    def _normalize_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
