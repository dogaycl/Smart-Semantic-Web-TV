from datetime import date, datetime, timedelta, timezone

from app.api.routers import recommendations as recommendations_router
from app.api.routers import search as search_router
from app.models.catalog_genre import CatalogGenre
from app.models.catalog_item import CatalogItem
from app.models.channel import Channel
from app.models.epg_entry import EPGEntry
from app.services.recommendations.service import RecommendationService
from app.services.search.index_service import SearchIndexService
from app.services.search.service import SemanticSearchService
from tests.test_discovery_services import FakeEmbeddingService


def _seed_catalog_and_live_data(db_session):
    item = CatalogItem(
        slug="movie-journey-to-space-1",
        content_type="movie",
        tmdb_id=101,
        title="Journey to Space",
        original_title="Journey to Space",
        overview="A science documentary about space exploration.",
        release_date=date(2024, 1, 1),
        runtime_minutes=95,
        poster_url="https://example.com/poster.jpg",
        backdrop_url="https://example.com/backdrop.jpg",
        vote_average=8.1,
        popularity=120,
        original_language="en",
        status="Released",
        top_cast=["Lead Actor"],
        top_crew=["Director"],
        tmdb_url="https://www.themoviedb.org/movie/101",
        is_active=True,
        last_synced_at=datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc),
    )
    db_session.add(item)
    db_session.flush()
    db_session.add(CatalogGenre(content_item_id=item.id, tmdb_genre_id=1, name="Documentary"))

    channel = Channel(
        slug="science-world-tv",
        name="Science World TV",
        description="Technology and science live channel",
        category="Documentary",
        logo_url="https://example.com/channel-logo.jpg",
        language="en",
        source_type="hls",
        stream_url="https://example.com/live.m3u8",
        quality="HD",
        is_active=True,
        stream_status="healthy",
        live_status="live",
    )
    db_session.add(channel)
    db_session.flush()
    entry = EPGEntry(
        channel_id=channel.id,
        external_id="live-1",
        title="AI Tonight",
        description="Live technology documentary coverage about robotics and space.",
        category="Documentary",
        start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2, minutes=30),
        source="xmltv",
    )
    db_session.add(entry)
    db_session.commit()


def _register_user(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "discovery-user",
            "email": "discovery@example.com",
            "password": "StrongPass123!",
            "display_name": "Discovery User",
            "interests": ["Technology"],
            "preferred_categories": ["Documentary"],
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_semantic_search_endpoint_returns_ranked_results(client, db_session, monkeypatch):
    _seed_catalog_and_live_data(db_session)
    token = _register_user(client)
    embedding_service = FakeEmbeddingService()
    custom_service = SemanticSearchService(
        embedding_service=embedding_service,
        index_service=SearchIndexService(embedding_service=embedding_service),
    )
    custom_service.index_service.sync_documents(db=db_session)
    monkeypatch.setattr(search_router, "search_service", custom_service)

    response = client.post(
        "/api/search/semantic",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": "Find a science documentary about space tonight.",
            "limit": 4,
            "window_hours": 6,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["embedding_enabled"] is True
    assert payload["results"][0]["title"] == "AI Tonight"
    assert payload["results"][0]["result_type"] == "live_program"


def test_semantic_search_endpoint_allows_anonymous_queries(client, db_session, monkeypatch):
    _seed_catalog_and_live_data(db_session)
    embedding_service = FakeEmbeddingService()
    custom_service = SemanticSearchService(
        embedding_service=embedding_service,
        index_service=SearchIndexService(embedding_service=embedding_service),
    )
    custom_service.index_service.sync_documents(db=db_session)
    monkeypatch.setattr(search_router, "search_service", custom_service)

    response = client.post(
        "/api/search/semantic",
        json={
            "query": "Show me a space documentary tonight.",
            "limit": 4,
            "window_hours": 6,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    assert payload["results"][0]["result_type"] in {"live_program", "movie"}


def test_semantic_search_endpoint_ignores_invalid_optional_token(client, db_session, monkeypatch):
    _seed_catalog_and_live_data(db_session)
    embedding_service = FakeEmbeddingService()
    custom_service = SemanticSearchService(
        embedding_service=embedding_service,
        index_service=SearchIndexService(embedding_service=embedding_service),
    )
    custom_service.index_service.sync_documents(db=db_session)
    monkeypatch.setattr(search_router, "search_service", custom_service)

    response = client.post(
        "/api/search/semantic",
        headers={"Authorization": "Bearer expired-or-invalid-token"},
        json={
            "query": "Show me a space documentary tonight.",
            "limit": 4,
            "window_hours": 6,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]


def test_recommendations_endpoint_returns_explanations(client, db_session, monkeypatch):
    _seed_catalog_and_live_data(db_session)
    token = _register_user(client)
    embedding_service = FakeEmbeddingService()
    custom_service = RecommendationService(
        embedding_service=embedding_service,
        index_service=SearchIndexService(embedding_service=embedding_service),
    )
    custom_service.index_service.sync_documents(db=db_session)
    monkeypatch.setattr(recommendations_router, "recommendation_service", custom_service)

    response = client.get(
        "/api/recommendations",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 4, "window_hours": 6},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    assert payload["results"][0]["explanation"]
    assert payload["profile_summary"]
