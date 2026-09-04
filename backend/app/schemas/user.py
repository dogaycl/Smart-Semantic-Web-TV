from datetime import datetime
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# An avatar reference is either a predefined avatar token ("preset:<slug>") that the
# frontend renders as a gradient tile, or an absolute http(s) image URL. Keeping it a
# plain string (instead of HttpUrl) lets the project ship profile pictures without any
# file-upload infrastructure while still persisting the choice in the database.
AVATAR_PRESET_PATTERN = re.compile(r"^preset:[a-z0-9-]{1,40}$")
AVATAR_MAX_LENGTH = 500


def validate_avatar_reference(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) > AVATAR_MAX_LENGTH:
        raise ValueError("Avatar reference is too long.")
    if AVATAR_PRESET_PATTERN.match(trimmed):
        return trimmed
    if trimmed.startswith(("http://", "https://")):
        return trimmed
    raise ValueError("Avatar must be a preset token (preset:<id>) or an http(s) URL.")


class UserProfileBase(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=AVATAR_MAX_LENGTH)
    interests: list[str] = Field(default_factory=list)
    preferred_categories: list[str] = Field(default_factory=list)


class UserProfileRead(UserProfileBase):
    model_config = ConfigDict(from_attributes=True)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: str
    created_at: datetime
    profile: UserProfileRead
