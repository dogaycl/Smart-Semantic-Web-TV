from dataclasses import dataclass, field
from typing import Literal

SourceType = Literal["youtube", "hls"]


@dataclass(slots=True)
class ChannelSeed:
    slug: str
    name: str
    description: str
    category: str
    country: str
    language: str
    source_type: SourceType
    is_active: bool = True
    iptv_org_channel_id: str | None = None
    preferred_stream_urls: list[str] = field(default_factory=list)
    youtube_handle: str | None = None
    logo_url: str | None = None
    epg_source_url: str | None = None
    epg_channel_id: str | None = None


LIVE_TV_CHANNEL_SEEDS: list[ChannelSeed] = [
    ChannelSeed(
        slug="abc-news-live",
        name="ABC News Live",
        description="US rolling news channel with live breaking coverage and headline updates.",
        category="News",
        country="US",
        language="en",
        source_type="hls",
        iptv_org_channel_id="ABCNewsLive.us",
        preferred_stream_urls=[
            "https://jmp2.uk/plu-6508be683a0d700008c534e4.m3u8",
            "https://aegis-cloudfront-1.tubi.video/d6cbb0de-68e4-4f3b-82f9-bf5d526e0bde/index.m3u8",
        ],
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz",
        epg_channel_id="ABC.News.Live.us2",
    ),
    ChannelSeed(
        slug="bloomberg-tv",
        name="Bloomberg TV",
        description="Live business television with global markets, tech, and economy coverage.",
        category="Business",
        country="US",
        language="en",
        source_type="hls",
        iptv_org_channel_id="BloombergTV.us",
        preferred_stream_urls=[
            "https://www.bloomberg.com/media-manifest/streams/us.m3u8",
            "https://bloomberg.com/media-manifest/streams/asia.m3u8",
        ],
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz",
        epg_channel_id="Bloomberg.Business.Television.us2",
    ),
    ChannelSeed(
        slug="reuters-tv",
        name="Reuters TV",
        description="Reuters live news stream with global events, analysis, and press coverage.",
        category="News",
        country="US",
        language="en",
        source_type="hls",
        iptv_org_channel_id="ReutersTV.us",
        preferred_stream_urls=[
            "https://amg00453-reuters-amg00453c1-rakuten-uk-2110.playouts.now.amagi.tv/playlist/amg00453-reuters-reuters-rakutenuk/playlist.m3u8",
        ],
    ),
    ChannelSeed(
        slug="nhk-world-japan",
        name="NHK World-Japan",
        description="International news and culture programming from Japan's public broadcaster.",
        category="News",
        country="JP",
        language="en",
        source_type="hls",
        iptv_org_channel_id="NHKWorldJapan.jp",
        preferred_stream_urls=[
            "https://masterpl.hls.nhkworld.jp/hls/w/live/smarttv.m3u8",
            "https://media-osa.hls.nhkworld.jp/hls/w/live/master.m3u8",
        ],
    ),
    ChannelSeed(
        slug="trt-world",
        name="TRT World",
        description="International news coverage from Turkiye with live reports and documentaries.",
        category="News",
        country="TR",
        language="en",
        source_type="hls",
        iptv_org_channel_id="TRTWorld.tr",
        preferred_stream_urls=[
            "https://tv-trtworld.medya.trt.com.tr/master.m3u8",
            "https://dash2.antik.sk/live/test_trt_world_atktv/playlist.m3u8",
        ],
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
        epg_channel_id="TRT.WORLD.tr",
    ),
    ChannelSeed(
        slug="arirang-tv",
        name="Arirang TV",
        description="Korean current affairs, culture, and international programming.",
        category="News",
        country="KR",
        language="en",
        source_type="hls",
        iptv_org_channel_id="ArirangTV.kr",
        preferred_stream_urls=[
            "https://dash3.antik.sk/live/test_arirang/playlist.m3u8",
            "http://amdlive-ch01.ctnd.com.edgesuite.net/arirang_1ch/smil:arirang_1ch.smil/playlist.m3u8",
        ],
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_KR1.xml.gz",
        epg_channel_id="Arirang.World.kr",
    ),
    ChannelSeed(
        slug="euronews-english",
        name="Euronews English",
        description="Pan-European live news with international headlines and business updates.",
        category="News",
        country="FR",
        language="en",
        source_type="hls",
        iptv_org_channel_id="EuronewsEnglish.fr",
        preferred_stream_urls=[
            "https://cdn-euronews.akamaized.net/live/eds/euronews-en/25002/index.m3u8",
            "https://jmp2.uk/plu-61de96114757070008d33cae.m3u8",
        ],
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_FR1.xml.gz",
        epg_channel_id="Euronews.fr",
    ),
    ChannelSeed(
        slug="cgtn",
        name="CGTN",
        description="China Global Television Network live international news feed.",
        category="News",
        country="CN",
        language="en",
        source_type="hls",
        iptv_org_channel_id="CGTN.cn",
        preferred_stream_urls=[
            "https://english-livebkali.cgtn.com/live/encgtn.m3u8",
            "https://amg00405-rakutentv-cgtn-rakuten-i9tar.amagi.tv/master.m3u8",
        ],
    ),
    ChannelSeed(
        slug="al-jazeera",
        name="Al Jazeera",
        description="Qatar-based global news channel with live world coverage.",
        category="News",
        country="QA",
        language="en",
        source_type="hls",
        iptv_org_channel_id="AlJazeera.qa",
        preferred_stream_urls=[
            "https://live-hls-apps-aja-fa.getaj.net/AJA/index.m3u8",
            "https://live-hls-apps-aja-fa.getaj.net/AJA/01.m3u8",
        ],
    ),
    ChannelSeed(
        slug="reuters-youtube",
        name="Reuters on YouTube",
        description="Reuters live YouTube channel for global events and breaking coverage.",
        category="News",
        country="US",
        language="en",
        source_type="youtube",
        youtube_handle="@Reuters",
    ),
    ChannelSeed(
        slug="dw-news-youtube",
        name="DW News on YouTube",
        description="DW's live YouTube news feed and upcoming live event schedule.",
        category="News",
        country="DE",
        language="en",
        source_type="youtube",
        youtube_handle="@DWNews",
    ),
    ChannelSeed(
        slug="associated-press-youtube",
        name="Associated Press on YouTube",
        description="AP live streams and scheduled broadcasts from the Associated Press.",
        category="News",
        country="US",
        language="en",
        source_type="youtube",
        youtube_handle="@AssociatedPress",
    ),
    ChannelSeed(
        slug="al-jazeera-youtube",
        name="Al Jazeera English on YouTube",
        description="Al Jazeera English live YouTube broadcasts and scheduled streams.",
        category="News",
        country="QA",
        language="en",
        source_type="youtube",
        youtube_handle="@AlJazeeraEnglish",
    ),
]


def channel_seed_map() -> dict[str, ChannelSeed]:
    return {seed.slug: seed for seed in LIVE_TV_CHANNEL_SEEDS}
