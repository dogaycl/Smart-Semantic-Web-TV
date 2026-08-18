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
