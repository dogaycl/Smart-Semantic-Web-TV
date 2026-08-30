from datetime import datetime, timezone

import httpx

from app.services.live_tv.providers.hls_provider import HLSStreamProvider
from app.services.live_tv.providers.youtube_provider import YouTubeLiveProvider


def test_youtube_live_provider_parses_live_and_upcoming_events(monkeypatch):
    provider = YouTubeLiveProvider()

    def fake_get(path, *, params):
        if path == "/channels":
            assert params["forHandle"] == "@Reuters"
            return {
                "items": [
                    {
                        "id": "UC-test-reuters",
                        "snippet": {
                            "thumbnails": {
                                "high": {"url": "https://img.example.com/channel.jpg"}
                            }
                        },
                    }
                ]
            }
        if path == "/search":
            if params["eventType"] == "live":
                return {"items": [{"id": {"videoId": "live-video-1"}}]}
            return {"items": [{"id": {"videoId": "upcoming-video-1"}}]}
        if path == "/videos":
            return {
                "items": [
                    {
                        "snippet": {
                            "title": "Reuters Live",
                            "description": "Global markets update",
                            "thumbnails": {"high": {"url": "https://img.example.com/live.jpg"}},
                        },
                        "status": {"embeddable": True},
                        "liveStreamingDetails": {
                            "actualStartTime": "2026-08-15T10:00:00Z",
                            "scheduledStartTime": "2026-08-15T09:55:00Z",
                            "scheduledEndTime": "2026-08-15T12:00:00Z",
                        },
                    }
                ]
            }
        raise AssertionError(f"Unexpected path: {path}")

    monkeypatch.setattr(provider, "_get", fake_get)

    event = provider.get_live_event(youtube_handle="@Reuters", youtube_channel_id=None)

    assert event.live_status == "live"
    assert event.video_id == "live-video-1"
    assert event.channel_id == "UC-test-reuters"
    assert event.embed_url == "https://www.youtube.com/embed/live-video-1?autoplay=1&playsinline=1&rel=0"
    assert event.actual_start_time == datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc)
    assert event.scheduled_end_time == datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)


def test_hls_stream_provider_marks_manifest_as_healthy(monkeypatch):
    provider = HLSStreamProvider()

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, headers=None):
            request = httpx.Request("GET", url)
            if url.endswith("media.m3u8"):
                return httpx.Response(
                    200,
                    headers={
                        "content-type": "application/vnd.apple.mpegurl",
                        "access-control-allow-origin": "*",
                    },
                    text="#EXTM3U\n#EXTINF:10,\nsegment0.ts",
                    request=request,
                )
            return httpx.Response(
                200,
                headers={
                    "content-type": "application/vnd.apple.mpegurl",
                    "access-control-allow-origin": "*",
                },
                text="#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1500000\nmedia.m3u8",
                request=request,
            )

    monkeypatch.setattr("app.services.live_tv.providers.hls_provider.httpx.Client", FakeClient)

    result = provider.check_stream("https://stream.example.com/live.m3u8")

    assert result.is_available is True
    assert result.stream_url == "https://stream.example.com/live.m3u8"
    assert result.error is None


def test_hls_stream_provider_reports_http_failure(monkeypatch):
    provider = HLSStreamProvider()

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url):
            request = httpx.Request("GET", url)
            return httpx.Response(404, request=request)

    monkeypatch.setattr("app.services.live_tv.providers.hls_provider.httpx.Client", FakeClient)

    result = provider.check_stream("https://stream.example.com/missing.m3u8")

    assert result.is_available is False
    assert result.error == "HTTP 404"


def test_youtube_provider_reuses_known_video_id_without_paying_for_a_search(monkeypatch):
    # Regression test: search.list costs 100 YouTube quota units against a 10,000/day default,
    # while videos.list costs 1. Re-searching every channel on every health sweep exhausted the
    # quota within the hour, which is what made every YouTube channel read "Unavailable".
    provider = YouTubeLiveProvider()
    called_paths: list[str] = []

    def fake_get(path, *, params):
        called_paths.append(path)
        if path == "/videos":
            assert params["id"] == "cached-live-video"
            return {
                "items": [
                    {
                        "snippet": {
                            "title": "NTV Canli Yayin",
                            "liveBroadcastContent": "live",
                            "thumbnails": {"high": {"url": "https://img.example.com/live.jpg"}},
                        },
                        "status": {"embeddable": True},
                        "liveStreamingDetails": {"actualStartTime": "2026-08-15T10:00:00Z"},
                    }
                ]
            }
        raise AssertionError(f"Unexpected path: {path}")

    monkeypatch.setattr(provider, "_get", fake_get)

    event = provider.get_live_event(
        youtube_handle="@NTV",
        youtube_channel_id="UC-ntv",
        known_video_id="cached-live-video",
    )

    assert event.live_status == "live"
    assert event.video_id == "cached-live-video"
    assert called_paths == ["/videos"], "a still-live cached video must not trigger search.list"


def test_youtube_provider_falls_back_to_search_when_cached_video_ended(monkeypatch):
    provider = YouTubeLiveProvider()
    called_paths: list[str] = []

    def fake_get(path, *, params):
        called_paths.append(path)
        if path == "/videos" and params["id"] == "stale-video":
            return {
                "items": [
                    {
                        "snippet": {"title": "Yesterday's stream", "liveBroadcastContent": "none"},
                        "status": {"embeddable": True},
                        "liveStreamingDetails": {
                            "actualStartTime": "2026-08-14T10:00:00Z",
                            "actualEndTime": "2026-08-14T12:00:00Z",
                        },
                    }
                ]
            }
        if path == "/channels":
            return {"items": [{"id": "UC-ntv", "snippet": {"thumbnails": {}}}]}
        if path == "/search":
            return {"items": [{"id": {"videoId": "fresh-live-video"}}]}
        if path == "/videos":
            return {
                "items": [
                    {
                        "snippet": {"title": "Live now", "liveBroadcastContent": "live"},
                        "status": {"embeddable": True},
                        "liveStreamingDetails": {"actualStartTime": "2026-08-15T10:00:00Z"},
                    }
                ]
            }
        raise AssertionError(f"Unexpected path: {path}")

    monkeypatch.setattr(provider, "_get", fake_get)

    event = provider.get_live_event(
        youtube_handle="@NTV", youtube_channel_id="UC-ntv", known_video_id="stale-video"
    )

    assert event.live_status == "live"
    assert event.video_id == "fresh-live-video"
    assert "/search" in called_paths, "an ended cached video must fall back to a real search"


def test_youtube_provider_reports_quota_exhaustion_as_check_failed(monkeypatch):
    # A 429 means "we could not check", not "the channel is offline". Treating it as an answer
    # permanently marked healthy channels unavailable until the next sweep.
    provider = YouTubeLiveProvider()

    def fake_get(path, *, params):
        request = httpx.Request("GET", "https://www.googleapis.com/youtube/v3/search")
        response = httpx.Response(429, request=request, text="quota exceeded")
        raise httpx.HTTPStatusError("429 Too Many Requests", request=request, response=response)

    monkeypatch.setattr(provider, "_get", fake_get)

    event = provider.get_live_event(youtube_handle="@NTV", youtube_channel_id=None)

    assert event.live_status == "check_failed"


def test_youtube_provider_redacts_api_key_from_error_text(monkeypatch):
    # channel.stream_error is returned to every client by GET /api/channels, and raw httpx
    # errors embed the full request URL including key=<YOUTUBE_API_KEY>.
    provider = YouTubeLiveProvider()
    monkeypatch.setattr(provider.settings, "youtube_api_key", "SUPER-SECRET-KEY-VALUE")

    def fake_get(path, *, params):
        raise httpx.ConnectError(
            "failed for url 'https://www.googleapis.com/youtube/v3/search"
            "?channelId=UC-x&key=SUPER-SECRET-KEY-VALUE'"
        )

    monkeypatch.setattr(provider, "_get", fake_get)

    event = provider.get_live_event(youtube_handle="@NTV", youtube_channel_id=None)

    assert "SUPER-SECRET-KEY-VALUE" not in (event.description or "")
    assert "<redacted>" in (event.description or "")
