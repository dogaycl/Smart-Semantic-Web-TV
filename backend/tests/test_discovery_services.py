from datetime import date, datetime, timedelta, timezone

from app.models.catalog_genre import CatalogGenre
from app.models.catalog_item import CatalogItem
from app.models.channel import Channel
from app.models.epg_entry import EPGEntry
from app.models.favorite import Favorite
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.watch_history import WatchHistory
from app.core.config import get_settings
from app.services.recommendations.service import RecommendationService
from app.services.search.index_service import SearchIndexService
from app.services.search.service import SemanticSearchService


class FakeEmbeddingService:
    def is_configured(self) -> bool:
        return True

    def embed_query(self, query: str) -> list[float]:
        return self._vectorize(query)

    def embed_document(self, *, title: str | None, text: str) -> list[float]:
        return self._vectorize(f"{title or ''} {text}")

    def _vectorize(self, value: str) -> list[float]:
        normalized = value.lower()
        vector = [0.0] * 8
        keyword_map = {
            "science": [1, 0, 0, 0, 0, 0, 0, 0],
            "documentary": [0, 1, 0, 0, 0, 0, 0, 0],
            "space": [1, 1, 0, 0, 0, 0, 0, 0],
            "technology": [0, 0, 1, 0, 0, 0, 0, 0],
            "ai": [0, 0, 1, 1, 0, 0, 0, 0],
            "artificial intelligence": [0, 0, 1, 1, 0, 0, 0, 0],
            "comedy": [0, 0, 0, 0, 1, 0, 0, 0],
            "funny": [0, 0, 0, 0, 1, 0, 0, 0],
            "live": [0, 0, 0, 0, 0, 1, 0, 0],
            "drama": [0, 0, 0, 0, 0, 0, 1, 0],
            "action": [0, 0, 0, 0, 0, 0, 0, 1],
        }
        for keyword, weights in keyword_map.items():
            if keyword in normalized:
                vector = [current + float(weight) for current, weight in zip(vector, weights, strict=True)]
        if sum(vector) == 0:
            vector[0] = 0.1
        return vector


class CountingEmbeddingService(FakeEmbeddingService):
    def __init__(self) -> None:
        self.document_calls = 0

    def embed_document(self, *, title: str | None, text: str) -> list[float]:
        self.document_calls += 1
        return super().embed_document(title=title, text=text)


def _create_catalog_item(db_session, *, slug: str, title: str, overview: str, runtime_minutes: int, genres: list[str], popularity: float = 100.0):
    item = CatalogItem(
        slug=slug,
        content_type="movie",
        tmdb_id=abs(hash(slug)) % 1000000,
        title=title,
        original_title=title,
        overview=overview,
        release_date=date(2024, 1, 1),
        runtime_minutes=runtime_minutes,
        poster_url="https://example.com/poster.jpg",
        backdrop_url="https://example.com/backdrop.jpg",
        vote_average=8.0,
        popularity=popularity,
        original_language="en",
        status="Released",
        top_cast=["Lead Actor"],
        top_crew=["Director"],
        tmdb_url=f"https://www.themoviedb.org/movie/{abs(hash(slug)) % 1000000}",
        is_active=True,
        last_synced_at=datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc),
    )
    db_session.add(item)
    db_session.flush()
    for index, genre in enumerate(genres, start=1):
        db_session.add(CatalogGenre(content_item_id=item.id, tmdb_genre_id=index, name=genre))
    db_session.commit()
    db_session.refresh(item)
    return item


def _create_channel_and_program(db_session, *, title: str, description: str, category: str, starts_in_hours: int = 1):
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

    start_time = datetime.now(timezone.utc) + timedelta(hours=starts_in_hours)
    entry = EPGEntry(
        channel_id=channel.id,
        external_id=f"program-{starts_in_hours}",
        title=title,
        description=description,
        category=category,
        start_time=start_time,
        end_time=start_time + timedelta(minutes=90),
        source="xmltv",
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(channel)
    db_session.refresh(entry)
    return channel, entry


def _create_user(db_session, *, interests: list[str], preferred_categories: list[str]) -> User:
    user = User(
        username="semantic-user",
        email="semantic@example.com",
        hashed_password="not-used-in-tests",
        role="user",
    )
    db_session.add(user)
    db_session.flush()
    profile = UserProfile(
        user_id=user.id,
        display_name="Semantic User",
        interests=interests,
        preferred_categories=preferred_categories,
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_semantic_search_prioritizes_live_tonight_space_documentary(db_session):
    embedding_service = FakeEmbeddingService()
    index_service = SearchIndexService(embedding_service=embedding_service)
    search_service = SemanticSearchService(embedding_service=embedding_service, index_service=index_service)

    _create_catalog_item(
        db_session,
        slug="movie-journey-to-space-1",
        title="Journey to Space",
        overview="A science documentary about space exploration and the cosmos.",
        runtime_minutes=95,
        genres=["Documentary", "Science Fiction"],
        popularity=120,
    )
    _create_channel_and_program(
        db_session,
        title="Space Lab: AI on Mars",
        description="A science documentary about space missions and artificial intelligence.",
        category="Documentary",
        starts_in_hours=1,
    )
    user = _create_user(db_session, interests=["Artificial Intelligence"], preferred_categories=["Documentary"])

    index_service.sync_documents(db=db_session)
    response = search_service.search(
        db=db_session,
        user=user,
        query="Find a science documentary about space tonight.",
        limit=5,
        window_hours=6,
    )

    assert response.results
    assert response.results[0].result_type == "live_program"
    assert response.results[0].title == "Space Lab: AI on Mars"
    assert "Upcoming" in response.results[0].explanation or "Strong semantic match" in response.results[0].explanation or "Upcoming on" in response.results[0].explanation


def test_semantic_search_respects_runtime_filter(db_session):
    embedding_service = FakeEmbeddingService()
    index_service = SearchIndexService(embedding_service=embedding_service)
    search_service = SemanticSearchService(embedding_service=embedding_service, index_service=index_service)

    _create_catalog_item(
        db_session,
        slug="movie-fast-laughs-2",
        title="Fast Laughs",
        overview="A funny comedy for friends.",
        runtime_minutes=98,
        genres=["Comedy"],
        popularity=90,
    )
    _create_catalog_item(
        db_session,
        slug="movie-epic-comedy-3",
        title="Epic Comedy",
        overview="A funny but very long comedy adventure.",
        runtime_minutes=145,
        genres=["Comedy", "Action"],
        popularity=200,
    )

    index_service.sync_documents(db=db_session)
    response = search_service.search(
        db=db_session,
        user=None,
        query="I want something funny that takes less than two hours.",
        limit=5,
    )

    assert response.results
    assert response.results[0].title == "Fast Laughs"
    assert all((item.runtime_minutes or 0) <= 120 for item in response.results)


def test_recommendations_include_live_preference_explanation(db_session):
    embedding_service = FakeEmbeddingService()
    index_service = SearchIndexService(embedding_service=embedding_service)
    recommendation_service = RecommendationService(embedding_service=embedding_service, index_service=index_service)

    favorite_item = _create_catalog_item(
        db_session,
        slug="movie-journey-to-space-1",
        title="Journey to Space",
        overview="A science documentary about deep space.",
        runtime_minutes=95,
        genres=["Documentary", "Science Fiction"],
        popularity=100,
    )
    _create_catalog_item(
        db_session,
        slug="movie-deep-space-machines-4",
        title="Deep Space Machines",
        overview="A technology documentary about AI systems for space travel.",
        runtime_minutes=104,
        genres=["Documentary", "Science Fiction"],
        popularity=180,
    )
    _create_channel_and_program(
        db_session,
        title="AI Tonight",
        description="Live technology documentary coverage about robotics and space.",
        category="Documentary",
        starts_in_hours=1,
    )
    user = _create_user(db_session, interests=["Technology"], preferred_categories=["Documentary"])
    db_session.add(Favorite(user_id=user.id, content_id=favorite_item.slug))
    db_session.add(
        WatchHistory(
            user_id=user.id,
            content_id=favorite_item.slug,
            content_type="content",
            watch_position_seconds=3600,
            total_watched_duration_seconds=5400,
            is_completed=True,
            last_watched_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    index_service.sync_documents(db=db_session)
    response = recommendation_service.recommend(
        db=db_session,
        user=user,
        limit=5,
        window_hours=6,
    )

    assert response.results
    assert response.results[0].title == "AI Tonight"
    assert "Live tonight" in response.results[0].explanation
    assert response.profile_summary


def test_search_index_request_time_auto_sync_skips_new_embedding_calls_when_index_exists(db_session):
    embedding_service = CountingEmbeddingService()
    index_service = SearchIndexService(embedding_service=embedding_service)
    settings = get_settings()
    original_auto_sync = settings.search_index_auto_sync
    settings.search_index_auto_sync = True
    try:
        _create_catalog_item(
            db_session,
            slug="movie-journey-to-space-1",
            title="Journey to Space",
            overview="A science documentary about space exploration and the cosmos.",
            runtime_minutes=95,
            genres=["Documentary", "Science Fiction"],
            popularity=120,
        )

        index_service.sync_documents(db=db_session)
        initial_calls = embedding_service.document_calls
        assert initial_calls > 0

        _create_channel_and_program(
            db_session,
            title="AI Tonight",
            description="Live technology documentary coverage about robotics and space.",
            category="Documentary",
            starts_in_hours=1,
        )

        index_service.ensure_ready(db=db_session)

        assert embedding_service.document_calls == initial_calls
    finally:
        settings.search_index_auto_sync = original_auto_sync
