from datetime import date

from app.models.playback_source import PlaybackSource
from app.repositories.catalog_repository import CatalogRepository
from app.services.catalog.providers.base import CatalogCandidate, ExternalCatalogItemPayload
from app.services.catalog.sync_service import CatalogSyncService
from app.services.playback import sync_service as playback_sync_module
from app.services.playback.registry import CuratedPlaybackTitle, PlaybackSourceSeed
from app.services.playback.sync_service import PlaybackCatalogSyncService


class FakeSearchableProvider:
    def is_configured(self) -> bool:
        return True

    def discover_catalog_candidates(self, *, target_items: int):
        return []

    def search_catalog_item(self, *, title: str, content_type: str, release_year: int | None = None):
        return CatalogCandidate(tmdb_id=10378, content_type="movie", title="Big Buck Bunny")

    def fetch_catalog_item(self, *, tmdb_id: int, content_type: str):
        return ExternalCatalogItemPayload(
            tmdb_id=10378,
            content_type="movie",
            title="Big Buck Bunny",
            original_title="Big Buck Bunny",
            overview="A giant rabbit gets even.",
            genres=[(16, "Animation")],
            release_date=date(2008, 4, 10),
            runtime_minutes=10,
            poster_url="https://example.com/bunny-poster.jpg",
            backdrop_url="https://example.com/bunny-backdrop.jpg",
            vote_average=7.3,
            popularity=44.2,
            original_language="en",
            status="Released",
            top_cast=[],
            top_crew=["Sacha Goedegebure"],
            tmdb_url="https://www.themoviedb.org/movie/10378",
        )


def test_playback_sync_service_imports_curated_titles_without_duplicates(db_session, monkeypatch):
    provider = FakeSearchableProvider()
    repository = CatalogRepository()
    catalog_sync_service = CatalogSyncService(provider=provider, repository=repository)
    service = PlaybackCatalogSyncService(
        provider=provider,
        catalog_repository=repository,
        catalog_sync_service=catalog_sync_service,
    )

    monkeypatch.setattr(
        playback_sync_module,
        "CURATED_PLAYBACK_TITLES",
        [
            CuratedPlaybackTitle(
                search_title="Big Buck Bunny",
                title_variants=["Big Buck Bunny"],
                release_year=2008,
                sources=[
                    PlaybackSourceSeed(
                        name="Open HLS Stream",
                        source_type="hls",
                        playback_url="https://example.com/bunny.m3u8",
                        is_primary=True,
                    )
                ],
            )
        ],
    )

    service.sync_curated_catalog(db=db_session)
    service.sync_curated_catalog(db=db_session)

    item = repository.get_by_tmdb(db=db_session, content_type="movie", tmdb_id=10378)
    assert item is not None
    assert item.title == "Big Buck Bunny"

    sources = db_session.query(PlaybackSource).filter(PlaybackSource.content_item_id == item.id).all()
    assert len(sources) == 1
    assert sources[0].name == "Open HLS Stream"


def test_playback_sync_service_reactivates_curated_item_after_bulk_catalog_sync(db_session, monkeypatch):
    # Regression test: PART 2 of the real-credentials activation pass found that running the
    # bulk TMDB CatalogSyncService.sync_catalog() (which deactivates any catalog item not present
    # in the freshly discovered TMDB set) can deactivate a curated legally-playable title, since
    # obscure open-license demo films never appear in TMDB's popularity-sorted discover results.
    # The catalog router already calls sync_service.ensure_ready() followed by
    # playback_sync_service.ensure_ready() on every relevant request - this proves that sequence
    # actually restores the curated item (and its real PlaybackSource) instead of leaving it
    # hidden from GET /api/catalog.
    provider = FakeSearchableProvider()
    repository = CatalogRepository()
    catalog_sync_service = CatalogSyncService(provider=provider, repository=repository)
    service = PlaybackCatalogSyncService(
        provider=provider,
        catalog_repository=repository,
        catalog_sync_service=catalog_sync_service,
    )
    curated_titles = [
        CuratedPlaybackTitle(
            search_title="Big Buck Bunny",
            title_variants=["Big Buck Bunny"],
            release_year=2008,
            sources=[
                PlaybackSourceSeed(
                    name="Open HLS Stream",
                    source_type="hls",
                    playback_url="https://example.com/bunny.m3u8",
                    is_primary=True,
                )
            ],
        )
    ]
    monkeypatch.setattr(playback_sync_module, "CURATED_PLAYBACK_TITLES", curated_titles)

    service.sync_curated_catalog(db=db_session)
    curated_item = repository.get_by_tmdb(db=db_session, content_type="movie", tmdb_id=10378)
    assert curated_item.is_active is True

    # Simulate a bulk TMDB resync that discovers only unrelated, currently-popular titles -
    # Big Buck Bunny is not among them, so the bulk sync deactivates it (this is correct
    # behavior for the bulk sync in isolation).
    unrelated_candidate = CatalogCandidate(tmdb_id=99999, content_type="movie", title="Some Popular Movie")
    original_fetch_catalog_item = provider.fetch_catalog_item

    def fetch_catalog_item(*, tmdb_id: int, content_type: str):
        if tmdb_id == 99999:
            return ExternalCatalogItemPayload(
                tmdb_id=99999,
                content_type="movie",
                title="Some Popular Movie",
                original_title="Some Popular Movie",
                overview="A currently popular movie unrelated to the curated demo catalog.",
                genres=[(28, "Action")],
                release_date=date(2026, 1, 1),
                runtime_minutes=110,
                poster_url="https://example.com/popular-poster.jpg",
                backdrop_url="https://example.com/popular-backdrop.jpg",
                vote_average=7.0,
                popularity=500.0,
                original_language="en",
                status="Released",
                top_cast=[],
                top_crew=[],
                tmdb_url="https://www.themoviedb.org/movie/99999",
            )
        return original_fetch_catalog_item(tmdb_id=tmdb_id, content_type=content_type)

    monkeypatch.setattr(provider, "discover_catalog_candidates", lambda *, target_items: [unrelated_candidate])
    monkeypatch.setattr(provider, "fetch_catalog_item", fetch_catalog_item)
    catalog_sync_service.sync_catalog(db=db_session)

    curated_item = repository.get_by_tmdb(db=db_session, content_type="movie", tmdb_id=10378)
    assert curated_item.is_active is False, "bulk sync should deactivate titles TMDB no longer surfaces"

    # The router calls playback_sync_service.ensure_ready() right after sync_service.ensure_ready()
    # on every catalog request - reproduce that here directly via sync_curated_catalog().
    service.sync_curated_catalog(db=db_session)

    curated_item = repository.get_by_tmdb(db=db_session, content_type="movie", tmdb_id=10378)
    assert curated_item.is_active is True, "playback sync must restore a curated item the bulk sync deactivated"
    sources = db_session.query(PlaybackSource).filter(PlaybackSource.content_item_id == curated_item.id).all()
    assert len(sources) == 1
    assert sources[0].is_active is True


def test_playback_sync_service_updates_existing_source_in_place(db_session, monkeypatch):
    provider = FakeSearchableProvider()
    repository = CatalogRepository()
    catalog_sync_service = CatalogSyncService(provider=provider, repository=repository)
    service = PlaybackCatalogSyncService(
        provider=provider,
        catalog_repository=repository,
        catalog_sync_service=catalog_sync_service,
    )

    monkeypatch.setattr(
        playback_sync_module,
        "CURATED_PLAYBACK_TITLES",
        [
            CuratedPlaybackTitle(
                search_title="Big Buck Bunny",
                title_variants=["Big Buck Bunny"],
                release_year=2008,
                sources=[
                    PlaybackSourceSeed(
                        name="Open HLS Stream",
                        source_type="hls",
                        playback_url="https://example.com/old.m3u8",
                        is_primary=True,
                    )
                ],
            )
        ],
    )
    service.sync_curated_catalog(db=db_session)

    monkeypatch.setattr(
        playback_sync_module,
        "CURATED_PLAYBACK_TITLES",
        [
            CuratedPlaybackTitle(
                search_title="Big Buck Bunny",
                title_variants=["Big Buck Bunny"],
                release_year=2008,
                sources=[
                    PlaybackSourceSeed(
                        name="Open HLS Stream",
                        source_type="hls",
                        playback_url="https://example.com/new.m3u8",
                        is_primary=True,
                    )
                ],
            )
        ],
    )
    service.sync_curated_catalog(db=db_session)

    item = repository.get_by_tmdb(db=db_session, content_type="movie", tmdb_id=10378)
    assert item is not None
    sources = db_session.query(PlaybackSource).filter(PlaybackSource.content_item_id == item.id).all()
    assert len(sources) == 1
    assert sources[0].playback_url == "https://example.com/new.m3u8"
