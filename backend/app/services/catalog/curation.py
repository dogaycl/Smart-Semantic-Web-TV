from dataclasses import dataclass, field
from typing import Literal


ContentType = Literal["movie", "tv"]


@dataclass(slots=True)
class CatalogBucket:
    name: str
    content_type: ContentType
    genre_names: list[str] = field(default_factory=list)
    pages: int = 1
    sort_by: str = "popularity.desc"
    min_vote_count: int = 50
    min_vote_average: float = 6.0


CATALOG_BUCKETS: list[CatalogBucket] = [
    CatalogBucket(
        name="movie-action",
        content_type="movie",
        genre_names=["Action"],
        pages=2,
        min_vote_count=250,
        min_vote_average=6.5,
    ),
    CatalogBucket(
        name="movie-comedy",
        content_type="movie",
        genre_names=["Comedy"],
        pages=2,
        min_vote_count=180,
        min_vote_average=6.2,
    ),
    CatalogBucket(
        name="movie-drama",
        content_type="movie",
        genre_names=["Drama"],
        pages=2,
        min_vote_count=180,
        min_vote_average=6.5,
    ),
    CatalogBucket(
        name="movie-scifi",
        content_type="movie",
        genre_names=["Science Fiction"],
        pages=2,
        min_vote_count=180,
        min_vote_average=6.3,
    ),
    CatalogBucket(
        name="movie-documentary",
        content_type="movie",
        genre_names=["Documentary"],
        pages=1,
        min_vote_count=40,
        min_vote_average=6.5,
    ),
    CatalogBucket(
        name="tv-drama",
        content_type="tv",
        genre_names=["Drama"],
        pages=2,
        min_vote_count=120,
        min_vote_average=6.8,
    ),
    CatalogBucket(
        name="tv-comedy",
        content_type="tv",
        genre_names=["Comedy"],
        pages=1,
        min_vote_count=100,
        min_vote_average=6.5,
    ),
    CatalogBucket(
        name="tv-scifi",
        content_type="tv",
        genre_names=["Sci-Fi & Fantasy"],
        pages=2,
        min_vote_count=100,
        min_vote_average=6.5,
    ),
    CatalogBucket(
        name="tv-action",
        content_type="tv",
        genre_names=["Action & Adventure"],
        pages=1,
        min_vote_count=100,
        min_vote_average=6.3,
    ),
    CatalogBucket(
        name="tv-documentary",
        content_type="tv",
        genre_names=["Documentary"],
        pages=1,
        min_vote_count=25,
        min_vote_average=6.5,
    ),
]
