import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import AVATAR_MAX_LENGTH, UserRead, validate_avatar_reference

USERNAME_PATTERN = r"^[A-Za-z0-9_.-]+$"


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=USERNAME_PATTERN)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=AVATAR_MAX_LENGTH)
    interests: list[str] = Field(default_factory=list)
    preferred_categories: list[str] = Field(default_factory=list)

    @field_validator("avatar_url")
    @classmethod
    def _validate_avatar(cls, value: str | None) -> str | None:
        return validate_avatar_reference(value)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        has_letter = re.search(r"[A-Za-z]", value)
        has_digit = re.search(r"\d", value)
        if not has_letter or not has_digit:
            raise ValueError("Password must include at least one letter and one digit.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
