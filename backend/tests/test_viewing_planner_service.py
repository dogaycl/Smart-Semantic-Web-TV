from datetime import date, datetime, time, timedelta, timezone

from app.models.catalog_genre import CatalogGenre
from app.models.catalog_item import CatalogItem
from app.models.channel import Channel
from app.models.epg_entry import EPGEntry
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.planner import ViewingPlanGenerateRequest, ViewingPlannerLLMItem, ViewingPlannerLLMResponse
from app.services.planner.service import ViewingPlannerService
from app.services.recommendations.service import RecommendationService
from app.services.search.index_service import SearchIndexService
from tests.test_discovery_services import FakeEmbeddingService


class FakeLLMService:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.prompts: list[str] = []

    def is_configured(self) -> bool:
        return True

    def generate_viewing_plan(self, *, prompt: str) -> ViewingPlannerLLMResponse:
        self.prompts.append(prompt)
        if not self.responses:
            raise RuntimeError("No fake LLM response was queued.")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _create_user(db_session, *, username: str, email: str, interests: list[str], preferred_categories: list[str]) -> User:
    user = User(
        username=username,
        email=email,
        hashed_password="not-used",
        role="user",
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(
        UserProfile(
            user_id=user.id,
            display_name=username.title(),
            interests=interests,
            preferred_categories=preferred_categories,
        )
    )
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_catalog_item(
    db_session,
    *,
    slug: str,
    title: str,
    overview: str,
    runtime_minutes: int,
    genres: list[str],
    popularity: float = 120.0,
    content_type: str = "movie",
):
    item = CatalogItem(
        slug=slug,
        content_type=content_type,
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


def _create_live_program(
    db_session,
    *,
    slug: str,
    title: str,
    description: str,
    category: str,
    start_time: datetime,
    duration_minutes: int = 60,
):
    channel = Channel(
        slug=slug,
        name=slug.replace("-", " ").title(),
        description="Live channel for planner tests",
        category=category,
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
        external_id=f"{slug}-{start_time.isoformat()}",
        title=title,
        description=description,
        category=category,
        start_time=start_time,
        end_time=start_time + timedelta(minutes=duration_minutes),
        source="xmltv",
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(channel)
    db_session.refresh(entry)
    return channel, entry


def _build_service(fake_llm):
    embedding_service = FakeEmbeddingService()
    index_service = SearchIndexService(embedding_service=embedding_service)
    recommendation_service = RecommendationService(embedding_service=embedding_service, index_service=index_service)
    planner_service = ViewingPlannerService(
        llm_service=fake_llm,
        embedding_service=embedding_service,
        recommendation_service=recommendation_service,
        index_service=index_service,
    )
    return planner_service, index_service, recommendation_service


def _default_payload(**overrides) -> ViewingPlanGenerateRequest:
    payload = {
        "plan_date": date(2026, 8, 15),
        "available_start": time(19, 0),
        "available_end": time(23, 0),
        "timezone": "UTC",
        "max_duration_minutes": 180,
        "preferred_categories": ["Documentary"],
        "include_live": True,
        "include_vod": True,
        "preference_text": "technology science",
    }
    payload.update(overrides)
    return ViewingPlanGenerateRequest(**payload)


def test_planner_candidate_selection_excludes_unavailable_and_too_long_content(db_session):
    service, index_service, recommendation_service = _build_service(FakeLLMService())
    user = _create_user(
        db_session,
        username="planner-one",
        email="planner-one@example.com",
        interests=["Technology"],
        preferred_categories=["Documentary"],
    )
    payload = _default_payload()

    short_movie = _create_catalog_item(
        db_session,
        slug="tech-frontiers",
        title="Tech Frontiers",
        overview="A documentary about science and future technology.",
        runtime_minutes=110,
        genres=["Documentary", "Technology"],
    )
    _create_catalog_item(
        db_session,
        slug="epic-marathon",
        title="Epic Marathon",
        overview="A very long science documentary.",
        runtime_minutes=220,
        genres=["Documentary"],
    )
    _, in_window_program = _create_live_program(
        db_session,
        slug="science-live",
        title="Science Tonight",
        description="Live science bulletin.",
        category="Documentary",
        start_time=datetime(2026, 8, 15, 19, 0, tzinfo=timezone.utc),
    )
    _create_live_program(
        db_session,
        slug="late-night-live",
        title="Late Night Special",
        description="Starts after the requested window.",
        category="Documentary",
        start_time=datetime(2026, 8, 15, 23, 10, tzinfo=timezone.utc),
    )

    index_service.sync_documents(db=db_session)
    window = service._build_window(payload=payload, user=user)
    documents = service.search_repository.list_active(db=db_session)
    profile, scored = recommendation_service.score_documents(
        db=db_session,
        user=user,
        documents=documents,
        now=window.window_start,
        window_end=window.window_end,
    )
    candidates = service._select_candidates(
        payload=payload,
        window=window,
        profile=profile,
        documents=documents,
        scored_documents=scored,
    )

    candidate_ids = {item.candidate_id for item in candidates}
    assert f"catalog:{short_movie.slug}" in candidate_ids
    assert f"epg:{in_window_program.channel_id}:{in_window_program.source}:{in_window_program.external_id}" in candidate_ids
    assert "catalog:epic-marathon" not in candidate_ids
    assert not any("late-night-live" in candidate_id for candidate_id in candidate_ids)


def test_planner_repairs_invalid_llm_schedule_once_then_accepts_valid_result(db_session):
    invalid_response = ViewingPlannerLLMResponse(
        summary="First draft",
        plan=[
            ViewingPlannerLLMItem(
                candidate_id="epg:1:xmltv:science-live-2026-08-15T19:00:00+00:00",
                planned_start=datetime(2026, 8, 15, 19, 0, tzinfo=timezone.utc),
                planned_end=datetime(2026, 8, 15, 19, 40, tzinfo=timezone.utc),
                reason="Wrong live range",
            ),
            ViewingPlannerLLMItem(
                candidate_id="catalog:tech-frontiers",
                planned_start=datetime(2026, 8, 15, 19, 30, tzinfo=timezone.utc),
                planned_end=datetime(2026, 8, 15, 21, 0, tzinfo=timezone.utc),
                reason="Overlaps and uses the wrong duration",
            ),
        ],
    )
    valid_response = ViewingPlannerLLMResponse(
        summary="Technology evening plan",
        plan=[
            ViewingPlannerLLMItem(
                candidate_id="epg:1:xmltv:science-live-2026-08-15T19:00:00+00:00",
                planned_start=datetime(2026, 8, 15, 19, 0, tzinfo=timezone.utc),
                planned_end=datetime(2026, 8, 15, 20, 0, tzinfo=timezone.utc),
                reason="Start with the live science bulletin.",
            ),
            ViewingPlannerLLMItem(
                candidate_id="catalog:tech-frontiers",
                planned_start=datetime(2026, 8, 15, 20, 0, tzinfo=timezone.utc),
                planned_end=datetime(2026, 8, 15, 22, 0, tzinfo=timezone.utc),
                reason="Then continue with a full-length technology documentary.",
            ),
        ],
    )
    service, index_service, _ = _build_service(FakeLLMService(invalid_response, valid_response))
    user = _create_user(
        db_session,
        username="planner-two",
        email="planner-two@example.com",
        interests=["Science"],
        preferred_categories=["Documentary"],
    )
    _create_catalog_item(
        db_session,
        slug="tech-frontiers",
        title="Tech Frontiers",
        overview="A documentary about science and future technology.",
        runtime_minutes=120,
        genres=["Documentary", "Technology"],
    )
    _create_live_program(
        db_session,
        slug="science-live",
        title="Science Tonight",
        description="Live science bulletin.",
        category="Documentary",
        start_time=datetime(2026, 8, 15, 19, 0, tzinfo=timezone.utc),
    )
    index_service.sync_documents(db=db_session)

    result = service.generate_plan(db=db_session, user=user, payload=_default_payload())

    assert result.generation_source == "gemini"
    assert result.llm_repair_applied is True
    assert [item.title for item in result.items] == ["Science Tonight", "Tech Frontiers"]
    assert result.items[0].planned_start == datetime(2026, 8, 15, 19, 0, tzinfo=timezone.utc)
    assert result.items[1].planned_end == datetime(2026, 8, 15, 22, 0, tzinfo=timezone.utc)


def test_planner_rejects_invalid_gemini_ids_and_uses_fallback(db_session):
    invalid_one = ViewingPlannerLLMResponse(
        summary="Invalid plan",
        plan=[
            ViewingPlannerLLMItem(
                candidate_id="catalog:not-real",
                planned_start=datetime(2026, 8, 15, 19, 0, tzinfo=timezone.utc),
                planned_end=datetime(2026, 8, 15, 20, 0, tzinfo=timezone.utc),
                reason="Not real.",
            )
        ],
    )
    invalid_two = ViewingPlannerLLMResponse(
        summary="Still invalid",
        plan=[
            ViewingPlannerLLMItem(
                candidate_id="catalog:not-real-again",
                planned_start=datetime(2026, 8, 15, 20, 0, tzinfo=timezone.utc),
                planned_end=datetime(2026, 8, 15, 21, 0, tzinfo=timezone.utc),
                reason="Still not real.",
            )
        ],
    )
    service, index_service, _ = _build_service(FakeLLMService(invalid_one, invalid_two))
    user = _create_user(
        db_session,
        username="planner-three",
        email="planner-three@example.com",
        interests=["Technology"],
        preferred_categories=["Documentary"],
    )
    _create_catalog_item(
        db_session,
        slug="tech-frontiers",
        title="Tech Frontiers",
        overview="A documentary about science and future technology.",
        runtime_minutes=95,
        genres=["Documentary", "Technology"],
    )
    index_service.sync_documents(db=db_session)

    result = service.generate_plan(
        db=db_session,
        user=user,
        payload=_default_payload(include_live=False, max_duration_minutes=120),
    )

    assert result.generation_source == "fallback"
    assert result.items
    assert all(item.candidate_id.startswith("catalog:") or item.candidate_id.startswith("epg:") for item in result.items)


def test_planner_uses_fallback_when_gemini_call_fails(db_session):
    service, index_service, _ = _build_service(FakeLLMService(RuntimeError("Gemini offline")))
    user = _create_user(
        db_session,
        username="planner-four",
        email="planner-four@example.com",
        interests=["Technology"],
        preferred_categories=["Documentary"],
    )
    _create_catalog_item(
        db_session,
        slug="tech-frontiers",
        title="Tech Frontiers",
        overview="A documentary about science and future technology.",
        runtime_minutes=100,
        genres=["Documentary", "Technology"],
    )
    index_service.sync_documents(db=db_session)

    result = service.generate_plan(
        db=db_session,
        user=user,
        payload=_default_payload(include_live=False, max_duration_minutes=120),
    )

    assert result.generation_source == "fallback"
    assert result.summary
    assert result.items


def test_planner_user_preferences_influence_fallback_selection(db_session):
    service, index_service, _ = _build_service(FakeLLMService(RuntimeError("Force fallback")))
    user = _create_user(
        db_session,
        username="planner-five",
        email="planner-five@example.com",
        interests=["Technology", "Science"],
        preferred_categories=["Documentary"],
    )
    _create_catalog_item(
        db_session,
        slug="tech-frontiers",
        title="Tech Frontiers",
        overview="A documentary about artificial intelligence and future science.",
        runtime_minutes=100,
        genres=["Documentary", "Technology"],
        popularity=140,
    )
    _create_catalog_item(
        db_session,
        slug="romance-weekend",
        title="Romance Weekend",
        overview="A romance story by the sea.",
        runtime_minutes=100,
        genres=["Romance"],
        popularity=200,
    )
    index_service.sync_documents(db=db_session)

    result = service.generate_plan(
        db=db_session,
        user=user,
        payload=_default_payload(include_live=False, max_duration_minutes=120),
    )

    assert result.generation_source == "fallback"
    assert result.items
    assert result.items[0].title == "Tech Frontiers"
