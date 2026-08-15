import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.api.deps.db import get_db
from app.core.config import get_settings
from app.db.base import Base
from app.main import app

TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def test_settings():
    settings = get_settings()
    original_auto_sync = settings.live_tv_auto_sync
    original_youtube_api_key = settings.youtube_api_key
    original_timeout = settings.live_tv_request_timeout_seconds
    original_catalog_auto_sync = settings.catalog_auto_sync
    original_tmdb_api_key = settings.tmdb_api_key
    original_tmdb_access_token = settings.tmdb_access_token
    original_catalog_timeout = settings.catalog_request_timeout_seconds
    original_catalog_target = settings.catalog_sync_target_items
    original_gemini_api_key = settings.gemini_api_key
    original_gemini_embedding_model = settings.gemini_embedding_model
    original_gemini_dimensions = settings.gemini_embedding_dimensions
    original_gemini_viewing_planner_model = settings.gemini_viewing_planner_model
    original_search_auto_sync = settings.search_index_auto_sync
    original_search_epg_window = settings.search_index_epg_window_hours
    original_search_timeout = settings.search_request_timeout_seconds
    original_recommendation_window = settings.recommendation_default_window_hours
    original_viewing_planner_candidate_limit = settings.viewing_planner_candidate_limit
    original_viewing_planner_max_items = settings.viewing_planner_max_items
    settings.live_tv_auto_sync = False
    settings.youtube_api_key = "test-youtube-key"
    settings.live_tv_request_timeout_seconds = 1
    settings.catalog_auto_sync = False
    settings.tmdb_api_key = "test-tmdb-api-key"
    settings.tmdb_access_token = "test-tmdb-access-token"
    settings.catalog_request_timeout_seconds = 1
    settings.catalog_sync_target_items = 12
    settings.gemini_api_key = "test-gemini-key"
    settings.gemini_embedding_model = "gemini-embedding-2"
    settings.gemini_embedding_dimensions = 8
    settings.gemini_viewing_planner_model = "gemini-3.6-flash"
    settings.search_index_auto_sync = False
    settings.search_index_epg_window_hours = 24
    settings.search_request_timeout_seconds = 1
    settings.recommendation_default_window_hours = 12
    settings.viewing_planner_candidate_limit = 12
    settings.viewing_planner_max_items = 5
    try:
        yield settings
    finally:
        settings.live_tv_auto_sync = original_auto_sync
        settings.youtube_api_key = original_youtube_api_key
        settings.live_tv_request_timeout_seconds = original_timeout
        settings.catalog_auto_sync = original_catalog_auto_sync
        settings.tmdb_api_key = original_tmdb_api_key
        settings.tmdb_access_token = original_tmdb_access_token
        settings.catalog_request_timeout_seconds = original_catalog_timeout
        settings.catalog_sync_target_items = original_catalog_target
        settings.gemini_api_key = original_gemini_api_key
        settings.gemini_embedding_model = original_gemini_embedding_model
        settings.gemini_embedding_dimensions = original_gemini_dimensions
        settings.gemini_viewing_planner_model = original_gemini_viewing_planner_model
        settings.search_index_auto_sync = original_search_auto_sync
        settings.search_index_epg_window_hours = original_search_epg_window
        settings.search_request_timeout_seconds = original_search_timeout
        settings.recommendation_default_window_hours = original_recommendation_window
        settings.viewing_planner_candidate_limit = original_viewing_planner_candidate_limit
        settings.viewing_planner_max_items = original_viewing_planner_max_items


@pytest.fixture()
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
