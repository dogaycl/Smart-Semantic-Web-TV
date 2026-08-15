from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


ResultType = Literal["movie", "series", "live_program"]
AvailabilityKind = Literal["vod", "live", "upcoming_live"]


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=240)
    limit: int = Field(default=12, ge=1, le=30)
    window_hours: int | None = Field(default=None, ge=1, le=72)


class DiscoveryChannelRead(BaseModel):
    id: int
    slug: str | None = None
    name: str
    logo_url: HttpUrl | None = None
    source_type: str | None = None


class DiscoveryAvailabilityRead(BaseModel):
    kind: AvailabilityKind
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    label: str


class DiscoveryResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    result_type: ResultType
    score: float
    explanation: str
    title: str
    description: str | None = None
    category_label: str
    genres: list[str]
    language: str | None = None
    runtime_minutes: int | None = None
    runtime_display: str
    year: int | None = None
    release_date: date | None = None
    rating: float | None = None
    popularity: float | None = None
    poster_url: HttpUrl | None = None
    backdrop_url: HttpUrl | None = None
    content_slug: str | None = None
    channel: DiscoveryChannelRead | None = None
    availability: DiscoveryAvailabilityRead


class SemanticSearchResponse(BaseModel):
    query: str
    embedding_enabled: bool
    applied_filters: list[str]
    results: list[DiscoveryResultRead]


class RecommendationResponse(BaseModel):
    generated_at: datetime
    embedding_enabled: bool
    profile_summary: list[str]
    results: list[DiscoveryResultRead]
