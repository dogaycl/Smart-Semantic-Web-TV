from datetime import datetime, timezone

from app.schemas.assistant import AssistantChatRequest, AssistantLLMResponse
from app.services.assistant.retrieval import RetrievalService
from app.services.assistant.service import AssistantService
from app.services.recommendations.service import RecommendationService
from app.services.search.index_service import SearchIndexService
from tests.test_discovery_services import FakeEmbeddingService
from tests.test_viewing_planner_service import _create_catalog_item, _create_live_program, _create_user


class FakeAssistantLLMService:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.prompts: list[str] = []

    def is_configured(self) -> bool:
        return True

    def generate_assistant_reply(self, *, prompt: str) -> AssistantLLMResponse:
        self.prompts.append(prompt)
        if not self.responses:
            raise RuntimeError("No fake assistant response was queued.")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _build_assistant_service(fake_llm):
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
    service = AssistantService(
        retrieval_service=retrieval_service,
        llm_service=fake_llm,
        embedding_service=embedding_service,
        recommendation_service=recommendation_service,
        index_service=index_service,
    )
    return service, index_service


def test_assistant_returns_grounded_catalog_answer_with_mocked_llm(db_session):
    service, index_service = _build_assistant_service(
        FakeAssistantLLMService(
            AssistantLLMResponse(
                answer="Journey to Space is a science documentary about space exploration and the people behind it.",
                limitation_note=None,
                cited_chunk_ids=["catalog-overview:journey-to-space", "catalog-credits:journey-to-space"],
                follow_up_questions=["Who are the main contributors?"],
            )
        )
    )
    user = _create_user(
        db_session,
        username="assistant-one",
        email="assistant-one@example.com",
        interests=["Science"],
        preferred_categories=["Documentary"],
    )
    _create_catalog_item(
        db_session,
        slug="journey-to-space",
        title="Journey to Space",
        overview="A science documentary about space exploration and future missions.",
        runtime_minutes=95,
        genres=["Documentary", "Science Fiction"],
    )
    index_service.sync_documents(db=db_session)

    result = service.chat(
        db=db_session,
        user=user,
        payload=AssistantChatRequest(
            message="What is this movie about and who made it?",
            context_type="catalog",
            content_slug="journey-to-space",
        ),
    )

    assert result.generation_source == "gemini"
    assert result.context.context_type == "catalog"
    assert result.context.title == "Journey to Space"
    assert result.grounded is True
    assert result.sources
    assert result.sources[0].chunk_id == "catalog-overview:journey-to-space"
    assert result.limitation_note is None


def test_assistant_limits_live_answers_without_transcript_context(db_session):
    service, index_service = _build_assistant_service(
        FakeAssistantLLMService(RuntimeError("Gemini unavailable"))
    )
    user = _create_user(
        db_session,
        username="assistant-two",
        email="assistant-two@example.com",
        interests=["Technology"],
        preferred_categories=["Documentary"],
    )
    channel, entry = _create_live_program(
        db_session,
        slug="science-live",
        title="Science Tonight",
        description="A live science bulletin about robotics and AI.",
        category="Documentary",
        start_time=datetime(2026, 8, 22, 19, 0, tzinfo=timezone.utc),
    )
    index_service.sync_documents(db=db_session)

    result = service.chat(
        db=db_session,
        user=user,
        payload=AssistantChatRequest(
            message="Who is speaking right now?",
            context_type="program",
            epg_entry_id=entry.id,
        ),
    )

    assert result.generation_source == "fallback"
    assert result.context.context_type == "program"
    assert result.context.channel_id == channel.id
    assert result.limitation_note is not None
    assert "guide and channel metadata" in result.limitation_note
    assert result.sources
