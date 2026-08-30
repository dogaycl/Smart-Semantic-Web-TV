from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import get_settings
from app.models.channel import Channel
from app.models.epg_entry import EPGEntry
from app.services.live_tv.sync_service import LiveTVSyncService


@pytest.fixture()
def sync_service():
    service = LiveTVSyncService()
    # live_tv_auto_sync is disabled globally in conftest so unrelated tests never hit the network.
    settings = get_settings()
    original = settings.live_tv_auto_sync
    settings.live_tv_auto_sync = True
    yield service
    settings.live_tv_auto_sync = original


def _create_channel(db_session, slug: str) -> Channel:
    channel = Channel(
        slug=slug,
        name=slug.title(),
        description="Test channel",
        category="News",
        country="TR",
        language="tr",
        source_type="hls",
        stream_url="https://example.com/live.m3u8",
        is_active=True,
        stream_status="healthy",
        live_status="live",
        last_checked_at=datetime.now(timezone.utc),
        epg_source_url="https://example.com/epg.xml.gz",
        epg_channel_id=f"{slug.upper()}.tr",
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    return channel


def _add_entry(db_session, channel: Channel, *, start: datetime, updated_at: datetime) -> None:
    db_session.add(
        EPGEntry(
            channel_id=channel.id,
            external_id=f"{channel.slug}-{start.isoformat()}",
            title="Programme",
            category="News",
            start_time=start,
            end_time=start + timedelta(hours=1),
            source="xmltv",
            last_updated_at=updated_at,
        )
    )
    db_session.commit()


def _record_syncs(monkeypatch, service):
    calls: list[tuple[datetime, datetime]] = []
    monkeypatch.setattr(
        service,
        "sync_epg",
        lambda *, db, window_start, window_end: calls.append((window_start, window_end)),
    )
    monkeypatch.setattr(service, "refresh_live_status", lambda **kwargs: None)
    monkeypatch.setattr(service, "sync_channels", lambda **kwargs: None)
    monkeypatch.setattr(service, "_requires_channel_resync", lambda **kwargs: False)
    return calls


def test_requests_for_an_uncovered_day_trigger_a_sync(db_session, monkeypatch, sync_service):
    # The reported bug: EPG only re-synced when a window had zero entries across ALL channels,
    # so browsing the guide to another date rendered an empty grid that never populated.
    channel = _create_channel(db_session, "trt-haber")
    now = datetime.now(timezone.utc)
    _add_entry(db_session, channel, start=now + timedelta(hours=1), updated_at=now)

    calls = _record_syncs(monkeypatch, sync_service)

    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    sync_service.ensure_ready(db=db_session, window_start=tomorrow, window_end=tomorrow + timedelta(days=1))

    assert len(calls) == 1, "a day with no stored entries must be fetched"


def test_covered_and_fresh_window_is_not_resynced(db_session, monkeypatch, sync_service):
    channel = _create_channel(db_session, "trt-1")
    now = datetime.now(timezone.utc)
    _add_entry(db_session, channel, start=now + timedelta(minutes=30), updated_at=now)

    calls = _record_syncs(monkeypatch, sync_service)
    sync_service.ensure_ready(db=db_session, window_start=now, window_end=now + timedelta(hours=4))

    assert calls == [], "a covered, freshly-updated window must not re-download the feed"


def test_stale_window_is_resynced_even_when_covered(db_session, monkeypatch, sync_service):
    channel = _create_channel(db_session, "trt-muzik")
    now = datetime.now(timezone.utc)
    settings = get_settings()
    stale = now - timedelta(minutes=settings.live_tv_epg_ttl_minutes + 60)
    _add_entry(db_session, channel, start=now + timedelta(minutes=30), updated_at=stale)

    calls = _record_syncs(monkeypatch, sync_service)
    sync_service.ensure_ready(db=db_session, window_start=now, window_end=now + timedelta(hours=4))

    assert len(calls) == 1, "entries older than the EPG TTL must be refreshed"


def test_repeated_requests_for_an_uncoverable_day_are_throttled(db_session, monkeypatch, sync_service):
    # Each sync downloads whole multi-MB XMLTV dumps. Without a cooldown, every Prev/Next click
    # on a day the upstream feed does not publish would re-download them.
    _create_channel(db_session, "trt-world")
    now = datetime.now(timezone.utc)

    calls = _record_syncs(monkeypatch, sync_service)
    far_day = (now + timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0)

    sync_service.ensure_ready(db=db_session, window_start=far_day, window_end=far_day + timedelta(days=1))
    sync_service.ensure_ready(db=db_session, window_start=far_day, window_end=far_day + timedelta(days=1))
    sync_service.ensure_ready(db=db_session, window_start=far_day, window_end=far_day + timedelta(days=1))

    assert len(calls) == 1, "repeated misses for the same day must be throttled to one attempt"


def test_windows_beyond_the_lookahead_are_never_fetched(db_session, monkeypatch, sync_service):
    _create_channel(db_session, "trt-belgesel")
    now = datetime.now(timezone.utc)

    calls = _record_syncs(monkeypatch, sync_service)
    far_future = now + timedelta(days=30)
    sync_service.ensure_ready(db=db_session, window_start=far_future, window_end=far_future + timedelta(days=1))

    assert calls == [], "no upstream dump publishes a month ahead, so this must not be chased"
