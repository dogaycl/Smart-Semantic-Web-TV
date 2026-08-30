from datetime import datetime, timedelta

import httpx

from app.core.config import get_settings
from app.core.redaction import redact_secrets
from app.services.live_tv.providers.base import ExternalEPGEntry, ExternalLiveEvent, LiveStatus

# YouTube Data API quota costs: search.list = 100 units, videos.list/channels.list = 1 unit,
# against a default 10,000 units/day. Re-searching every channel on every health sweep
# exhausts the quota within the hour and makes every YouTube channel read "Unavailable",
# so a known-good live video is re-verified with videos.list instead.
TRANSIENT_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}


class YouTubeLiveProvider:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = "https://www.googleapis.com/youtube/v3"

    def is_configured(self) -> bool:
        return bool(self.settings.youtube_api_key)

    def get_live_event(
        self,
        *,
        youtube_handle: str | None,
        youtube_channel_id: str | None,
        known_video_id: str | None = None,
    ) -> ExternalLiveEvent:
        if not self.is_configured():
            return ExternalLiveEvent(live_status="unavailable", description="YOUTUBE_API_KEY is not configured.")

        try:
            # Cheap path (1 quota unit): a previously resolved broadcast is usually still the
            # current one for a 24/7 simulcast, so verify it before paying for a search.
            if known_video_id:
                cached = self._hydrate_video(known_video_id)
                if cached.live_status in {"live", "upcoming"}:
                    cached.channel_id = youtube_channel_id
                    return cached

            resolved_channel_id, channel_thumbnail_url = self._resolve_channel(youtube_handle=youtube_handle, youtube_channel_id=youtube_channel_id)
            if resolved_channel_id is None:
                return ExternalLiveEvent(live_status="unavailable", description="YouTube channel could not be resolved.")

            live_items = self._search_channel_events(channel_id=resolved_channel_id, event_type="live")
            if live_items:
                event = self._hydrate_video(live_items[0]["id"]["videoId"])
                event.live_status = "live"
                event.channel_id = resolved_channel_id
                event.channel_thumbnail_url = channel_thumbnail_url
                return event

            upcoming_items = self._search_channel_events(channel_id=resolved_channel_id, event_type="upcoming")
            if upcoming_items:
                event = self._hydrate_video(upcoming_items[0]["id"]["videoId"])
                event.live_status = "upcoming"
                event.channel_id = resolved_channel_id
                event.channel_thumbnail_url = channel_thumbnail_url
                return event

            return ExternalLiveEvent(
                live_status="offline",
                channel_id=resolved_channel_id,
                channel_thumbnail_url=channel_thumbnail_url,
            )
        except httpx.HTTPError as exc:
            return ExternalLiveEvent(
                live_status=self._failure_status(exc),
                description=redact_secrets(str(exc)),
            )

    def list_schedule(
        self,
        *,
        youtube_handle: str | None,
        youtube_channel_id: str | None,
    ) -> tuple[str | None, str | None, list[ExternalEPGEntry]]:
        if not self.is_configured():
            return youtube_channel_id, None, []

        try:
            resolved_channel_id, channel_thumbnail_url = self._resolve_channel(youtube_handle=youtube_handle, youtube_channel_id=youtube_channel_id)
            if resolved_channel_id is None:
                return None, channel_thumbnail_url, []

            events: list[ExternalEPGEntry] = []
            for event_type in ("live", "upcoming"):
                items = self._search_channel_events(channel_id=resolved_channel_id, event_type=event_type)
                for item in items[:5]:
                    hydrated = self._hydrate_video(item["id"]["videoId"])
                    start_time = hydrated.actual_start_time or hydrated.scheduled_start_time
                    if start_time is None:
                        continue
                    end_time = hydrated.scheduled_end_time or (start_time + timedelta(hours=1))
                    events.append(
                        ExternalEPGEntry(
                            external_id=hydrated.video_id or item["id"]["videoId"],
                            title=hydrated.title or item["snippet"]["title"],
                            description=hydrated.description,
                            category="Live Stream",
                            start_time=start_time,
                            end_time=end_time,
                            source="youtube",
                        )
                    )

            deduped: dict[str, ExternalEPGEntry] = {}
            for event in events:
                deduped[event.external_id] = event
            return resolved_channel_id, channel_thumbnail_url, sorted(deduped.values(), key=lambda entry: entry.start_time)
        except httpx.HTTPError:
            return youtube_channel_id, None, []

    def _resolve_channel(self, *, youtube_handle: str | None, youtube_channel_id: str | None) -> tuple[str | None, str | None]:
        params = {"part": "id,snippet", "key": self.settings.youtube_api_key}
        if youtube_channel_id:
            params["id"] = youtube_channel_id
        elif youtube_handle:
            params["forHandle"] = youtube_handle
        else:
            return None, None

        data = self._get("/channels", params=params)
        items = data.get("items", [])
        if not items:
            return None, None
        item = items[0]
        thumbnails = item.get("snippet", {}).get("thumbnails", {})
        thumbnail_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
        )
        return item.get("id"), thumbnail_url

    def _search_channel_events(self, *, channel_id: str, event_type: str) -> list[dict]:
        data = self._get(
            "/search",
            params={
                "part": "snippet",
                "channelId": channel_id,
                "eventType": event_type,
                "maxResults": 5,
                "order": "date",
                "type": "video",
                "videoEmbeddable": "true",
                "key": self.settings.youtube_api_key,
            },
        )
        return data.get("items", [])

    def _hydrate_video(self, video_id: str) -> ExternalLiveEvent:
        data = self._get(
            "/videos",
            params={
                "part": "snippet,liveStreamingDetails,status",
                "id": video_id,
                "key": self.settings.youtube_api_key,
            },
        )
        items = data.get("items", [])
        if not items:
            return ExternalLiveEvent(video_id=video_id, live_status="unavailable")

        item = items[0]
        if item.get("status", {}).get("embeddable") is False:
            return ExternalLiveEvent(
                video_id=video_id,
                live_status="unavailable",
                description="YouTube video is not embeddable.",
            )

        snippet = item.get("snippet", {})
        live_details = item.get("liveStreamingDetails", {})
        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
        )
        # Derive the state from the video itself so a cached video id can be re-verified
        # without a search. Search-based callers still overwrite live_status explicitly.
        broadcast = snippet.get("liveBroadcastContent")
        if live_details.get("actualEndTime"):
            derived_status: LiveStatus = "offline"
        elif broadcast == "live":
            derived_status = "live"
        elif broadcast == "upcoming":
            derived_status = "upcoming"
        else:
            derived_status = "offline"
        return ExternalLiveEvent(
            title=snippet.get("title"),
            description=snippet.get("description"),
            video_id=video_id,
            live_status=derived_status,
            thumbnail_url=thumbnail_url,
            scheduled_start_time=self._parse_datetime(live_details.get("scheduledStartTime")),
            scheduled_end_time=self._parse_datetime(live_details.get("scheduledEndTime")),
            actual_start_time=self._parse_datetime(live_details.get("actualStartTime")),
            embed_url=f"https://www.youtube.com/embed/{video_id}?autoplay=1&playsinline=1&rel=0",
        )

    @staticmethod
    def _failure_status(exc: httpx.HTTPError) -> LiveStatus:
        """Separate "we could not check" from "the channel is not broadcasting"."""
        response = getattr(exc, "response", None)
        if response is not None and response.status_code in TRANSIENT_HTTP_STATUS_CODES:
            return "check_failed"
        if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError)):
            return "check_failed"
        return "unavailable"

    def _get(self, path: str, *, params: dict[str, str]) -> dict:
        with httpx.Client(timeout=self.settings.live_tv_request_timeout_seconds, follow_redirects=True) as client:
            response = client.get(f"{self.base_url}{path}", params=params)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
