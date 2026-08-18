from datetime import datetime, timedelta, timezone

from app.api.routers import channels as channels_router
from app.api.routers import epg as epg_router
from app.models.channel import Channel
from app.models.epg_entry import EPGEntry


def _freeze_sync(monkeypatch):
    monkeypatch.setattr(channels_router.sync_service, "ensure_ready", lambda **kwargs: None)
    monkeypatch.setattr(epg_router.sync_service, "ensure_ready", lambda **kwargs: None)


def _create_channel(db, **overrides):
    payload = {
        "slug": "abc-news-live",
        "name": "ABC News Live",
        "description": "Live US news",
        "category": "News",
        "logo_url": "https://example.com/logo.png",
        "country": "US",
        "language": "en",
        "source_type": "hls",
        "stream_url": "https://streams.example.com/abc.m3u8",
        "quality": "720p",
        "is_active": True,
        "stream_status": "healthy",
        "live_status": "live",
    }
    payload.update(overrides)
    channel = Channel(**payload)
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


def test_channels_endpoint_returns_playback_and_current_program(client, db_session, monkeypatch):
    _freeze_sync(monkeypatch)
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    channel = _create_channel(db_session)
    db_session.add(
        EPGEntry(
            channel_id=channel.id,
            external_id="abc-now",
            title="ABC Noon",
            start_time=now - timedelta(minutes=15),
            end_time=now + timedelta(minutes=45),
            source="xmltv",
        )
    )
    db_session.add(
        EPGEntry(
            channel_id=channel.id,
            external_id="abc-next",
            title="ABC World",
            start_time=now + timedelta(minutes=45),
            end_time=now + timedelta(hours=1, minutes=45),
            source="xmltv",
        )
    )
    db_session.commit()

    response = client.get("/api/channels")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["playback"]["type"] == "hls"
    assert payload[0]["current_program"]["title"] == "ABC Noon"
    assert payload[0]["next_program"]["title"] == "ABC World"


def test_channels_endpoint_filters_by_category_and_language(client, db_session, monkeypatch):
    _freeze_sync(monkeypatch)
    _create_channel(db_session)  # English News (default fixture values)
    _create_channel(
        db_session,
        slug="trt-muzik",
        name="TRT Muzik",
        category="Music",
        country="TR",
        language="tr",
        stream_url="https://tv-trtmuzik.medya.trt.com.tr/master.m3u8",
    )

    all_channels = client.get("/api/channels")
    assert all_channels.status_code == 200
    assert len(all_channels.json()) == 2

    turkish_only = client.get("/api/channels", params={"language": "tr"})
    assert turkish_only.status_code == 200
    assert [item["slug"] for item in turkish_only.json()] == ["trt-muzik"]

    music_only = client.get("/api/channels", params={"category": "Music"})
    assert music_only.status_code == 200
    assert [item["slug"] for item in music_only.json()] == ["trt-muzik"]

    news_and_english = client.get("/api/channels", params={"category": "News", "language": "en"})
    assert news_and_english.status_code == 200
    assert [item["slug"] for item in news_and_english.json()] == ["abc-news-live"]

    no_match = client.get("/api/channels", params={"category": "Sports"})
    assert no_match.status_code == 200
    assert no_match.json() == []


def test_channel_live_endpoint_supports_youtube_playback(client, db_session, monkeypatch):
    _freeze_sync(monkeypatch)
    channel = _create_channel(
        db_session,
        slug="reuters-youtube",
        name="Reuters on YouTube",
        source_type="youtube",
        youtube_channel_id="UC123",
        youtube_video_id="live-video-123",
        stream_url=None,
        stream_status="healthy",
        live_status="live",
    )

    response = client.get(f"/api/channels/{channel.id}/live")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_type"] == "youtube"
    assert payload["playback"]["type"] == "youtube"
    assert payload["playback"]["youtube_video_id"] == "live-video-123"


def test_epg_window_endpoint_groups_entries_by_channel(client, db_session, monkeypatch):
    _freeze_sync(monkeypatch)
    start = datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 15, 14, 0, tzinfo=timezone.utc)
    channel = _create_channel(db_session)
    db_session.add(
        EPGEntry(
            channel_id=channel.id,
            external_id="abc-epg-1",
            title="ABC News Live",
            start_time=start,
            end_time=start + timedelta(hours=1),
            source="xmltv",
        )
    )
    db_session.add(
        EPGEntry(
            channel_id=channel.id,
            external_id="abc-epg-2",
            title="ABC Politics",
            start_time=start + timedelta(hours=1),
            end_time=start + timedelta(hours=2),
            source="xmltv",
        )
    )
    db_session.commit()

    response = client.get(
        "/api/epg",
        params={
            "start": start.isoformat(),
            "end": end.isoformat(),
            "slot_minutes": 60,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["slots"]) == 4
    assert len(payload["channels"]) == 1
    assert payload["channels"][0]["channel"]["name"] == "ABC News Live"
    assert [entry["title"] for entry in payload["channels"][0]["entries"]] == [
        "ABC News Live",
        "ABC Politics",
    ]
