from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import get_settings
from app.models.playback_source import PlaybackSource


class PlaybackHealthService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def refresh_source_if_stale(self, source: PlaybackSource) -> bool:
        if not self.settings.playback_health_checks_enabled:
            return False
        if source.source_type not in {"hls", "mp4"} or not source.playback_url:
            if source.last_checked_at is None:
                source.last_checked_at = datetime.now(timezone.utc)
                source.last_error = None
                return True
            return False

        now = datetime.now(timezone.utc)
        if source.last_checked_at and source.last_checked_at >= now - timedelta(minutes=self.settings.playback_health_ttl_minutes):
            return False

        try:
            response = httpx.get(
                source.playback_url,
                headers={"Range": "bytes=0-0"},
                follow_redirects=True,
                timeout=self.settings.playback_request_timeout_seconds,
            )
            if response.status_code not in {200, 206}:
                raise httpx.HTTPStatusError(
                    f"Unexpected status {response.status_code}",
                    request=response.request,
                    response=response,
                )
            source.last_error = None
        except httpx.HTTPError:
            source.last_error = "Playback source is currently unavailable."
        source.last_checked_at = now
        return True
