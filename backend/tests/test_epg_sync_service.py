from datetime import datetime, timedelta, timezone

from app.models.channel import Channel
from app.services.epg.service import EPGService
from app.services.live_tv.providers.base import ExternalEPGEntry


def _create_channel(db_session, *, slug: str, source_type: str = "hls", epg_channel_id: str | None = "DEMO.tr") -> Channel:
    channel = Channel(
        slug=slug,
        name=slug.replace("-", " ").title(),
        description="Test channel",
        category="News",
        logo_url="https://example.com/logo.png",
        country="TR",
        language="tr",
        source_type=source_type,
        stream_url="https://example.com/live.m3u8" if source_type == "hls" else None,
        youtube_handle="@demo" if source_type == "youtube" else None,
        is_active=True,
        stream_status="healthy",
        live_status="live",
        epg_source_url="https://example.com/epg.xml.gz" if epg_channel_id else None,
        epg_channel_id=epg_channel_id,
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    return channel


def _entry(*, external_id: str, title: str, start: datetime, minutes: int = 60) -> ExternalEPGEntry:
    return ExternalEPGEntry(
        external_id=external_id,
        title=title,
        description=None,
        category="News",
        start_time=start,
        end_time=start + timedelta(minutes=minutes),
        source="xmltv",
    )


def test_syncing_one_day_does_not_delete_entries_from_other_days(db_session, monkeypatch):
    # Regression test: _replace_channel_entries used to prune a fixed 7-day span starting at the
    # sync window, while the XMLTV provider only ever returns entries *inside* that window. So
    # syncing a single day (which EPG date navigation does) deleted every other day's schedule,
    # and nulled the epg_entry_id links that accepted My Channel plans depend on.
    service = EPGService()
    channel = _create_channel(db_session, slug="trt-haber")

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    day_after = today + timedelta(days=2)

    def fake_fetch(*, source_url, channel_ids, window_start, window_end):
        # Mirror the real provider: only return entries that overlap the requested window.
        pool = [
            _entry(external_id="today-1", title="Today Bulletin", start=today + timedelta(hours=9)),
            _entry(external_id="day2-1", title="Day Two Bulletin", start=day_after + timedelta(hours=9)),
        ]
        matched = [e for e in pool if e.end_time > window_start and e.start_time < window_end]
        return {"DEMO.tr": matched}

    monkeypatch.setattr(service.xmltv_provider, "fetch_entries", fake_fetch)

    # Populate today and day+2.
    service.sync_epg(db=db_session, channels=[channel], window_start=today, window_end=today + timedelta(days=3))
    stored = {entry.external_id for entry in service.epg_entry_repository.list_for_window(
        db=db_session, channel_ids=[channel.id], start=today, end=today + timedelta(days=3))}
    assert stored == {"today-1", "day2-1"}

    # Now sync only day+1 - which legitimately has no programmes.
    tomorrow = today + timedelta(days=1)
    service.sync_epg(db=db_session, channels=[channel], window_start=tomorrow, window_end=tomorrow + timedelta(days=1))

    surviving = {entry.external_id for entry in service.epg_entry_repository.list_for_window(
        db=db_session, channel_ids=[channel.id], start=today, end=today + timedelta(days=3))}
    assert surviving == {"today-1", "day2-1"}, "syncing one day must not delete other days"


def test_syncing_removes_entries_that_vanished_from_the_source_within_the_window(db_session, monkeypatch):
    service = EPGService()
    channel = _create_channel(db_session, slug="trt-1")
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    window_end = today + timedelta(days=1)

    payload = {
        "DEMO.tr": [
            _entry(external_id="a", title="Show A", start=today + timedelta(hours=9)),
            _entry(external_id="b", title="Show B", start=today + timedelta(hours=10)),
        ]
    }
    monkeypatch.setattr(
        service.xmltv_provider, "fetch_entries",
        lambda **kwargs: payload,
    )
    service.sync_epg(db=db_session, channels=[channel], window_start=today, window_end=window_end)
    assert len(service.epg_entry_repository.list_for_window(
        db=db_session, channel_ids=[channel.id], start=today, end=window_end)) == 2

    # The source drops "b" - it must disappear from our copy of that same window.
    payload["DEMO.tr"] = [_entry(external_id="a", title="Show A", start=today + timedelta(hours=9))]
    service.sync_epg(db=db_session, channels=[channel], window_start=today, window_end=window_end)

    remaining = {entry.external_id for entry in service.epg_entry_repository.list_for_window(
        db=db_session, channel_ids=[channel.id], start=today, end=window_end)}
    assert remaining == {"a"}


def test_failed_xmltv_download_preserves_existing_entries(db_session, monkeypatch):
    # A download failure must not be interpreted as "the schedule is empty" - that would prune
    # real data every time the upstream feed had a hiccup.
    import httpx

    service = EPGService()
    channel = _create_channel(db_session, slug="trt-muzik")
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    window_end = today + timedelta(days=1)

    monkeypatch.setattr(
        service.xmltv_provider, "fetch_entries",
        lambda **kwargs: {"DEMO.tr": [_entry(external_id="keep-me", title="Keep", start=today + timedelta(hours=8))]},
    )
    service.sync_epg(db=db_session, channels=[channel], window_start=today, window_end=window_end)

    def boom(**kwargs):
        raise httpx.ConnectError("upstream down")

    monkeypatch.setattr(service.xmltv_provider, "fetch_entries", boom)
    service.sync_epg(db=db_session, channels=[channel], window_start=today, window_end=window_end)

    surviving = {entry.external_id for entry in service.epg_entry_repository.list_for_window(
        db=db_session, channel_ids=[channel.id], start=today, end=window_end)}
    assert surviving == {"keep-me"}


def test_youtube_sourced_channel_still_uses_xmltv_when_mapped(db_session, monkeypatch):
    # A channel played back via YouTube can still have a real published schedule. Restricting
    # XMLTV to source_type == "hls" hid hundreds of genuine programmes for channels like NTV.
    service = EPGService()
    channel = _create_channel(db_session, slug="ntv-tr", source_type="youtube", epg_channel_id="DEMO.tr")
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    monkeypatch.setattr(
        service.xmltv_provider, "fetch_entries",
        lambda **kwargs: {"DEMO.tr": [_entry(external_id="ntv-1", title="NTV Haber", start=today + timedelta(hours=9))]},
    )

    def fail_if_called(**kwargs):
        raise AssertionError("XMLTV-mapped channels must not spend YouTube quota on a schedule lookup")

    monkeypatch.setattr(service.youtube_schedule_provider, "fetch_entries", fail_if_called)

    service.sync_epg(db=db_session, channels=[channel], window_start=today, window_end=today + timedelta(days=1))

    stored = service.epg_entry_repository.list_for_window(
        db=db_session, channel_ids=[channel.id], start=today, end=today + timedelta(days=1))
    assert [entry.title for entry in stored] == ["NTV Haber"]
    assert stored[0].source == "xmltv"
