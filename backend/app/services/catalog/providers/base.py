from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal


ContentType = Literal["movie", "tv"]


@dataclass(slots=True)
class CatalogCandidate:
    tmdb_id: int
    content_type: ContentType
    title: str


@dataclass(slots=True)
class CatalogVideoPayload:
    tmdb_video_id: str
    name: str
    site: str
    type: str
    video_key: str
    official: bool = False
    language: str | None = None
    country: str | None = None
    published_at: datetime | None = None


@dataclass(slots=True)
class CatalogSeasonPayload:
    tmdb_season_id: int | None
    season_number: int
    name: str
    overview: str | None = None
    air_date: date | None = None
    episode_count: int | None = None
    poster_url: str | None = None


@dataclass(slots=True)
class ExternalCatalogItemPayload:
    tmdb_id: int
    content_type: ContentType
    title: str
    original_title: str | None
    overview: str | None
    genres: list[tuple[int, str]] = field(default_factory=list)
    release_date: date | None = None
    runtime_minutes: int | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    vote_average: float | None = None
    popularity: float | None = None
    original_language: str | None = None
    status: str | None = None
    top_cast: list[str] = field(default_factory=list)
    top_crew: list[str] = field(default_factory=list)
    number_of_seasons: int | None = None
    number_of_episodes: int | None = None
    tmdb_url: str = ""
    seasons: list[CatalogSeasonPayload] = field(default_factory=list)
    videos: list[CatalogVideoPayload] = field(default_factory=list)


class CatalogProvider(ABC):
    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def discover_catalog_candidates(self, *, target_items: int) -> list[CatalogCandidate]:
        raise NotImplementedError

    @abstractmethod
    def fetch_catalog_item(self, *, tmdb_id: int, content_type: ContentType) -> ExternalCatalogItemPayload:
        raise NotImplementedError
