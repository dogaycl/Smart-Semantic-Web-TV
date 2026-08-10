from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class UserProfileBase(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    avatar_url: HttpUrl | None = None
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
