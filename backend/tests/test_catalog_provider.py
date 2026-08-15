from datetime import date, datetime, timezone

from app.services.catalog.curation import CatalogBucket
from app.services.catalog.providers.tmdb_provider import TMDBProvider


def test_tmdb_provider_discovers_candidates_without_duplicates(monkeypatch):
    provider = TMDBProvider()

    monkeypatch.setattr(
        "app.services.catalog.providers.tmdb_provider.CATALOG_BUCKETS",
        [
            CatalogBucket(name="movie-action", content_type="movie", genre_names=["Action"], pages=1),
            CatalogBucket(name="tv-scifi", content_type="tv", genre_names=["Sci-Fi & Fantasy"], pages=1),
        ],
    )

    def fake_request(path, *, params=None):
        if path == "/genre/movie/list":
            return {"genres": [{"id": 28, "name": "Action"}]}
        if path == "/genre/tv/list":
            return {"genres": [{"id": 10765, "name": "Sci-Fi & Fantasy"}]}
        if path == "/discover/movie":
            assert params["with_genres"] == "28"
            return {
                "results": [
                    {"id": 11, "title": "Dune: Part Two"},
                    {"id": 11, "title": "Dune: Part Two"},
                ]
            }
        if path == "/discover/tv":
            assert params["with_genres"] == "10765"
            return {"results": [{"id": 22, "name": "The Last of Us"}]}
        raise AssertionError(f"Unexpected path: {path}")

    monkeypatch.setattr(provider, "_request_json", fake_request)

    candidates = provider.discover_catalog_candidates(target_items=10)

    assert [(item.content_type, item.tmdb_id, item.title) for item in candidates] == [
        ("movie", 11, "Dune: Part Two"),
        ("tv", 22, "The Last of Us"),
    ]


def test_tmdb_provider_maps_movie_details_and_images(monkeypatch):
    provider = TMDBProvider()

    def fake_request(path, *, params=None):
        if path == "/configuration":
            return {"images": {"secure_base_url": "https://image.tmdb.org/t/p/", "poster_sizes": ["w500"], "backdrop_sizes": ["original"]}}
        if path == "/movie/693134":
            return {
                "title": "Dune: Part Two",
                "original_title": "Dune: Part Two",
                "overview": "Paul Atreides unites with the Fremen.",
                "genres": [
                    {"id": 878, "name": "Science Fiction"},
                    {"id": 12, "name": "Adventure"},
                ],
                "release_date": "2024-02-27",
                "runtime": 166,
                "poster_path": "/poster.jpg",
                "backdrop_path": "/backdrop.jpg",
                "vote_average": 8.2,
                "popularity": 445.6,
                "original_language": "en",
                "status": "Released",
                "videos": {
                    "results": [
                        {
                            "id": "vid-1",
                            "name": "Official Trailer",
                            "site": "YouTube",
                            "type": "Trailer",
                            "key": "abcd1234",
                            "official": True,
                            "published_at": "2024-01-01T10:00:00Z",
                            "iso_639_1": "en",
                            "iso_3166_1": "US",
                        }
                    ]
                },
                "credits": {
                    "cast": [{"name": "Timothee Chalamet"}, {"name": "Zendaya"}],
                    "crew": [{"name": "Denis Villeneuve", "job": "Director"}],
                },
            }
        raise AssertionError(f"Unexpected path: {path}")

    monkeypatch.setattr(provider, "_request_json", fake_request)

    item = provider.fetch_catalog_item(tmdb_id=693134, content_type="movie")

    assert item.title == "Dune: Part Two"
    assert item.release_date == date(2024, 2, 27)
    assert item.runtime_minutes == 166
    assert item.poster_url == "https://image.tmdb.org/t/p/w500/poster.jpg"
    assert item.backdrop_url == "https://image.tmdb.org/t/p/original/backdrop.jpg"
    assert item.genres == [(878, "Science Fiction"), (12, "Adventure")]
    assert item.top_cast == ["Timothee Chalamet", "Zendaya"]
    assert item.top_crew == ["Denis Villeneuve"]
    assert item.videos[0].video_key == "abcd1234"
    assert item.videos[0].published_at == datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)


def test_tmdb_provider_maps_tv_details_and_seasons(monkeypatch):
    provider = TMDBProvider()

    def fake_request(path, *, params=None):
        if path == "/configuration":
            return {"images": {"secure_base_url": "https://image.tmdb.org/t/p/", "poster_sizes": ["w500"], "backdrop_sizes": ["original"]}}
        if path == "/tv/1399":
            return {
                "name": "Game of Thrones",
                "original_name": "Game of Thrones",
                "overview": "Nine noble families fight for control over Westeros.",
                "genres": [{"id": 10765, "name": "Sci-Fi & Fantasy"}],
                "first_air_date": "2011-04-17",
                "episode_run_time": [55],
                "poster_path": "/got-poster.jpg",
                "backdrop_path": "/got-backdrop.jpg",
                "vote_average": 8.5,
                "popularity": 322.1,
                "original_language": "en",
                "status": "Ended",
                "number_of_seasons": 8,
                "number_of_episodes": 73,
                "created_by": [{"name": "David Benioff"}, {"name": "D. B. Weiss"}],
                "seasons": [
                    {
                        "id": 101,
                        "season_number": 1,
                        "name": "Season 1",
                        "overview": "The first season.",
                        "air_date": "2011-04-17",
                        "episode_count": 10,
                        "poster_path": "/season1.jpg",
                    }
                ],
                "videos": {"results": []},
                "aggregate_credits": {
                    "cast": [{"name": "Emilia Clarke"}, {"name": "Kit Harington"}],
                    "crew": [{"name": "Miguel Sapochnik", "jobs": [{"job": "Director"}]}],
                },
            }
        raise AssertionError(f"Unexpected path: {path}")

    monkeypatch.setattr(provider, "_request_json", fake_request)

    item = provider.fetch_catalog_item(tmdb_id=1399, content_type="tv")

    assert item.title == "Game of Thrones"
    assert item.release_date == date(2011, 4, 17)
    assert item.runtime_minutes == 55
    assert item.number_of_seasons == 8
    assert item.number_of_episodes == 73
    assert item.top_cast == ["Emilia Clarke", "Kit Harington"]
    assert item.top_crew[:2] == ["David Benioff", "D. B. Weiss"]
    assert item.seasons[0].season_number == 1
    assert item.seasons[0].poster_url == "https://image.tmdb.org/t/p/w500/season1.jpg"
