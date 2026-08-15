from datetime import datetime, timezone

import httpx

from app.core.config import get_settings
from app.services.live_tv.providers.base import StreamHealthResult

HLS_CONTENT_TYPES = (
    "application/vnd.apple.mpegurl",
    "application/x-mpegurl",
    "audio/mpegurl",
    "audio/x-mpegurl",
)


class HLSStreamProvider:
    def __init__(self) -> None:
        self.settings = get_settings()

    def check_stream(self, url: str) -> StreamHealthResult:
        checked_at = datetime.now(timezone.utc)
        try:
            with httpx.Client(
                timeout=self.settings.live_tv_request_timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": "SmartSemanticWebTV/1.0"},
            ) as client:
                response = client.get(url)
                content_type = response.headers.get("content-type", "").lower()
                text = response.text[:512]

            if response.status_code >= 400:
                return StreamHealthResult(
                    stream_url=url,
                    is_available=False,
                    error=f"HTTP {response.status_code}",
                    checked_at=checked_at,
                )

            if any(value in content_type for value in HLS_CONTENT_TYPES) or "#EXTM3U" in text:
                return StreamHealthResult(
                    stream_url=url,
                    is_available=True,
                    checked_at=checked_at,
                )

            return StreamHealthResult(
                stream_url=url,
                is_available=False,
                error="Response is not an HLS manifest.",
                checked_at=checked_at,
            )
        except httpx.HTTPError as exc:
            return StreamHealthResult(
                stream_url=url,
                is_available=False,
                error=str(exc),
                checked_at=checked_at,
            )

    def resolve_stream(self, candidates: list[str]) -> StreamHealthResult:
        last_result = StreamHealthResult(stream_url=None, is_available=False, error="No candidate stream URLs configured.")
        for url in candidates:
            result = self.check_stream(url)
            if result.is_available:
                return result
            last_result = result
        return last_result
