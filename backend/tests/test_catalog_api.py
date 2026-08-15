from datetime import date, datetime, timezone

from app.api.routers import catalog as catalog_router
from app.models.catalog_genre import CatalogGenre
from app.models.catalog_item import CatalogItem
from app.models.catalog_season import CatalogSeason
from app.models.catalog_video import CatalogVideo


def _freeze_sync(monkeypatch):
    monkeypatch.setattr(catalog_router.sync_service, "ensure_ready", lambda **kwargs: None)


def _create_catalog_item(db_session, **overrides):
    payload = {
        "slug": "movie-dune-part-two-693134",
        "content_type": "movie",
        "tmdb_id": 693134,
        "title": "Dune: Part Two",
        "original_title": "Dune: Part Two",
        "overview": "Paul Atreides unites with Chani and the Fremen.",
        "release_date": date(2024, 2, 27),
        "runtime_minutes": 166,
        "poster_url": "https://example.com/dune-poster.jpg",
        "backdrop_url": "https://example.com/dune-backdrop.jpg",
        "vote_average": 8.2,
        "popularity": 445.6,
        "original_language": "en",
        "status": "Released",
        "top_cast": ["Timothee Chalamet", "Zendaya"],
        "top_crew": ["Denis Villeneuve"],
        "tmdb_url": "https://www.themoviedb.org/movie/693134",
        "is_active": True,
        "last_synced_at": datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc),
    }
    payload.update(overrides)
    item = CatalogItem(**payload)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def test_catalog_listing_supports_filters_and_search(client, db_session, monkeypatch):
    _freeze_sync(monkeypatch)
    dune = _create_catalog_item(db_session)
    dark = _create_catalog_item(
        db_session,
        slug="series-dark-70523",
        content_type="tv",
        tmdb_id=70523,
        title="Dark",
        original_title="Dark",
        overview="Time travel mystery.",
        release_date=date(2017, 12, 1),
        runtime_minutes=53,
        vote_average=8.4,
        popularity=180.0,
        original_language="de",
        status="Ended",
        tmdb_url="https://www.themoviedb.org/tv/70523",
    )
    db_session.add_all(
        [
            CatalogGenre(content_item_id=dune.id, tmdb_genre_id=878, name="Science Fiction"),
            CatalogGenre(content_item_id=dune.id, tmdb_genre_id=12, name="Adventure"),
            CatalogGenre(content_item_id=dark.id, tmdb_genre_id=18, name="Drama"),
        ]
    )
    db_session.commit()

    response = client.get("/api/catalog/movies", params={"category": "Science Fiction", "search": "dune"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == "Dune: Part Two"
    assert payload["items"][0]["content_type"] == "movie"
    assert payload["items"][0]["genres"] == ["Adventure", "Science Fiction"]


def test_catalog_detail_returns_trailer_seasons_and_related_items(client, db_session, monkeypatch):
    _freeze_sync(monkeypatch)
    dune = _create_catalog_item(db_session)
    dune_related = _create_catalog_item(
        db_session,
        slug="movie-arrival-329865",
        tmdb_id=329865,
        title="Arrival",
        original_title="Arrival",
        overview="A linguist works with the military.",
        release_date=date(2016, 11, 10),
        runtime_minutes=116,
        vote_average=7.8,
        popularity=200.0,
        tmdb_url="https://www.themoviedb.org/movie/329865",
    )
    db_session.add_all(
        [
            CatalogGenre(content_item_id=dune.id, tmdb_genre_id=878, name="Science Fiction"),
            CatalogGenre(content_item_id=dune_related.id, tmdb_genre_id=878, name="Science Fiction"),
            CatalogVideo(
                content_item_id=dune.id,
                tmdb_video_id="dune-trailer-1",
                name="Official Trailer",
                site="YouTube",
                type="Trailer",
                video_key="dunetrailer",
                official=True,
            ),
            CatalogSeason(
                content_item_id=dune.id,
                tmdb_season_id=1,
                season_number=1,
                name="Bonus Material",
                episode_count=3,
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/catalog/movie-dune-part-two-693134")

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Dune: Part Two"
    assert payload["trailer"]["embed_url"] == "https://www.youtube.com/embed/dunetrailer"
    assert payload["seasons"][0]["name"] == "Bonus Material"
    assert payload["related_items"][0]["title"] == "Arrival"
    assert payload["attribution"]["source"] == "TMDB"
