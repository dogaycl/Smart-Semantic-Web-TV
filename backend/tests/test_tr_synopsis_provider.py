from datetime import datetime, timezone

from app.services.epg.providers.tr_synopsis_provider import TRSynopsisProvider, normalize_title


NEXT_DATA_PAGE = """
<html><body>
<script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"rows":[{"tvChannels":[{"title":"TRT 1","upcoming":[
  {"title":"Seksenler","synopsis":"Seksenli yıllarda İstanbul'un küçük bir mahallesinde yaşayan insanların hikâyesi.","starttime":"2026-09-02T16:15:00.000Z"},
  {"title":"İstiklal Marşı","synopsis":"İstiklal Marşı","starttime":"2026-09-02T08:13:00.000Z"},
  {"title":"Ana Haber","synopsis":"Türkiye ve dünya gündemi ana haber bülteninde.","starttime":"2026-09-02T19:00:00.000Z"}
]}]}]}}}
</script></body></html>
"""

INLINE_PAGE = """
<html><body><script>
self.__data = {"days":[],"epg":[
  {"date":"2026-09-02","data":[
    {"title":"İzler Suretler","synopsis":"Fotoğraf sanatçılarının eserlerini ve üretim süreçlerini anlatan program.","starttime":"2026-09-02T08:00:00.000Z"},
    {"title":"Kısa Film","synopsis":"K","starttime":"2026-09-02T09:00:00.000Z"}
  ]}
]};
</script></body></html>
"""


def test_normalize_title_is_turkish_case_insensitive():
    assert normalize_title("3'Te 3") == normalize_title("3’te 3")
    assert normalize_title("İZLER Suretler") == "izler suretler"


def test_parses_next_data_synopses_and_skips_filler(monkeypatch):
    provider = TRSynopsisProvider()
    monkeypatch.setattr(provider, "_download", lambda source_url: NEXT_DATA_PAGE)

    result = provider.fetch_synopses(source_url="https://example.com/yayin-akisi")

    assert result[normalize_title("Seksenler")].startswith("Seksenli yıllarda")
    assert normalize_title("Ana Haber") in result
    # "synopsis" equal to the title is filler, not a description.
    assert normalize_title("İstiklal Marşı") not in result


def test_parses_inline_epg_blob(monkeypatch):
    provider = TRSynopsisProvider()
    monkeypatch.setattr(provider, "_download", lambda source_url: INLINE_PAGE)

    result = provider.fetch_synopses(source_url="https://example.com/yayin-akisi")

    assert normalize_title("İzler Suretler") in result
    # Too short to be a real synopsis.
    assert normalize_title("Kısa Film") not in result


def test_inline_epg_as_full_timed_source(monkeypatch):
    provider = TRSynopsisProvider()
    monkeypatch.setattr(provider, "_download", lambda source_url: INLINE_PAGE)

    entries = provider.fetch_entries(
        source_url="https://example.com/yayin-akisi",
        window_start=datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 9, 3, 0, 0, tzinfo=timezone.utc),
    )

    assert [e.title for e in entries] == ["İzler Suretler", "Kısa Film"]
    first = entries[0]
    assert first.source == "broadcaster"
    assert first.start_time == datetime(2026, 9, 2, 8, 0, tzinfo=timezone.utc)
    # End is derived from the next programme's start.
    assert first.end_time == datetime(2026, 9, 2, 9, 0, tzinfo=timezone.utc)
    assert first.description.startswith("Fotoğraf sanatçıları")


HABERTURK_PAGE = """
<div data-date="2026-09-02" data-hours="06:00" data-index="0">
  <div><h3>Haber Bülteni</h3><p>Günün sıcak gelişmeleri Haber B&#252;lteni&#039;nde ekranlara geliyor.</p></div>
</div>
"""

EVENT_LIST_PAGE = """
<ul class="event-list">
  <li id="item1" data-title="Klipark">
    <time datetime="02.09.2026"><span class="day"><a href="javascript:void()">07:05</a></span></time>
    <div class="info"><h1 class="title">Klipark</h1>
      <p class="desc"><a href="javascript:void()">Pop müziğin en çok izlenen ve sevilen klipleri Klipark programıyla ekranlara geliyor.</a></p>
    </div>
  </li>
</ul>
"""


def test_parses_haberturk_rows_and_unescapes_entities(monkeypatch):
    provider = TRSynopsisProvider()
    monkeypatch.setattr(provider, "_download", lambda source_url: HABERTURK_PAGE)

    result = provider.fetch_synopses(source_url="https://tv.haberturk.com/yayin-akisi")

    assert result[normalize_title("Haber Bülteni")] == (
        "Günün sıcak gelişmeleri Haber Bülteni'nde ekranlara geliyor."
    )


def test_parses_trt_event_list(monkeypatch):
    provider = TRSynopsisProvider()
    monkeypatch.setattr(provider, "_download", lambda source_url: EVENT_LIST_PAGE)

    result = provider.fetch_synopses(source_url="https://www.trtmuzik.net.tr/yayin-akisi")

    assert normalize_title("Klipark") in result
    assert result[normalize_title("Klipark")].startswith("Pop müziğin")
