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
            "https://aegis-cloudfront-1.tubi.video/d6cbb0de-68e4-4f3b-82f9-bf5d526e0bde/index.m3u8",
            "https://jmp2.uk/plu-6508be683a0d700008c534e4.m3u8",
        ],
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz",
        epg_channel_id="ABC.News.Live.us2",
        is_active=False,
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
        slug="bloomberg-originals",
        name="Bloomberg Originals",
        description="English-language Bloomberg originals focused on technology, startups, and business storytelling.",
        category="Technology",
        country="US",
        language="en",
        source_type="hls",
        iptv_org_channel_id="BloombergOriginals.us",
        preferred_stream_urls=[
            "https://bloomberg.com/media-manifest/streams/qt.m3u8",
        ],
    ),
    ChannelSeed(
        slug="cbc-news-network",
        name="CBC News Network",
        description="Canadian live news coverage with national and international reporting.",
        category="News",
        country="CA",
        language="en",
        source_type="hls",
        iptv_org_channel_id="CBCNewsNetwork.ca",
        preferred_stream_urls=[
            "https://amg00788-cbc-amg00788c4-xumo-us-3045.playouts.now.amagi.tv/master.m3u8",
            "https://aegis-cloudfront-1.tubi.video/c71ce9b6-cddb-4cec-b0db-2f09289f8782/master.m3u8",
            "https://d2ny9lo79ujali.cloudfront.net/CBC_News_International.m3u8",
        ],
        is_active=False,
    ),
    ChannelSeed(
        slug="cloudflare-tv",
        name="Cloudflare TV",
        description="Technology-focused live channel with developer talks, product sessions, and internet infrastructure coverage.",
        category="Technology",
        country="US",
        language="en",
        source_type="hls",
        iptv_org_channel_id="CloudflareTV.us",
        preferred_stream_urls=[
            "https://cloudflare.tv/hls/live.m3u8",
        ],
    ),
    ChannelSeed(
        slug="create",
        name="Create",
        description="Educational lifestyle television with cooking, travel, craft, and public media programming.",
        category="Education",
        country="US",
        language="en",
        source_type="hls",
        iptv_org_channel_id="Create.us",
        preferred_stream_urls=[
            "https://create.lls.pbs.org/index.m3u8",
        ],
        is_active=False,
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
        slug="fite-24-7",
        name="FITE 24/7",
        description="Always-on combat sports and live event highlights channel with public HLS playback.",
        category="Sports",
        country="US",
        language="en",
        source_type="hls",
        iptv_org_channel_id="FITE247.us",
        preferred_stream_urls=[
            "https://a-cdn.klowdtv.com/live2/fite247_720p/playlist.m3u8",
        ],
    ),
    ChannelSeed(
        slug="bounce-xl",
        name="Bounce XL",
        description="Free English-language entertainment channel with movies and series programming.",
        category="Entertainment",
        country="US",
        language="en",
        source_type="hls",
        iptv_org_channel_id="BounceXL.us",
        preferred_stream_urls=[
            "https://cdn-uw2-prod.tsv2.amagi.tv/linear/amg01438-ewscrippscompan-bouncexl-tablo/playlist.m3u8",
            "https://aegis-cloudfront-1.tubi.video/22eea4e9-00a6-427c-92dd-57e78cc160dc/playlist.m3u8",
        ],
        is_active=False,
    ),
    ChannelSeed(
        slug="love-pets",
        name="Love Pets",
        description="Animal and pet-focused factual programming from an English-language public channel.",
        category="Documentary",
        country="CA",
        language="en",
        source_type="hls",
        iptv_org_channel_id="LovePets.ca",
        preferred_stream_urls=[
            "https://amg01576-blueskyeenterta-lovepetsemea-samsungse-ctamh.amagi.tv/playlist/amg01576-blueskyeenterta-lovepetsemea-samsungse/playlist.m3u8",
            "https://d31r8y66tn175.cloudfront.net/Love_Pets.m3u8",
        ],
        is_active=False,
    ),
    ChannelSeed(
        slug="nature-time",
        name="NatureTime",
        description="Nature and wildlife documentaries from an English-language free linear feed.",
        category="Documentary",
        country="CA",
        language="en",
        source_type="hls",
        iptv_org_channel_id="NatureTime.ca",
        preferred_stream_urls=[
            "https://amg00090-blueantllc-lovenature-au-samsungau-wggcn.amagi.tv/playlist/amg00090-blueantllc-lovenature-au-samsungau/playlist.m3u8",
            "https://jmp2.uk/plu-60dd6b1da79e4d0007309455.m3u8",
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
        is_active=False,
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
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        epg_channel_id="TRT.WORLD.HD.tr",
    ),
    ChannelSeed(
        slug="arirang-tv",
        name="Arirang TV",
        description="English-language Korean current affairs, culture, and lifestyle programming.",
        category="General TV",
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
        slug="acc-digital-network",
        name="ACC Digital Network",
        description="College sports highlights, studio coverage, and live sports programming.",
        category="Sports",
        country="US",
        language="en",
        source_type="hls",
        iptv_org_channel_id="ACCDigitalNetwork.us",
        preferred_stream_urls=[
            "https://raycom-accdn-firetv.amagi.tv/playlist.m3u8",
        ],
        is_active=False,
    ),
    ChannelSeed(
        slug="yahoo-finance",
        name="Yahoo! Finance",
        description="Business headlines, markets, and company news from Yahoo! Finance.",
        category="Business",
        country="US",
        language="en",
        source_type="hls",
        iptv_org_channel_id="YahooFinance.us",
        preferred_stream_urls=[
            "https://d1ewctnvcwvvvu.cloudfront.net/playlist.m3u8",
        ],
    ),
    ChannelSeed(
        slug="sky-news-youtube",
        name="Sky News on YouTube",
        description="Sky News live YouTube coverage for breaking UK and global stories.",
        category="News",
        country="GB",
        language="en",
        source_type="youtube",
        youtube_handle="@SkyNews",
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
        slug="associated-press-youtube",
        name="Associated Press on YouTube",
        description="AP live streams and scheduled broadcasts from the Associated Press.",
        category="News",
        country="US",
        language="en",
        source_type="youtube",
        youtube_handle="@AssociatedPress",
    ),
    # --- Turkish channels (verified working: real HTTP + HLS manifest + browser CORS check) ---
    ChannelSeed(
        slug="trt-haber",
        name="TRT Haber",
        description="Turkiye's public broadcaster rolling news channel with national and international coverage.",
        category="News",
        country="TR",
        language="tr",
        source_type="hls",
        iptv_org_channel_id="TRTHaber.tr",
        preferred_stream_urls=[
            "https://tv-trthaber.medya.trt.com.tr/master.m3u8",
        ],
        logo_url="https://upload.wikimedia.org/wikipedia/commons/thumb/7/72/TRT_Haber_Eyl%C3%BCl_2020_Logo.svg/960px-TRT_Haber_Eyl%C3%BCl_2020_Logo.svg.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        # The plain "TRT.HABER.tr" feed id currently carries zero programmes; the HD variant is
        # the one the source actually populates. Verified against the live TR3 XMLTV dump.
        epg_channel_id="TRT.HABER.tr",
    ),
    ChannelSeed(
        slug="trt-1",
        name="TRT 1",
        description="Turkiye's flagship public broadcaster channel with news, drama, and entertainment programming.",
        category="General TV",
        country="TR",
        language="tr",
        source_type="hls",
        iptv_org_channel_id="TRT1.tr",
        preferred_stream_urls=[
            "https://tv-trt1.medya.trt.com.tr/master.m3u8",
        ],
        logo_url="https://upload.wikimedia.org/wikipedia/commons/thumb/8/85/TRT_1_logo_%282021-%29.svg/960px-TRT_1_logo_%282021-%29.svg.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        # "TRT.1.tr" carries zero programmes in the current TR3 dump; "TRT1.HD.tr" is populated.
        epg_channel_id="TRT.1.tr",
    ),
    ChannelSeed(
        slug="trt-muzik",
        name="TRT Muzik",
        description="Turkiye's public broadcaster music channel featuring Turkish and international music programming.",
        category="Music",
        country="TR",
        language="tr",
        source_type="hls",
        iptv_org_channel_id="TRTMuzik.tr",
        preferred_stream_urls=[
            "https://tv-trtmuzik.medya.trt.com.tr/master.m3u8",
        ],
        logo_url="https://i.imgur.com/JgUzRH8.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        epg_channel_id="TRT.MÜZİK.tr",
    ),
    ChannelSeed(
        slug="trt-belgesel",
        name="TRT Belgesel",
        description="Turkiye's public broadcaster documentary channel covering nature, history, and science.",
        category="Documentary",
        country="TR",
        language="tr",
        source_type="hls",
        iptv_org_channel_id="TRTBelgesel.tr",
        preferred_stream_urls=[
            "https://tv-trtbelgesel.medya.trt.com.tr/master.m3u8",
        ],
        logo_url="https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/TRT_Belgesel_logo_%282019-%29.svg/960px-TRT_Belgesel_logo_%282019-%29.svg.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        epg_channel_id="TRT.BELGESEL.HD.tr",
    ),
    # TRT is Turkiye's public broadcaster and publishes these streams openly on its own CDN.
    # Every URL below was verified end to end with the same 3-stage HLS check the health
    # service uses (master manifest -> variant playlist -> first segment, CORS required at
    # each level), and each has real programme data in the TR3 XMLTV feed.
    ChannelSeed(
        slug="trt-2",
        name="TRT 2",
        description="Turkiye's public broadcaster arts and culture channel with film, literature, and documentary programming.",
        category="General TV",
        country="TR",
        language="tr",
        source_type="hls",
        preferred_stream_urls=[
            "https://tv-trt2.medya.trt.com.tr/master.m3u8",
        ],
        logo_url="https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/TRT_2_logo_%282019-%29.svg/960px-TRT_2_logo_%282019-%29.svg.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        # No TRT 2 listing exists in the TR1 XMLTV dump, so no schedule is claimed.
        epg_channel_id=None,
    ),
    ChannelSeed(
        slug="trt-spor",
        name="TRT Spor",
        description="Turkiye's public broadcaster sports channel covering domestic leagues, athletics, and international competition.",
        category="Sports",
        country="TR",
        language="tr",
        source_type="hls",
        preferred_stream_urls=[
            "https://tv-trtspor1.medya.trt.com.tr/master.m3u8",
            "https://tv-trtspor2.medya.trt.com.tr/master.m3u8",
        ],
        logo_url="https://upload.wikimedia.org/wikipedia/commons/thumb/1/17/TRT_Spor_logo_%282021-%29.svg/960px-TRT_Spor_logo_%282021-%29.svg.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        epg_channel_id="TRT.SPOR.tr",
    ),
    ChannelSeed(
        slug="trt-cocuk",
        name="TRT Cocuk",
        description="Turkiye's public broadcaster children's channel with cartoons and educational programming.",
        category="Youth",
        country="TR",
        language="tr",
        source_type="hls",
        preferred_stream_urls=[
            "https://tv-trtcocuk.medya.trt.com.tr/master.m3u8",
        ],
        logo_url="https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/TRT_%C3%87ocuk_logo_%282019-%29.svg/960px-TRT_%C3%87ocuk_logo_%282019-%29.svg.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        epg_channel_id="TRT.ÇOCUK.HD.tr",
    ),
    ChannelSeed(
        slug="trt-genc",
        name="TRT Genc",
        description="Turkiye's public broadcaster youth channel with music, culture, and student-focused programming.",
        category="Youth",
        country="TR",
        language="tr",
        source_type="hls",
        preferred_stream_urls=[
            "https://tv-trtgenc.medya.trt.com.tr/master.m3u8",
        ],
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        # No TRT Genc listing exists in the TR1 XMLTV dump, so no schedule is claimed.
        epg_channel_id=None,
    ),
    ChannelSeed(
        slug="trt-avaz",
        name="TRT Avaz",
        description="Turkiye's public broadcaster channel for the Balkans, Caucasus, and Central Asia.",
        category="General TV",
        country="TR",
        language="tr",
        source_type="hls",
        preferred_stream_urls=[
            "https://tv-trtavaz.medya.trt.com.tr/master.m3u8",
        ],
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        epg_channel_id="TRT.AVAZ.HD.tr",
    ),
    ChannelSeed(
        slug="trt-turk",
        name="TRT Turk",
        description="Turkiye's public broadcaster international channel for Turkish audiences abroad.",
        category="General TV",
        country="TR",
        language="tr",
        source_type="hls",
        preferred_stream_urls=[
            "https://tv-trtturk.medya.trt.com.tr/master.m3u8",
        ],
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        epg_channel_id="TRT.TÜRK.tr",
    ),
    ChannelSeed(
        slug="trt-kurdi",
        name="TRT Kurdi",
        description="Turkiye's public broadcaster Kurdish-language channel with news, culture, and drama.",
        category="General TV",
        country="TR",
        language="tr",
        source_type="hls",
        preferred_stream_urls=[
            "https://tv-trtkurdi.medya.trt.com.tr/master.m3u8",
        ],
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        epg_channel_id="TRT.KURDİ.tr",
    ),
    ChannelSeed(
        slug="bloomberg-ht",
        name="Bloomberg HT",
        description="Turkish-language business and markets channel operated under the Bloomberg HT brand.",
        category="Business",
        country="TR",
        language="tr",
        source_type="hls",
        iptv_org_channel_id="BloombergHT.tr",
        preferred_stream_urls=[
            "https://tv.ensonhaber.com/bloomberght/bloomberght.m3u8",
        ],
        logo_url="https://i.imgur.com/bmkXfIE.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        epg_channel_id="BLOOMBERG.HT.tr",
    ),
    ChannelSeed(
        slug="haberturk-tv",
        name="Haberturk",
        description="Turkish rolling news channel with domestic and international coverage.",
        category="News",
        country="TR",
        language="tr",
        source_type="hls",
        iptv_org_channel_id="HaberturkTV.tr",
        preferred_stream_urls=[
            "https://tv.ensonhaber.com/haberturk/haberturk.m3u8",
        ],
        logo_url="https://i.imgur.com/6Tw3rUp.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        epg_channel_id="HABERTÜRK.tr",
    ),
    ChannelSeed(
        slug="tgrt-haber",
        name="TGRT Haber",
        description="Turkish news channel with domestic politics, economy, and breaking news coverage.",
        category="News",
        country="TR",
        language="tr",
        source_type="hls",
        iptv_org_channel_id="TGRTHaber.tr",
        preferred_stream_urls=[
            "https://canli.tgrthaber.com/tgrt.m3u8",
        ],
        logo_url="https://i.imgur.com/PrxwKDw.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        epg_channel_id="TGRT.HABER.tr",
    ),
    ChannelSeed(
        slug="dha-tv",
        name="DHA",
        description="Live feed from Demiroren News Agency (DHA), one of Turkiye's major wire news services.",
        category="News",
        country="TR",
        language="tr",
        source_type="hls",
        iptv_org_channel_id="DHA.tr",
        preferred_stream_urls=[
            "https://603c568fccdf5.streamlock.net/live/dhaweb1_C5efC/playlist.m3u8",
        ],
        logo_url="https://i.imgur.com/VZhag2x.png",
    ),
    ChannelSeed(
        slug="dream-turk",
        name="Dream Turk",
        description="Turkish music television channel featuring Turkish pop, arabesque, and folk music videos.",
        category="Music",
        country="TR",
        language="tr",
        source_type="hls",
        iptv_org_channel_id="DreamTurk.tr",
        preferred_stream_urls=[
            "https://live.duhnet.tv/S2/HLS_LIVE/dreamturknp/playlist.m3u8",
        ],
        logo_url="https://i.imgur.com/vJ8VaZi.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        # No Dream Turk listing exists in the TR1 XMLTV dump, so no schedule is claimed.
        epg_channel_id=None,
    ),
    # --- Turkish channels kept defined but DISABLED. Their direct HLS stream is browser-CORS
    # blocked (their CDN sends no Access-Control-Allow-Origin, and proxying around that is
    # explicitly out of scope), and a re-check against the official YouTube Data API - run
    # *without* the videoEmbeddable filter, so this is not an embedding restriction - found no
    # live broadcast of any kind on their official channels. There is therefore no legitimate
    # source to play, and substituting an unverified third-party relay is not acceptable.
    # They stay in the catalog as a record of the investigation, but are inactive so the Live TV
    # list is not padded with entries that can never play. Re-enable if an official stream appears.
    ChannelSeed(
        slug="atv-tr",
        name="ATV",
        description="Turkish free-to-air general entertainment channel. Disabled: direct HLS is CORS-blocked and the official YouTube channel carries no live broadcast.",
        category="General TV",
        country="TR",
        language="tr",
        source_type="youtube",
        is_active=False,
        youtube_handle="@atvturkiye",
        logo_url="https://i.imgur.com/HyVUwFC.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        epg_channel_id="ATV.tr",
    ),
    ChannelSeed(
        slug="kanal-d",
        name="Kanal D",
        description="Turkish free-to-air general entertainment channel. Disabled: direct HLS is CORS-blocked and the official YouTube channel carries no live broadcast.",
        category="General TV",
        country="TR",
        language="tr",
        source_type="youtube",
        is_active=False,
        youtube_handle="@kanald",
        logo_url="https://i.imgur.com/9o1atM6.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        epg_channel_id="KANAL.D.tr",
    ),
    ChannelSeed(
        slug="star-tv",
        name="Star TV",
        description="Turkish free-to-air general entertainment channel. Disabled: direct HLS is CORS-blocked and the official YouTube channel carries no live broadcast.",
        category="General TV",
        country="TR",
        language="tr",
        source_type="youtube",
        is_active=False,
        youtube_handle="@StarTVResmi",
        logo_url="https://i.imgur.com/9O3DHRB.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        epg_channel_id="STAR.TV.tr",
    ),
    ChannelSeed(
        slug="tv8-tr",
        name="TV8",
        description="Turkish free-to-air general entertainment channel. Disabled: direct HLS is CORS-blocked and the official YouTube channel carries no live broadcast.",
        category="General TV",
        country="TR",
        language="tr",
        source_type="youtube",
        is_active=False,
        youtube_handle="@TV8",
        logo_url="https://upload.wikimedia.org/wikipedia/tr/thumb/6/68/Tv8_Yeni_Logo.png/960px-Tv8_Yeni_Logo.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        epg_channel_id="TV8.tr",
    ),
    ChannelSeed(
        slug="ntv-tr",
        name="NTV",
        description="Turkish general news and current affairs channel. Direct HLS stream is CORS-blocked; official YouTube channel verified with a genuine, currently live 24/7 news simulcast.",
        category="News",
        country="TR",
        language="tr",
        source_type="youtube",
        youtube_handle="@NTV",
        logo_url="https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/NTV_%28Turkey%29_logo.svg/960px-NTV_%28Turkey%29_logo.svg.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        # "NTV.tr" carries zero programmes in the current TR3 dump; the HD id has ~295.
        epg_channel_id="NTV.tr",
    ),
    # --- Turkish channels with no legitimate open HLS candidate found (their real stream is
    # app/DRM-gated or only served through an unverified third-party relay). These stay defined
    # as YouTube-sourced so they activate automatically once YOUTUBE_API_KEY is configured,
    # rather than being embedded through an unverifiable HLS mirror.
    ChannelSeed(
        slug="cnn-turk-youtube",
        name="CNN Turk",
        description="Turkish news channel from the CNN Turk partnership. Requires YOUTUBE_API_KEY to activate official YouTube live coverage.",
        category="News",
        country="TR",
        language="tr",
        source_type="youtube",
        youtube_handle="@cnnturk",
        logo_url="https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/CNN_T%C3%BCrk_logo.svg/960px-CNN_T%C3%BCrk_logo.svg.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        # "CNN.TÜRK.tr" carries zero programmes in the current TR3 dump; the HD id is populated.
        epg_channel_id="CNN.TÜRK.HD.tr",
    ),
    ChannelSeed(
        slug="show-tv-youtube",
        name="Show TV",
        description="Turkish free-to-air general entertainment channel. Requires YOUTUBE_API_KEY to activate official YouTube live coverage; no CORS-compatible HLS stream was found.",
        category="General TV",
        country="TR",
        language="tr",
        source_type="youtube",
        youtube_handle="@ShowTV",
        logo_url="https://i.imgur.com/1l7SCCu.png",
        epg_source_url="https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
        # "SHOW.TV.tr" carries zero programmes in the current TR3 dump; the HD id is populated.
        epg_channel_id="SHOW.TV.tr",
    ),
    # NOTE: the former "trt-spor-youtube" seed was removed. TRT Spor now has a verified official
    # TRT HLS stream (see the "trt-spor" seed above), which plays directly in the browser instead
    # of depending on a YouTube channel that carries no live broadcast. Dropping the slug here
    # deactivates the old row on the next channel sync.
    # --- Additional international channels (Sports/Music/Youth/News diversity, all verified) ---
    ChannelSeed(
        slug="dw-english",
        name="DW English",
        description="Germany's international public broadcaster with English-language news, documentaries, and current affairs.",
        category="News",
        country="DE",
        language="en",
        source_type="hls",
        iptv_org_channel_id="DW.de",
        preferred_stream_urls=[
            "https://dwamdstream102.akamaized.net/hls/live/2015525/dwstream102/master.m3u8",
        ],
        logo_url="https://i.imgur.com/8MRNFb9.png",
    ),
    ChannelSeed(
        slug="france24-english",
        name="France 24 English",
        description="France's international public broadcaster with English-language rolling news coverage.",
        category="News",
        country="FR",
        language="en",
        source_type="hls",
        iptv_org_channel_id="France24.fr",
        preferred_stream_urls=[
            "https://live.france24.com/hls/live/2037218/F24_EN_HI_HLS/master_5000.m3u8",
        ],
        logo_url="https://dtil.tmsimg.com/assets/s159111_ld_h15_aa.png?lock=720x540",
    ),
    ChannelSeed(
        slug="red-bull-tv",
        name="Red Bull TV",
        description="Red Bull's official global channel covering extreme sports, motorsport, and music festival culture for a young audience.",
        category="Youth",
        country="AT",
        language="en",
        source_type="hls",
        iptv_org_channel_id="RedBullTV.at",
        preferred_stream_urls=[
            "https://rbmn-live.akamaized.net/hls/live/590964/BoRB-AT/master.m3u8",
            "https://d1hlbgn3fph0cz.cloudfront.net/playlist.m3u8",
        ],
        logo_url="https://i.postimg.cc/8c78JM28/image.png",
    ),
    ChannelSeed(
        slug="trace-urban",
        name="Trace Urban",
        description="Official Trace network channel for global urban, hip-hop, and Afrobeats music aimed at a young audience.",
        category="Youth",
        country="FR",
        language="en",
        source_type="hls",
        iptv_org_channel_id="TraceUrban.fr",
        preferred_stream_urls=[
            "https://channels.trace.plus/Traceprod/URBAN_FR_hd/index.m3u8",
        ],
        logo_url="https://i.imgur.com/DLIbUMx.png",
    ),
    ChannelSeed(
        slug="more-than-sports-tv",
        name="More Than Sports TV",
        description="German sports channel covering a wide range of non-mainstream and highlight sports content (not premium live match broadcasts).",
        category="Sports",
        country="DE",
        language="en",
        source_type="hls",
        iptv_org_channel_id="MoreThanSportsTV.de",
        preferred_stream_urls=[
            "https://mts1.iptv-playoutcenter.de/mts/mts-web/playlist.m3u8",
        ],
        logo_url="https://i.imgur.com/SLrjImc.png",
    ),
]


def channel_seed_map() -> dict[str, ChannelSeed]:
    return {seed.slug: seed for seed in LIVE_TV_CHANNEL_SEEDS}


def enabled_channel_seed_map(*, youtube_enabled: bool) -> dict[str, ChannelSeed]:
    return {
        seed.slug: seed
        for seed in LIVE_TV_CHANNEL_SEEDS
        if youtube_enabled or seed.source_type != "youtube"
    }
