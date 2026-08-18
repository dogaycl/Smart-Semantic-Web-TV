from datetime import datetime, timezone
from urllib.parse import urljoin

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
                text = response.text

            if response.status_code >= 400:
                return StreamHealthResult(
                    stream_url=url,
                    is_available=False,
                    error=f"HTTP {response.status_code}",
                    checked_at=checked_at,
                )

            if not self._looks_like_manifest(content_type=content_type, text=text):
                return StreamHealthResult(
                    stream_url=url,
                    is_available=False,
                    error="Response is not an HLS manifest.",
                    checked_at=checked_at,
                )

            if not self._has_cors_headers(response):
                return StreamHealthResult(
                    stream_url=url,
                    is_available=False,
                    error="The HLS manifest is missing browser CORS headers.",
                    checked_at=checked_at,
                )

            media_playlist_url = self._first_media_playlist_url(base_url=str(response.url), text=text) or str(response.url)
            with httpx.Client(
                timeout=self.settings.live_tv_request_timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": "SmartSemanticWebTV/1.0"},
            ) as client:
                media_response = response if media_playlist_url == str(response.url) else client.get(media_playlist_url)
                media_content_type = media_response.headers.get("content-type", "").lower()
                media_text = media_response.text

                if media_response.status_code >= 400:
                    return StreamHealthResult(
                        stream_url=url,
                        is_available=False,
                        error=f"Media playlist HTTP {media_response.status_code}",
                        checked_at=checked_at,
                    )

                if not self._looks_like_manifest(content_type=media_content_type, text=media_text):
                    return StreamHealthResult(
                        stream_url=url,
                        is_available=False,
                        error="Resolved media playlist is not a valid HLS manifest.",
                        checked_at=checked_at,
                    )

                if not self._has_cors_headers(media_response):
                    return StreamHealthResult(
                        stream_url=url,
                        is_available=False,
                        error="The HLS media playlist is missing browser CORS headers.",
                        checked_at=checked_at,
                    )

                segment_url = self._first_segment_url(base_url=str(media_response.url), text=media_text)
                if not segment_url:
                    return StreamHealthResult(
                        stream_url=url,
                        is_available=False,
                        error="The HLS playlist does not expose playable media segments.",
                        checked_at=checked_at,
                    )

                segment_response = client.get(segment_url, headers={"Range": "bytes=0-1"})
                if segment_response.status_code >= 400:
                    return StreamHealthResult(
                        stream_url=url,
                        is_available=False,
                        error=f"HLS segment HTTP {segment_response.status_code}",
                        checked_at=checked_at,
                    )

                if not self._has_cors_headers(segment_response):
                    return StreamHealthResult(
                        stream_url=url,
                        is_available=False,
                        error="The HLS media segment is missing browser CORS headers.",
                        checked_at=checked_at,
                    )

                return StreamHealthResult(
                    stream_url=url,
                    is_available=True,
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

    def _looks_like_manifest(self, *, content_type: str, text: str) -> bool:
        return any(value in content_type for value in HLS_CONTENT_TYPES) or "#EXTM3U" in text[:2048]

    def _has_cors_headers(self, response: httpx.Response) -> bool:
        origin = response.headers.get("access-control-allow-origin", "").strip()
        return bool(origin and origin != "null")

    def _first_media_playlist_url(self, *, base_url: str, text: str) -> str | None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for index, line in enumerate(lines):
            if not line.startswith("#EXT-X-STREAM-INF"):
                continue
            for candidate in lines[index + 1:]:
                if candidate.startswith("#"):
                    continue
                return urljoin(base_url, candidate)
        return None

    def _first_segment_url(self, *, base_url: str, text: str) -> str | None:
        for line in (value.strip() for value in text.splitlines()):
            if not line or line.startswith("#"):
                continue
            return urljoin(base_url, line)
        return None
