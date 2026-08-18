from app.api.routers import assistant as assistant_router
from app.schemas.assistant import AssistantLLMResponse
from app.services.assistant.retrieval import RetrievalService
from app.services.assistant.service import AssistantService
from app.services.recommendations.service import RecommendationService
from app.services.search.index_service import SearchIndexService
from tests.test_assistant_service import FakeAssistantLLMService
from tests.test_discovery_services import FakeEmbeddingService
from tests.test_viewing_planner_service import _create_catalog_item


def _register_user(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "assistant-api-user",
            "email": "assistant-api@example.com",
            "password": "StrongPass123!",
            "display_name": "Assistant API User",
            "interests": ["Science"],
            "preferred_categories": ["Documentary"],
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_assistant_chat_endpoint_returns_grounded_response(client, db_session, monkeypatch):
    _create_catalog_item(
        db_session,
        slug="journey-to-space",
        title="Journey to Space",
        overview="A science documentary about space exploration and future missions.",
        runtime_minutes=95,
        genres=["Documentary", "Science Fiction"],
    )
    token = _register_user(client)

    embedding_service = FakeEmbeddingService()
    index_service = SearchIndexService(embedding_service=embedding_service)
    retrieval_service = RetrievalService(
        embedding_service=embedding_service,
        index_service=index_service,
    )
    recommendation_service = RecommendationService(
        embedding_service=embedding_service,
        index_service=index_service,
    )
    custom_service = AssistantService(
        retrieval_service=retrieval_service,
        llm_service=FakeAssistantLLMService(
            AssistantLLMResponse(
                answer="Journey to Space is a documentary about space exploration.",
                limitation_note=None,
                cited_chunk_ids=["catalog-overview:journey-to-space"],
                follow_up_questions=["Who are the main contributors?"],
            )
        ),
        embedding_service=embedding_service,
        recommendation_service=recommendation_service,
        index_service=index_service,
    )
    custom_service.index_service.sync_documents(db=db_session)
    monkeypatch.setattr(assistant_router, "assistant_service", custom_service)

    response = client.post(
        "/api/assistant/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "What is this about?",
            "context_type": "catalog",
            "content_slug": "journey-to-space",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["generation_source"] == "gemini"
    assert payload["context"]["context_type"] == "catalog"
    assert payload["context"]["content_slug"] == "journey-to-space"
    assert payload["sources"]
    assert payload["sources"][0]["chunk_id"] == "catalog-overview:journey-to-space"
