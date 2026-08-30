from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


PlannerResultType = Literal["movie", "series", "live_program"]
PlannerGenerationSource = Literal["gemini", "fallback"]
# A generated plan is only a proposal ("draft") until the user accepts it. Accepting makes it
# "active" for its plan_date; a previously active plan for that same date becomes "superseded"
# and is kept as history rather than deleted.
PlannerPlanStatus = Literal["draft", "active", "superseded"]


class ViewingPlanGenerateRequest(BaseModel):
    plan_date: date
    available_start: time
    available_end: time
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    max_duration_minutes: int | None = Field(default=None, ge=15, le=720)
    preferred_categories: list[str] = Field(default_factory=list)
    include_live: bool = True
    include_vod: bool = True
    preference_text: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def validate_request(self) -> "ViewingPlanGenerateRequest":
        try:
            ZoneInfo(self.timezone)
        except Exception as exc:  # pragma: no cover - defensive, exercised by validation behavior
            raise ValueError("timezone must be a valid IANA timezone.") from exc

        if self.plan_date < date.today():
            raise ValueError("plan_date cannot be in the past.")

        start_dt = datetime.combine(self.plan_date, self.available_start)
        end_dt = datetime.combine(self.plan_date, self.available_end)
        if end_dt <= start_dt:
            raise ValueError("available_end must be later than available_start on the selected date.")
        if not self.include_live and not self.include_vod:
            raise ValueError("At least one of include_live or include_vod must be true.")
        window_minutes = int((end_dt - start_dt) / timedelta(minutes=1))
        if self.max_duration_minutes is not None and self.max_duration_minutes > window_minutes:
            raise ValueError("max_duration_minutes cannot exceed the requested availability window.")
        return self


class ViewingPlanChannelRead(BaseModel):
    id: int
    slug: str | None = None
    name: str
    logo_url: HttpUrl | None = None
    source_type: str | None = None


class ViewingPlanItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: str
    result_type: PlannerResultType
    title: str
    description: str | None = None
    category_label: str
    genres: list[str]
    runtime_minutes: int | None = None
    runtime_display: str
    epg_entry_id: int | None = None
    planned_start: datetime
    planned_end: datetime
    availability_start: datetime | None = None
    availability_end: datetime | None = None
    recommendation_score: float | None = None
    reason: str
    poster_url: HttpUrl | None = None
    backdrop_url: HttpUrl | None = None
    content_slug: str | None = None
    channel: ViewingPlanChannelRead | None = None


class ViewingPlannerLLMItem(BaseModel):
    candidate_id: str
    planned_start: datetime
    planned_end: datetime
    reason: str = Field(min_length=4, max_length=280)


class ViewingPlannerLLMResponse(BaseModel):
    summary: str = Field(min_length=4, max_length=800)
    plan: list[ViewingPlannerLLMItem] = Field(default_factory=list)


class ViewingPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_date: date
    timezone: str
    available_start: datetime
    available_end: datetime
    max_duration_minutes: int
    include_live: bool
    include_vod: bool
    preferred_categories: list[str]
    preference_text: str | None = None
    profile_summary: list[str]
    summary: str
    generation_source: PlannerGenerationSource
    llm_model: str | None = None
    llm_repair_applied: bool
    status: PlannerPlanStatus = "draft"
    is_accepted: bool
    accepted_at: datetime | None = None
    superseded_at: datetime | None = None
    items: list[ViewingPlanItemRead]
    created_at: datetime
    updated_at: datetime


class ViewingPlanListResponse(BaseModel):
    items: list[ViewingPlanRead]
