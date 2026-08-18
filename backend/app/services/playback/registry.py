from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


PlaybackSourceType = Literal["hls", "mp4", "youtube", "external"]


@dataclass(slots=True)
class PlaybackSourceSeed:
    name: str
    source_type: PlaybackSourceType
    playback_url: str | None = None
    external_video_id: str | None = None
    embed_url: str | None = None
    quality: str | None = None
    language: str | None = "en"
    is_primary: bool = False
    supports_seek: bool = True
    supports_state_tracking: bool = True
    provider_name: str | None = None
    provider_url: str | None = None
    license_note: str | None = None
    source_note: str | None = None


@dataclass(slots=True)
class CuratedPlaybackTitle:
    search_title: str
    title_variants: list[str]
    release_year: int | None
    content_type: str = "movie"
    sources: list[PlaybackSourceSeed] = field(default_factory=list)


def _external(
    *,
    name: str,
    embed_url: str,
    provider_name: str,
    provider_url: str,
    license_note: str,
    source_note: str,
    is_primary: bool = True,
) -> PlaybackSourceSeed:
    return PlaybackSourceSeed(
        name=name,
        source_type="external",
        playback_url=embed_url,
        embed_url=embed_url,
        is_primary=is_primary,
        supports_seek=False,
        supports_state_tracking=False,
        provider_name=provider_name,
        provider_url=provider_url,
        license_note=license_note,
        source_note=source_note,
    )


CURATED_PLAYBACK_TITLES: list[CuratedPlaybackTitle] = [
    CuratedPlaybackTitle(
        search_title="Big Buck Bunny",
        title_variants=["Big Buck Bunny"],
        release_year=2008,
        sources=[
            PlaybackSourceSeed(
                name="Open HLS Stream",
                source_type="hls",
                playback_url="https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
                quality="auto",
                is_primary=True,
                provider_name="Mux Test Streams",
                provider_url="https://test-streams.mux.dev/",
                license_note="Open Big Buck Bunny sample stream used for browser HLS playback testing.",
                source_note="Curated demo HLS source for legal playback validation.",
            ),
            PlaybackSourceSeed(
                name="Open MP4 File",
                source_type="mp4",
                playback_url="https://test.playready.microsoft.com/media/profficialsite/bbb-3840x2160-cfg02-frag-6mbps.mp4",
                quality="2160p",
                provider_name="Microsoft PlayReady Test Content",
                provider_url="https://learn.microsoft.com/playready/advanced/testcontent/playready-3x-test-content",
                license_note="Public Big Buck Bunny MP4 test asset documented by Microsoft.",
                source_note="Alternative HTML5 MP4 playback source for the demo.",
            ),
            _external(
                name="Official Blender Embed",
                embed_url="https://video.blender.org/videos/embed/pAQiVCgv2CsLg79KKXUoMw",
                provider_name="Blender Video",
                provider_url="https://video.blender.org/videos/watch/bf1f3fb5-b119-4f9f-9930-8e20e892b898",
                license_note="Official Blender Foundation Open Movie embed.",
                source_note="Authorized PeerTube embed from Blender Video.",
                is_primary=False,
            ),
        ],
    ),
    CuratedPlaybackTitle(
        search_title="Elephants Dream",
        title_variants=["Elephants Dream"],
        release_year=2006,
        sources=[
            _external(
                name="Official Blender Embed",
                embed_url="https://video.blender.org/videos/embed/rhMeBiBURa2KgsAfkC6kda",
                provider_name="Blender Video",
                provider_url="https://video.blender.org/videos/watch/cccc3e60-0291-4ecc-aa56-39b2e2c7d0d5",
                license_note="Official Blender Foundation Open Movie embed.",
                source_note="Authorized PeerTube embed from Blender Video.",
            )
        ],
    ),
    CuratedPlaybackTitle(
        search_title="Sintel",
        title_variants=["Sintel"],
        release_year=2010,
        sources=[
            _external(
                name="Official Blender Embed",
                embed_url="https://video.blender.org/videos/embed/2PcJe5aZqozRvH7MJ8BTmC",
                provider_name="Blender Video",
                provider_url="https://video.blender.org/videos/watch/0eb052d0-fd51-43e6-aa33-ecdbf77a5d40",
                license_note="Official Blender Foundation Open Movie embed.",
                source_note="Authorized PeerTube embed from Blender Video.",
            )
        ],
    ),
    CuratedPlaybackTitle(
        search_title="Tears of Steel",
        title_variants=["Tears of Steel"],
        release_year=2012,
        sources=[
            PlaybackSourceSeed(
                name="Official YouTube Upload",
                source_type="youtube",
                external_video_id="41hv2tW5Lc4",
                is_primary=True,
                provider_name="Blender Foundation YouTube",
                provider_url="https://youtu.be/41hv2tW5Lc4",
                license_note="Official Blender Foundation YouTube upload referenced from the Blender Video page.",
                source_note="Uses the official YouTube player API; no direct YouTube stream extraction is performed.",
            ),
            _external(
                name="Official Blender Embed",
                embed_url="https://video.blender.org/videos/embed/hs1zJY8mdr3iH2JNmxpeGV",
                provider_name="Blender Video",
                provider_url="https://video.blender.org/videos/watch/8533ea43-4271-4a57-9694-e9d0b35e1aa1",
                license_note="Official Blender Foundation Open Movie embed.",
                source_note="Authorized PeerTube embed from Blender Video.",
                is_primary=False,
            ),
        ],
    ),
    CuratedPlaybackTitle(
        search_title="Cosmos Laundromat",
        title_variants=["Cosmos Laundromat", "Cosmos Laundromat: First Cycle"],
        release_year=2015,
        sources=[
            _external(
                name="Official Blender Embed",
                embed_url="https://video.blender.org/videos/embed/wfW3bDTkUhQKRnEfT9Wpeq",
                provider_name="Blender Video",
                provider_url="https://video.blender.org/videos/watch/f507dfdc-e73e-45a4-9778-d758cbe1ce96",
                license_note="Official Blender Foundation Open Movie embed.",
                source_note="Authorized PeerTube embed from Blender Video.",
            )
        ],
    ),
    CuratedPlaybackTitle(
        search_title="Coffee Run",
        title_variants=["Coffee Run"],
        release_year=2020,
        sources=[
            _external(
                name="Official Blender Embed",
                embed_url="https://video.blender.org/videos/embed/xymLD6rkpHNug3fzzMyhmZ",
                provider_name="Blender Video",
                provider_url="https://video.blender.org/videos/watch/ff8fe61b-026f-4f07-b66b-2a790d6f6ab1",
                license_note="Official Blender Studio short-film embed.",
                source_note="Authorized PeerTube embed from Blender Video.",
            )
        ],
    ),
    CuratedPlaybackTitle(
        search_title="Caminandes 3: Llamigos",
        title_variants=["Caminandes 3: Llamigos"],
        release_year=2016,
        sources=[
            _external(
                name="Official Blender Embed",
                embed_url="https://video.blender.org/videos/embed/5ruRYckTcQMTMQvyqMnVsr",
                provider_name="Blender Video",
                provider_url="https://video.blender.org/videos/watch/23f3ef79-15dc-44c5-aa45-cf92e78a4509",
                license_note="Official Blender Foundation short-film embed.",
                source_note="Authorized PeerTube embed from Blender Video.",
            )
        ],
    ),
    CuratedPlaybackTitle(
        search_title="Agent 327: Operation Barbershop",
        title_variants=["Agent 327: Operation Barbershop"],
        release_year=2017,
        sources=[
            _external(
                name="Official Blender Embed",
                embed_url="https://video.blender.org/videos/embed/5JoZUZzbUdpNqGXpd5QJ5T",
                provider_name="Blender Video",
                provider_url="https://video.blender.org/videos/watch/264ff760-803e-430e-8d81-15648e904183",
                license_note="Official Blender Studio teaser embed.",
                source_note="Authorized PeerTube embed from Blender Video.",
            )
        ],
    ),
    CuratedPlaybackTitle(
        search_title="Glass Half",
        title_variants=["Glass Half"],
        release_year=2015,
        sources=[
            _external(
                name="Official Blender Embed",
                embed_url="https://video.blender.org/videos/embed/dnayqfMS4PAE9pSZ3kyVUb",
                provider_name="Blender Video",
                provider_url="https://video.blender.org/videos/watch/64222c8a-c4c7-4b3b-9850-7fb2078edcf6",
                license_note="Official Blender Studio short-film embed.",
                source_note="Authorized PeerTube embed from Blender Video.",
            )
        ],
    ),
    CuratedPlaybackTitle(
        search_title="Sprite Fright",
        title_variants=["Sprite Fright"],
        release_year=2021,
        sources=[
            _external(
                name="Official Blender Embed",
                embed_url="https://video.blender.org/videos/embed/mziZQzmf95pGMSqk7BPZvi",
                provider_name="Blender Video",
                provider_url="https://video.blender.org/w/mziZQzmf95pGMSqk7BPZvi",
                license_note="Official Blender Studio Open Movie embed.",
                source_note="Authorized PeerTube embed from Blender Video.",
            )
        ],
    ),
    CuratedPlaybackTitle(
        search_title="His Girl Friday",
        title_variants=["His Girl Friday"],
        release_year=1940,
        sources=[
            _external(
                name="Internet Archive Embed",
                embed_url="https://archive.org/embed/HisGirlFriday1940_201505",
                provider_name="Internet Archive",
                provider_url="https://archive.org/details/HisGirlFriday1940_201505",
                license_note="Public-domain film embedded from Internet Archive.",
                source_note="Archive.org embed used for legally accessible public-domain playback.",
            )
        ],
    ),
    CuratedPlaybackTitle(
        search_title="The General",
        title_variants=["The General"],
        release_year=1926,
        sources=[
            _external(
                name="Internet Archive Embed",
                embed_url="https://archive.org/embed/TheGeneral720p1926",
                provider_name="Internet Archive",
                provider_url="https://archive.org/details/TheGeneral720p1926",
                license_note="Public-domain film embedded from Internet Archive.",
                source_note="Archive.org embed used for legally accessible public-domain playback.",
            )
        ],
    ),
    CuratedPlaybackTitle(
        search_title="Night of the Living Dead",
        title_variants=["Night of the Living Dead"],
        release_year=1968,
        sources=[
            _external(
                name="Internet Archive Embed",
                embed_url="https://archive.org/embed/night_of_the_living_dead",
                provider_name="Internet Archive",
                provider_url="https://archive.org/details/night_of_the_living_dead",
                license_note="Public-domain film embedded from Internet Archive.",
                source_note="Archive.org embed used for legally accessible public-domain playback.",
            )
        ],
    ),
    CuratedPlaybackTitle(
        search_title="Plan 9 from Outer Space",
        title_variants=["Plan 9 from Outer Space"],
        release_year=1959,
        sources=[
            _external(
                name="Internet Archive Embed",
                embed_url="https://archive.org/embed/Plan_9_from_Outer_Space_1959",
                provider_name="Internet Archive",
                provider_url="https://archive.org/details/Plan_9_from_Outer_Space_1959",
                license_note="Public-domain film embedded from Internet Archive.",
                source_note="Archive.org embed used for legally accessible public-domain playback.",
            )
        ],
    ),
    CuratedPlaybackTitle(
        search_title="A Trip to the Moon",
        title_variants=["A Trip to the Moon", "Le voyage dans la lune"],
        release_year=1902,
        sources=[
            _external(
                name="Internet Archive Embed",
                embed_url="https://archive.org/embed/Levoyagedanslalune",
                provider_name="Internet Archive",
                provider_url="https://archive.org/details/Levoyagedanslalune",
                license_note="Public-domain film embedded from Internet Archive.",
                source_note="Archive.org embed used for legally accessible public-domain playback.",
            )
        ],
    ),
    CuratedPlaybackTitle(
        search_title="D.O.A.",
        title_variants=["D.O.A.", "DOA"],
        release_year=1949,
        sources=[
            _external(
                name="Internet Archive Embed",
                embed_url="https://archive.org/embed/doa_1949",
                provider_name="Internet Archive",
                provider_url="https://archive.org/details/doa_1949",
                license_note="Public-domain film embedded from Internet Archive.",
                source_note="Archive.org embed used for legally accessible public-domain playback.",
            )
        ],
    ),
]
