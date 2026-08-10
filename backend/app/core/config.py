from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Smart Semantic Web TV Backend"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://app_user:change_me@localhost:5432/smart_semantic_web_tv"
    cors_allowed_origins: str = "http://127.0.0.1:5500"
    jwt_secret_key: str = Field(
        default="change-this-secret-in-env-to-at-least-32-characters",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
