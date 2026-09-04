from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, HttpUrl


ContentType = Literal["movie", "tv"]


class CatalogAttributionRead(BaseModel):
    source: str
    notice: str
    url: HttpUrl
    logo_url: HttpUrl


class CatalogVideoRead(BaseModel):
    name: str
    site: str
    type: str
    official: bool
    published_at: str | None = None
    embed_url: HttpUrl | None = None


class CatalogSeasonRead(BaseModel):
    season_number: int
    name: str
    overview: str | None = None
    air_date: date | None = None
    episode_count: int | None = None
    poster_url: HttpUrl | None = None


class CatalogItemSummaryRead(BaseModel):
    id: int
    slug: str
    content_type: ContentType
    tmdb_id: int
    title: str
    original_title: str | None = None
    overview: str | None = None
    genres: list[str]
    release_date: date | None = None
    year: int | None = None
    runtime_minutes: int | None = None
    runtime_display: str
    poster_url: HttpUrl | None = None
    backdrop_url: HttpUrl | None = None
    rating: float | None = None
    popularity: float | None = None
    language: str | None = None
    status: str | None = None
    number_of_seasons: int | None = None
    number_of_episodes: int | None = None
    category_label: str
    primary_genre: str
    tmdb_url: HttpUrl
    has_trailer: bool
    is_playable: bool = False
    last_synced_at: str | None = None


class CatalogItemDetailRead(CatalogItemSummaryRead):
    top_cast: list[str]
    top_crew: list[str]
    videos: list[CatalogVideoRead]
    seasons: list[CatalogSeasonRead]
    trailer: CatalogVideoRead | None = None
    related_items: list[CatalogItemSummaryRead]
    attribution: CatalogAttributionRead


class CatalogListResponse(BaseModel):
    items: list[CatalogItemSummaryRead]
    total: int
    limit: int
    offset: int
    attribution: CatalogAttributionRead
