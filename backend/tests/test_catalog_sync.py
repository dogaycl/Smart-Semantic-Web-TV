from datetime import date

from app.models.catalog_item import CatalogItem
from app.repositories.catalog_repository import CatalogRepository
from app.services.catalog.providers.base import CatalogCandidate, CatalogProvider, CatalogVideoPayload, ExternalCatalogItemPayload
from app.services.catalog.sync_service import CatalogSyncService


class FakeCatalogProvider(CatalogProvider):
    def __init__(self) -> None:
        self.payloads = {
            ("movie", 101): ExternalCatalogItemPayload(
                tmdb_id=101,
                content_type="movie",
                title="Arrival",
                original_title="Arrival",
                overview="Aliens arrive on Earth.",
                genres=[(878, "Science Fiction"), (18, "Drama")],
                release_date=date(2016, 11, 10),
                runtime_minutes=116,
                poster_url="https://example.com/arrival.jpg",
                backdrop_url="https://example.com/arrival-bg.jpg",
                vote_average=7.8,
                popularity=200.0,
                original_language="en",
                status="Released",
                top_cast=["Amy Adams"],
                top_crew=["Denis Villeneuve"],
                tmdb_url="https://www.themoviedb.org/movie/101",
                videos=[
                    CatalogVideoPayload(
                        tmdb_video_id="arrival-trailer",
                        name="Trailer",
                        site="YouTube",
                        type="Trailer",
                        video_key="arrivalkey",
                        official=True,
                    )
                ],
            ),
            ("tv", 202): ExternalCatalogItemPayload(
                tmdb_id=202,
                content_type="tv",
                title="Dark",
                original_title="Dark",
                overview="A family saga with a supernatural twist.",
                genres=[(18, "Drama"), (9648, "Mystery")],
                release_date=date(2017, 12, 1),
                runtime_minutes=53,
                poster_url="https://example.com/dark.jpg",
                backdrop_url="https://example.com/dark-bg.jpg",
                vote_average=8.4,
                popularity=180.0,
                original_language="de",
                status="Ended",
                top_cast=["Louis Hofmann"],
                top_crew=["Baran bo Odar"],
                number_of_seasons=3,
                number_of_episodes=26,
                tmdb_url="https://www.themoviedb.org/tv/202",
            ),
        }

    def is_configured(self) -> bool:
        return True

    def discover_catalog_candidates(self, *, target_items: int) -> list[CatalogCandidate]:
        return [
            CatalogCandidate(tmdb_id=101, content_type="movie", title="Arrival"),
            CatalogCandidate(tmdb_id=202, content_type="tv", title="Dark"),
        ][:target_items]

    def fetch_catalog_item(self, *, tmdb_id: int, content_type: str):
        return self.payloads[(content_type, tmdb_id)]


def test_catalog_sync_upserts_without_duplicates_and_refreshes_data(db_session):
    provider = FakeCatalogProvider()
    repository = CatalogRepository()
    service = CatalogSyncService(provider=provider, repository=repository)

    synced = service.sync_catalog(db=db_session, target_items=2)

    assert len(synced) == 2
    assert repository.count_active(db=db_session) == 2

    arrival = repository.get_by_tmdb(db=db_session, content_type="movie", tmdb_id=101)
    assert arrival is not None
    assert arrival.title == "Arrival"
    assert sorted(genre.name for genre in arrival.genres) == ["Drama", "Science Fiction"]

    provider.payloads[("movie", 101)].overview = "Updated canonical overview."
    provider.payloads[("movie", 101)].vote_average = 8.1

    synced_again = service.sync_catalog(db=db_session, target_items=2)

    assert len(synced_again) == 2
    assert repository.count_active(db=db_session) == 2

    refreshed = repository.get_by_tmdb(db=db_session, content_type="movie", tmdb_id=101)
    assert refreshed is not None
    assert refreshed.overview == "Updated canonical overview."
    assert refreshed.vote_average == 8.1


def test_catalog_sync_does_not_deactivate_pinned_items(db_session):
    # Curator-added movies (bulk import, wired-up playable titles) carry is_pinned=True and must
    # survive the reconciliation sweep even though they are never in the discovered bucket set.
    provider = FakeCatalogProvider()
    repository = CatalogRepository()
    service = CatalogSyncService(provider=provider, repository=repository)

    pinned = CatalogItem(
        slug="movie-open-demo-999999",
        content_type="movie",
        tmdb_id=999999,
        title="Open Demo",
        original_title="Open Demo",
        overview="An obscure open-licensed film TMDB never surfaces.",
        release_date=date(2010, 1, 1),
        runtime_minutes=90,
        tmdb_url="https://www.themoviedb.org/movie/999999",
        is_active=True,
        is_pinned=True,
    )
    db_session.add(pinned)
    db_session.commit()

    service.sync_catalog(db=db_session, target_items=2)

    survivor = repository.get_by_tmdb(db=db_session, content_type="movie", tmdb_id=999999)
    assert survivor is not None
    assert survivor.is_active is True, "the reconciliation sweep must not touch pinned items"
    # The regular bucket items still reconcile normally.
    assert repository.count_active(db=db_session) == 3
