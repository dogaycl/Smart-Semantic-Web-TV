from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.user import AVATAR_MAX_LENGTH, UserRead, validate_avatar_reference

ContentType = Literal["content", "program"]


class FavoriteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    content_id: str
    added_at: datetime


class WatchHistoryUpsertRequest(BaseModel):
    content_id: str = Field(min_length=1, max_length=255)
    content_type: ContentType = "content"
    watch_position_seconds: int = Field(ge=0)
    total_watched_duration_seconds: int = Field(ge=0)
    is_completed: bool = False
    last_watched_at: datetime | None = None

    @field_validator("last_watched_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class WatchHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    content_id: str
    content_type: ContentType
    watch_position_seconds: int
    total_watched_duration_seconds: int
    is_completed: bool
    last_watched_at: datetime
    created_at: datetime
    updated_at: datetime


class UserProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=AVATAR_MAX_LENGTH)
    interests: list[str] | None = None
    preferred_categories: list[str] | None = None

    @field_validator("avatar_url")
    @classmethod
    def _validate_avatar(cls, value: str | None) -> str | None:
        return validate_avatar_reference(value)


class UserProfileUpdateResponse(UserRead):
    pass
