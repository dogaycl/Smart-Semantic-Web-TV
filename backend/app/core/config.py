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
    youtube_api_key: str | None = None
    gemini_api_key: str | None = None
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_embedding_dimensions: int = 768
    gemini_viewing_planner_model: str = "gemini-3.6-flash"
    gemini_assistant_model: str = "gemini-3.6-flash"
    tmdb_api_key: str | None = None
    tmdb_access_token: str | None = None
    tmdb_language: str = "en-US"
    tmdb_region: str = "US"
    jwt_secret_key: str = Field(
        default="change-this-secret-in-env-to-at-least-32-characters",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    live_tv_auto_sync: bool = True
    live_tv_status_ttl_minutes: int = 10
    live_tv_epg_ttl_minutes: int = 360
    live_tv_default_epg_window_hours: int = 4
    live_tv_request_timeout_seconds: float = 12.0
    catalog_auto_sync: bool = True
    catalog_sync_ttl_minutes: int = 1440
    catalog_sync_target_items: int = 160
    catalog_request_timeout_seconds: float = 12.0
    playback_catalog_auto_sync: bool = True
    playback_health_checks_enabled: bool = True
    playback_health_ttl_minutes: int = 180
    playback_request_timeout_seconds: float = 10.0
    search_index_auto_sync: bool = True
    search_index_epg_window_hours: int = 48
    search_request_timeout_seconds: float = 12.0
    recommendation_default_window_hours: int = 12
    viewing_planner_candidate_limit: int = 18
    viewing_planner_max_items: int = 6
    # Weights for the deterministic candidate ranking that runs before Gemini sees anything.
    # Kept here rather than inline in the service so the ranking can be tuned in one place.
    viewing_planner_weight_recommendation: float = 0.65
    viewing_planner_weight_request: float = 0.25
    viewing_planner_weight_category: float = 0.10
    watch_party_host_reconnect_grace_seconds: int = 30
    watch_party_chat_history_limit: int = 40
    watch_party_chat_message_max_length: int = 400
    watch_party_drift_threshold_seconds: float = 1.5
    watch_party_sync_request_interval_seconds: int = 12


@lru_cache
def get_settings() -> Settings:
    return Settings()
