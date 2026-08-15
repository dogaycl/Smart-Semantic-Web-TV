from datetime import datetime, timezone
import gzip

from app.services.epg.providers.xmltv_provider import XMLTVProvider


def test_xmltv_provider_parses_timezone_and_channel_mapping(monkeypatch):
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="ABC.News.Live.us2">
    <display-name>ABC News Live</display-name>
  </channel>
  <channel id="TRT.WORLD.tr">
    <display-name>TRT World</display-name>
  </channel>
  <programme channel="ABC.News.Live.us2" start="20260815100000 +0000" stop="20260815110000 +0000">
    <title>ABC Morning Briefing</title>
    <desc>Headlines from the US.</desc>
    <category>News</category>
  </programme>
  <programme channel="TRT.WORLD.tr" start="20260815133000 +0300" stop="20260815143000 +0300">
    <title>TRT Midday</title>
    <desc>Regional updates.</desc>
    <category>Current Affairs</category>
  </programme>
</tv>
"""
    compressed = gzip.compress(xml.encode("utf-8"))
    provider = XMLTVProvider()

    monkeypatch.setattr(provider, "_download", lambda source_url: compressed)

    entries = provider.fetch_entries(
        source_url="https://example.com/demo.xml.gz",
        channel_ids={"ABC.News.Live.us2", "TRT.WORLD.tr"},
        window_start=datetime(2026, 8, 15, 9, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc),
    )

    assert "ABC.News.Live.us2" in entries
    assert entries["ABC.News.Live.us2"][0].title == "ABC Morning Briefing"
    assert entries["ABC.News.Live.us2"][0].start_time == datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc)
    assert entries["TRT.WORLD.tr"][0].start_time == datetime(2026, 8, 15, 10, 30, tzinfo=timezone.utc)
    assert entries["TRT.WORLD.tr"][0].category == "Current Affairs"
