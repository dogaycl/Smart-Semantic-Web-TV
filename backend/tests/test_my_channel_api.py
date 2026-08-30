from datetime import date, datetime, time, timezone

from app.api.routers import viewing_plans as viewing_plans_router
from app.schemas.planner import ViewingPlannerLLMItem, ViewingPlannerLLMResponse
from app.services.planner.service import ViewingPlannerService
from app.services.recommendations.service import RecommendationService
from app.services.search.index_service import SearchIndexService
from tests.test_viewing_planner_service import (
    FakeEmbeddingService,
    FakeLLMService,
    _create_catalog_item,
    _create_live_program,
    _create_user,
)

TODAY = date.today()


def _register_user(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "my-channel-user",
            "email": "my-channel@example.com",
            "password": "StrongPass123!",
            "display_name": "My Channel User",
            "interests": ["Music"],
            "preferred_categories": ["Music"],
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_generate_my_channel_endpoint_reuses_the_existing_planner(client, db_session, monkeypatch):
    _create_catalog_item(
        db_session,
        slug="tech-frontiers",
        title="Tech Frontiers",
        overview="A documentary about science and future technology.",
        runtime_minutes=120,
        genres=["Documentary", "Technology"],
    )
    channel, entry = _create_live_program(
        db_session,
        slug="science-live",
        title="Science Tonight",
        description="Live science bulletin.",
        category="Documentary",
        start_time=datetime(TODAY.year, TODAY.month, TODAY.day, 19, 0, tzinfo=timezone.utc),
    )
    token = _register_user(client)

    embedding_service = FakeEmbeddingService()
    index_service = SearchIndexService(embedding_service=embedding_service)
    recommendation_service = RecommendationService(embedding_service=embedding_service, index_service=index_service)
    llm_service = FakeLLMService(
        ViewingPlannerLLMResponse(
            summary="My Channel tonight",
            plan=[
                ViewingPlannerLLMItem(
                    candidate_id=f"epg:{channel.id}:{entry.source}:{entry.external_id}",
                    planned_start=datetime(TODAY.year, TODAY.month, TODAY.day, 19, 0, tzinfo=timezone.utc),
                    planned_end=datetime(TODAY.year, TODAY.month, TODAY.day, 20, 0, tzinfo=timezone.utc),
                    reason="Start with the live science bulletin.",
                ),
                ViewingPlannerLLMItem(
                    candidate_id="catalog:tech-frontiers",
                    planned_start=datetime(TODAY.year, TODAY.month, TODAY.day, 20, 0, tzinfo=timezone.utc),
                    planned_end=datetime(TODAY.year, TODAY.month, TODAY.day, 22, 0, tzinfo=timezone.utc),
                    reason="Follow it with a technology documentary.",
                ),
            ],
        )
    )
    custom_service = ViewingPlannerService(
        llm_service=llm_service,
        embedding_service=embedding_service,
        recommendation_service=recommendation_service,
        index_service=index_service,
    )
    custom_service.index_service.sync_documents(db=db_session)
    # My Channel is an adapter over the same planner service used by /api/viewing-plans -
    # patching the one module attribute must be enough to control both routes.
    monkeypatch.setattr(viewing_plans_router, "viewing_planner_service", custom_service)

    payload = {
        "plan_date": str(date.today()),
        "available_start": str(time(19, 0)),
        "available_end": str(time(23, 0)),
        "timezone": "UTC",
        "max_duration_minutes": 180,
        "preferred_categories": ["Documentary"],
        "include_live": True,
        "include_vod": True,
    }
    response = client.post(
        "/api/my-channel/generate",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 201
    generated = response.json()
    assert generated["generation_source"] == "gemini"
    assert generated["summary"] == "My Channel tonight"
    assert generated["is_accepted"] is False
    assert len(generated["items"]) == 2
    assert generated["items"][0]["result_type"] == "live_program"
    assert generated["items"][0]["epg_entry_id"] == entry.id
    assert generated["items"][1]["result_type"] == "movie"

    list_response = client.get("/api/my-channel", headers={"Authorization": f"Bearer {token}"})
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == generated["id"]

    detail_response = client.get(
        f"/api/my-channel/{generated['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["summary"] == "My Channel tonight"

    # Same underlying plan storage as the existing viewing-plans API - not a parallel system.
    cross_check_response = client.get(
        f"/api/viewing-plans/{generated['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cross_check_response.status_code == 200
    assert cross_check_response.json()["summary"] == "My Channel tonight"


def test_generate_my_channel_falls_back_deterministically_when_gemini_unavailable(client, db_session, monkeypatch):
    _create_catalog_item(
        db_session,
        slug="tech-frontiers",
        title="Tech Frontiers",
        overview="A documentary about science and future technology.",
        runtime_minutes=100,
        genres=["Documentary", "Technology"],
    )
    token = _register_user(client)

    embedding_service = FakeEmbeddingService()
    index_service = SearchIndexService(embedding_service=embedding_service)
    recommendation_service = RecommendationService(embedding_service=embedding_service, index_service=index_service)
    # Simulate Gemini being unreachable (matches how test_viewing_planner_service.py
    # exercises the fallback path, instead of making a real network call in tests).
    custom_service = ViewingPlannerService(
        llm_service=FakeLLMService(RuntimeError("Gemini offline")),
        embedding_service=embedding_service,
        recommendation_service=recommendation_service,
        index_service=index_service,
    )
    custom_service.index_service.sync_documents(db=db_session)
    monkeypatch.setattr(viewing_plans_router, "viewing_planner_service", custom_service)

    payload = {
        "plan_date": str(date.today()),
        "available_start": str(time(19, 0)),
        "available_end": str(time(21, 0)),
        "timezone": "UTC",
        "max_duration_minutes": 120,
        "preferred_categories": ["Technology"],
        "include_live": False,
        "include_vod": True,
    }
    response = client.post(
        "/api/my-channel/generate",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 201
    generated = response.json()
    # Gemini failed, so this must be the deterministic fallback plan - not a crash,
    # not an empty result, and not invented content (it must be the real catalog item).
    assert generated["generation_source"] == "fallback"
    assert generated["items"]
    assert generated["items"][0]["candidate_id"] == "catalog:tech-frontiers"


def test_accept_my_channel_keeps_one_active_plan_per_date(client, db_session, monkeypatch):
    _create_catalog_item(
        db_session,
        slug="tech-frontiers",
        title="Tech Frontiers",
        overview="A documentary about science and future technology.",
        runtime_minutes=120,
        genres=["Documentary", "Technology"],
    )
    channel, entry = _create_live_program(
        db_session,
        slug="science-live",
        title="Science Tonight",
        description="Live science bulletin.",
        category="Documentary",
        start_time=datetime(TODAY.year, TODAY.month, TODAY.day, 19, 0, tzinfo=timezone.utc),
    )
    token = _register_user(client)

    embedding_service = FakeEmbeddingService()
    index_service = SearchIndexService(embedding_service=embedding_service)
    recommendation_service = RecommendationService(embedding_service=embedding_service, index_service=index_service)
    llm_service = FakeLLMService(
        ViewingPlannerLLMResponse(
            summary="Plan one",
            plan=[
                ViewingPlannerLLMItem(
                    candidate_id=f"epg:{channel.id}:{entry.source}:{entry.external_id}",
                    planned_start=datetime(TODAY.year, TODAY.month, TODAY.day, 19, 0, tzinfo=timezone.utc),
                    planned_end=datetime(TODAY.year, TODAY.month, TODAY.day, 20, 0, tzinfo=timezone.utc),
                    reason="Start live.",
                ),
                ViewingPlannerLLMItem(
                    candidate_id="catalog:tech-frontiers",
                    planned_start=datetime(TODAY.year, TODAY.month, TODAY.day, 20, 0, tzinfo=timezone.utc),
                    planned_end=datetime(TODAY.year, TODAY.month, TODAY.day, 22, 0, tzinfo=timezone.utc),
                    reason="Then watch the documentary.",
                ),
            ],
        ),
        ViewingPlannerLLMResponse(
            summary="Plan two",
            plan=[
                ViewingPlannerLLMItem(
                    candidate_id="catalog:tech-frontiers",
                    planned_start=datetime(TODAY.year, TODAY.month, TODAY.day, 19, 0, tzinfo=timezone.utc),
                    planned_end=datetime(TODAY.year, TODAY.month, TODAY.day, 21, 0, tzinfo=timezone.utc),
                    reason="Start with the documentary first.",
                ),
            ],
        ),
    )
    custom_service = ViewingPlannerService(
        llm_service=llm_service,
        embedding_service=embedding_service,
        recommendation_service=recommendation_service,
        index_service=index_service,
    )
    custom_service.index_service.sync_documents(db=db_session)
    monkeypatch.setattr(viewing_plans_router, "viewing_planner_service", custom_service)

    payload = {
        "plan_date": str(TODAY),
        "available_start": str(time(19, 0)),
        "available_end": str(time(23, 0)),
        "timezone": "UTC",
        "max_duration_minutes": 240,
        "preferred_categories": ["Documentary"],
        "include_live": True,
        "include_vod": True,
    }
    first = client.post("/api/my-channel/generate", headers={"Authorization": f"Bearer {token}"}, json=payload)
    second = client.post("/api/my-channel/generate", headers={"Authorization": f"Bearer {token}"}, json=payload)
    assert first.status_code == 201
    assert second.status_code == 201

    first_id = first.json()["id"]
    second_id = second.json()["id"]

    accept_first = client.post(f"/api/my-channel/{first_id}/accept", headers={"Authorization": f"Bearer {token}"})
    assert accept_first.status_code == 200
    assert accept_first.json()["is_accepted"] is True
    assert accept_first.json()["accepted_at"] is not None

    active_after_first = client.get(
        f"/api/my-channel/active?plan_date={TODAY}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert active_after_first.status_code == 200
    assert active_after_first.json()["id"] == first_id

    accept_second = client.post(f"/api/my-channel/{second_id}/accept", headers={"Authorization": f"Bearer {token}"})
    assert accept_second.status_code == 200
    assert accept_second.json()["id"] == second_id
    assert accept_second.json()["is_accepted"] is True

    first_detail = client.get(f"/api/my-channel/{first_id}", headers={"Authorization": f"Bearer {token}"})
    second_detail = client.get(f"/api/my-channel/{second_id}", headers={"Authorization": f"Bearer {token}"})
    assert first_detail.status_code == 200
    assert second_detail.status_code == 200
    assert first_detail.json()["is_accepted"] is False
    assert second_detail.json()["is_accepted"] is True

    active_after_second = client.get(
        f"/api/my-channel/active?plan_date={TODAY}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert active_after_second.status_code == 200
    assert active_after_second.json()["id"] == second_id


def test_active_my_channel_returns_404_when_no_plan_is_accepted(client, db_session, monkeypatch):
    _create_catalog_item(
        db_session,
        slug="tech-frontiers",
        title="Tech Frontiers",
        overview="A documentary about science and future technology.",
        runtime_minutes=100,
        genres=["Documentary", "Technology"],
    )
    token = _register_user(client)

    embedding_service = FakeEmbeddingService()
    index_service = SearchIndexService(embedding_service=embedding_service)
    recommendation_service = RecommendationService(embedding_service=embedding_service, index_service=index_service)
    custom_service = ViewingPlannerService(
        llm_service=FakeLLMService(RuntimeError("Gemini offline")),
        embedding_service=embedding_service,
        recommendation_service=recommendation_service,
        index_service=index_service,
    )
    custom_service.index_service.sync_documents(db=db_session)
    monkeypatch.setattr(viewing_plans_router, "viewing_planner_service", custom_service)

    response = client.get(
        f"/api/my-channel/active?plan_date={TODAY}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
