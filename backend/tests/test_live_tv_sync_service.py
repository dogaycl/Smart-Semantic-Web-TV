from app.models.channel import Channel
from app.services.live_tv.catalog import ChannelSeed
from app.services.live_tv.sync_service import IPTVOrgCatalog, LiveTVSyncService


def test_sync_channels_curates_english_demo_channels_and_disables_legacy_records(db_session, monkeypatch):
    service = LiveTVSyncService()
    service.settings.youtube_api_key = None

    seeds = {
        "demo-tech": ChannelSeed(
            slug="demo-tech",
            name="Demo Tech",
            description="Curated English technology channel.",
            category="Technology",
            country="US",
            language="en",
            source_type="hls",
            iptv_org_channel_id="DemoTech.us",
            preferred_stream_urls=["https://preferred.example.com/demo-tech.m3u8"],
        ),
    }
    catalog = IPTVOrgCatalog(
        channels={
            "DemoTech.us": {
                "id": "DemoTech.us",
                "country": "US",
                "categories": ["business"],
            }
        },
        feeds={
            "DemoTech.us": [
                {
                    "id": "US",
                    "channel": "DemoTech.us",
                    "languages": ["jpn", "eng"],
                    "broadcast_area": ["c/US"],
                    "is_main": True,
                }
            ]
        },
        streams={
            "DemoTech.us": [
                {
                    "channel": "DemoTech.us",
                    "feed": "US",
                    "url": "https://catalog.example.com/demo-tech.m3u8",
                    "quality": "1080p",
                }
            ]
        },
        logos={
            "DemoTech.us": [
                {
                    "channel": "DemoTech.us",
                    "feed": None,
                    "in_use": True,
                    "width": 1200,
                    "height": 500,
                    "url": "https://img.example.com/demo-tech.png",
                }
            ]
        },
        countries={"US": {"code": "US", "languages": ["eng"]}},
    )

    legacy = Channel(
        slug="legacy-arabic",
        name="Legacy Arabic Demo",
        category="News",
        country="QA",
        language="ar",
        source_type="hls",
        is_active=True,
        stream_status="healthy",
        live_status="live",
    )
    db_session.add(legacy)
    db_session.commit()

    monkeypatch.setattr(service, "_enabled_seed_map", lambda: seeds)
    monkeypatch.setattr(service, "_fetch_iptv_org_catalog", lambda: catalog)

    service.sync_channels(db=db_session)

    curated = service.channel_repository.get_by_slug(db=db_session, slug="demo-tech")
    legacy = service.channel_repository.get_by_slug(db=db_session, slug="legacy-arabic")

    assert curated is not None
    assert curated.is_active is True
    assert curated.category == "Technology"
    assert curated.language == "en"
    assert curated.logo_url == "https://img.example.com/demo-tech.png"
    assert curated.stream_url == "https://preferred.example.com/demo-tech.m3u8"
    assert legacy is not None
    assert legacy.is_active is False


def test_stream_candidates_prefer_browser_safe_english_feeds(db_session):
    service = LiveTVSyncService()
    seed = ChannelSeed(
        slug="demo-channel",
        name="Demo Channel",
        description="English demo channel.",
        category="News",
        country="US",
        language="en",
        source_type="hls",
        iptv_org_channel_id="DemoChannel.us",
    )
    channel = Channel(
        slug="demo-channel",
        name="Demo Channel",
        category="News",
        country="US",
        language="en",
        source_type="hls",
        is_active=True,
        stream_status="unknown",
        live_status="unknown",
    )
    catalog = IPTVOrgCatalog(
        feeds={
            "DemoChannel.us": [
                {
                    "id": "US",
                    "channel": "DemoChannel.us",
                    "languages": ["eng"],
                    "broadcast_area": ["c/US"],
                    "is_main": True,
                },
                {
                    "id": "ES",
                    "channel": "DemoChannel.us",
                    "languages": ["spa"],
                    "broadcast_area": ["c/MX"],
                    "is_main": False,
                },
            ]
        },
        streams={
            "DemoChannel.us": [
                {
                    "channel": "DemoChannel.us",
                    "feed": "US",
                    "url": "https://english.example.com/live.m3u8",
                    "quality": "1080p",
                },
                {
                    "channel": "DemoChannel.us",
                    "feed": "US",
                    "url": "https://blocked.example.com/live.m3u8",
                    "quality": "1080p",
                    "referrer": "https://requires-header.example.com",
                },
                {
                    "channel": "DemoChannel.us",
                    "feed": "ES",
                    "url": "https://spanish.example.com/live.m3u8",
                    "quality": "720p",
                },
            ]
        },
        guides={
            "DemoChannel.us": [
                {"channel": "DemoChannel.us", "feed": "US", "lang": "en"},
                {"channel": "DemoChannel.us", "feed": "ES", "lang": "es"},
            ]
        },
        countries={
            "US": {"code": "US", "languages": ["eng"]},
            "MX": {"code": "MX", "languages": ["spa"]},
        },
    )

    candidates = service._stream_candidates_for_channel(channel=channel, catalog=catalog, seed=seed)

    assert [candidate["url"] for candidate in candidates] == [
        "https://english.example.com/live.m3u8",
        "https://spanish.example.com/live.m3u8",
    ]
