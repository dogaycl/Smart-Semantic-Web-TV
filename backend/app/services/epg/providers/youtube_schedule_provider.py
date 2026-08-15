from app.services.live_tv.providers.base import ExternalEPGEntry
from app.services.live_tv.providers.youtube_provider import YouTubeLiveProvider


class YouTubeScheduleProvider:
    def __init__(self) -> None:
        self.youtube_provider = YouTubeLiveProvider()

    def fetch_entries(self, *, youtube_handle: str | None, youtube_channel_id: str | None) -> tuple[str | None, str | None, list[ExternalEPGEntry]]:
        return self.youtube_provider.list_schedule(
            youtube_handle=youtube_handle,
            youtube_channel_id=youtube_channel_id,
        )
