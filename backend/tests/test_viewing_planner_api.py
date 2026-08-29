from datetime import date, datetime, time, timedelta, timezone

from app.api.routers import viewing_plans as viewing_plans_router
from app.schemas.planner import ViewingPlannerLLMItem, ViewingPlannerLLMResponse
from app.services.planner.service import ViewingPlannerService
from tests.test_viewing_planner_service import (
    FakeEmbeddingService,
    FakeLLMService,
    _create_catalog_item,
    _create_live_program,
    _create_user,
)
from app.services.recommendations.service import RecommendationService
from app.services.search.index_service import SearchIndexService

TODAY = date.today()


def _register_user(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "planner-api-user",
            "email": "planner-api@example.com",
            "password": "StrongPass123!",
            "display_name": "Planner API User",
            "interests": ["Technology"],
            "preferred_categories": ["Documentary"],
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_generate_viewing_plan_endpoint_persists_and_lists_plans(client, db_session, monkeypatch):
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
            summary="API planner result",
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
        "preference_text": "technology science",
    }
    response = client.post(
        "/api/viewing-plans/generate",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 201
    generated = response.json()
    assert generated["generation_source"] == "gemini"
    assert len(generated["items"]) == 2

    list_response = client.get(
        "/api/viewing-plans",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["items"]
    assert list_payload["items"][0]["id"] == generated["id"]

    detail_response = client.get(
        f"/api/viewing-plans/{generated['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["summary"] == "API planner result"
    assert detail_payload["items"][0]["candidate_id"].startswith("epg:")


def test_generate_viewing_plan_returns_clean_400_for_past_plan_date(client, db_session):
    # Regression test: ViewingPlanGenerateRequest.validate_request() raises a plain
    # ValueError for a past plan_date. Pydantic's RequestValidationError.errors() embeds
    # that raw exception in each error's ctx, which the default JSONResponse encoder
    # cannot serialize - this used to crash the request with a 500 instead of a 400.
    token = _register_user(client)
    payload = {
        "plan_date": str(TODAY - timedelta(days=1)),
        "available_start": str(time(19, 0)),
        "available_end": str(time(23, 0)),
        "timezone": "UTC",
        "preferred_categories": ["Documentary"],
        "include_live": True,
        "include_vod": True,
    }

    response = client.post(
        "/api/viewing-plans/generate",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Validation error."
    assert "plan_date cannot be in the past" in data["errors"][0]["msg"]
