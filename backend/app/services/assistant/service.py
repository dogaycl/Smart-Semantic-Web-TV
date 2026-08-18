from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantContextRead,
    AssistantLLMResponse,
    AssistantSourceRead,
)
from app.services.assistant.retrieval import RetrievedChunk, RetrievedContext, RetrievalService
from app.services.llm.base import LLMService
from app.services.llm.gemini import GeminiLLMService
from app.services.recommendations.service import RecommendationService
from app.services.search.embeddings.base import EmbeddingService
from app.services.search.embeddings.gemini import GeminiEmbeddingService
from app.services.search.index_service import SearchIndexService

logger = logging.getLogger(__name__)


class AssistantService:
    def __init__(
        self,
        *,
        retrieval_service: RetrievalService | None = None,
        llm_service: LLMService | None = None,
        embedding_service: EmbeddingService | None = None,
        recommendation_service: RecommendationService | None = None,
        index_service: SearchIndexService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.embedding_service = embedding_service or GeminiEmbeddingService()
        self.index_service = index_service or SearchIndexService(embedding_service=self.embedding_service)
        self.retrieval_service = retrieval_service or RetrievalService(
            embedding_service=self.embedding_service,
            index_service=self.index_service,
        )
        self.llm_service = llm_service or GeminiLLMService()
        self.recommendation_service = recommendation_service or RecommendationService(
            embedding_service=self.embedding_service,
            index_service=self.index_service,
        )

    def chat(
        self,
        *,
        db: Session,
        user: User,
        payload: AssistantChatRequest,
    ) -> AssistantChatResponse:
        context = self.retrieval_service.retrieve(db=db, payload=payload)
        profile = self.recommendation_service.build_profile(db=db, user=user)

        llm_response: AssistantLLMResponse | None = None
        generation_source = "fallback"
        model_name: str | None = None

        if self.llm_service.is_configured():
            prompt = self._build_prompt(payload=payload, context=context, profile_summary=profile.summary)
            try:
                llm_response = self.llm_service.generate_assistant_reply(prompt=prompt)
                generation_source = "gemini"
                model_name = self.settings.gemini_assistant_model
            except Exception as exc:
                logger.warning(
                    "Gemini assistant reply generation failed for user %s, using deterministic fallback: %s",
                    user.id,
                    exc,
                    exc_info=True,
                )
                llm_response = None

        if llm_response is None:
            llm_response = self._build_fallback_response(payload=payload, context=context, profile_summary=profile.summary)

        used_sources = self._select_sources(chunks=context.chunks, cited_chunk_ids=llm_response.cited_chunk_ids)
        limitation_note = llm_response.limitation_note or self._default_limitation_note(
            context=context,
            user_message=payload.message,
        )

        return AssistantChatResponse(
            answer=llm_response.answer,
            limitation_note=limitation_note,
            grounded=bool(used_sources),
            used_rag=bool(context.chunks),
            generation_source=generation_source,
            model=model_name,
            context=self._serialize_context(context),
            sources=[self._serialize_source(item) for item in used_sources],
            follow_up_questions=llm_response.follow_up_questions,
        )

    def _build_prompt(
        self,
        *,
        payload: AssistantChatRequest,
        context: RetrievedContext,
        profile_summary: list[str],
    ) -> str:
        context_payload = {
            "context_type": context.context_type,
            "title": context.title,
            "description": context.description,
            "category_label": context.category_label,
            "content_slug": context.content_slug,
            "channel_id": context.channel_id,
            "epg_entry_id": context.epg_entry_id,
            "channel_name": context.channel_name,
            "live_status": context.live_status,
            "current_program_title": context.current_program_title,
            "next_program_title": context.next_program_title,
            "has_transcript": context.has_transcript,
            "metadata_only": context.metadata_only,
        }
        chunk_payload = [
            {
                "chunk_id": chunk.chunk_id,
                "source_type": chunk.source_type,
                "title": chunk.title,
                "text": chunk.text,
            }
            for chunk in context.chunks
        ]

        return (
            "You are the Smart Semantic Web TV content assistant.\n"
            "Return JSON only.\n"
            "You are answering about the single currently viewed content context below.\n"
            "Use ONLY the trusted retrieved chunks.\n"
            "Do not invent scenes, dialogue, speakers, transcript details, program events, or live broadcast moments.\n"
            "If transcript context is unavailable, never pretend to know who is speaking or what is happening right now.\n"
            "If the available context is limited, explain that in limitation_note.\n"
            "Cite only chunk_id values that exist in the retrieved chunk list.\n"
            "Keep follow_up_questions short and relevant to the same content.\n"
            f"User profile summary: {json.dumps(profile_summary, ensure_ascii=True)}\n"
            f"Resolved content context: {json.dumps(context_payload, ensure_ascii=True)}\n"
            f"Retrieved trusted chunks: {json.dumps(chunk_payload, ensure_ascii=True)}\n"
            f"User message: {payload.message}"
        )

    def _build_fallback_response(
        self,
        *,
        payload: AssistantChatRequest,
        context: RetrievedContext,
        profile_summary: list[str],
    ) -> AssistantLLMResponse:
        top_chunk = context.chunks[0] if context.chunks else None
        answer_parts = []

        if context.context_type == "catalog":
            if context.description:
                answer_parts.append(f"{context.title} is described as: {context.description}")
            if context.category_label:
                answer_parts.append(f"It is classified under {context.category_label}.")
            if top_chunk and top_chunk.source_type == "credits_metadata":
                answer_parts.append(top_chunk.text)
        elif context.context_type == "program":
            answer_parts.append(
                f"{context.title} is the current program context on {context.channel_name or 'the selected channel'}."
            )
            if context.description:
                answer_parts.append(context.description)
            if context.next_program_title:
                answer_parts.append(f"Next up on the channel: {context.next_program_title}.")
        else:
            answer_parts.append(f"You are viewing {context.title}.")
            if context.current_program_title:
                answer_parts.append(f"The current scheduled program is {context.current_program_title}.")
            if context.next_program_title:
                answer_parts.append(f"The next scheduled program is {context.next_program_title}.")
            if context.description:
                answer_parts.append(context.description)

        if profile_summary and "fit" in payload.message.lower():
            answer_parts.append(f"Your saved profile signals include: {'; '.join(profile_summary[:2])}.")

        answer = " ".join(part for part in answer_parts if part).strip() or (
            f"I could only confirm trusted metadata for {context.title}."
        )
        limitation_note = self._default_limitation_note(context=context, user_message=payload.message)
        return AssistantLLMResponse(
            answer=answer,
            limitation_note=limitation_note,
            cited_chunk_ids=[chunk.chunk_id for chunk in context.chunks[:3]],
            follow_up_questions=self._default_follow_ups(context=context),
        )

    def _default_follow_ups(self, *, context: RetrievedContext) -> list[str]:
        if context.context_type == "catalog":
            return [
                "What genres define this title?",
                "Who are the main cast and crew?",
            ]
        if context.context_type == "program":
            return [
                "What is this program about?",
                "What is on next on this channel?",
            ]
        return [
            "What is on this channel right now?",
            "What is the next scheduled program?",
        ]

    def _default_limitation_note(
        self,
        *,
        context: RetrievedContext,
        user_message: str,
    ) -> str | None:
        scene_level_request = any(
            phrase in user_message.lower()
            for phrase in [
                "right now",
                "currently",
                "who is speaking",
                "what is happening",
                "what just happened",
                "dialogue",
                "quote",
                "scene",
            ]
        )
        if context.context_type in {"channel", "program"}:
            return (
                "No trusted transcript or moment-by-moment live feed context is available right now, "
                "so this answer is limited to guide and channel metadata."
            )
        if scene_level_request and not context.has_transcript:
            return (
                "Only trusted catalog metadata is available for this title right now, "
                "so scene-level details or dialogue cannot be confirmed."
            )
        return None

    def _select_sources(
        self,
        *,
        chunks: list[RetrievedChunk],
        cited_chunk_ids: list[str],
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []
        if cited_chunk_ids:
            chunk_map = {chunk.chunk_id: chunk for chunk in chunks}
            selected = [chunk_map[chunk_id] for chunk_id in cited_chunk_ids if chunk_id in chunk_map]
            if selected:
                return selected[:4]
        return chunks[:4]

    def _serialize_context(self, context: RetrievedContext) -> AssistantContextRead:
        return AssistantContextRead(
            context_type=context.context_type,
            title=context.title,
            description=context.description,
            category_label=context.category_label,
            content_slug=context.content_slug,
            channel_id=context.channel_id,
            epg_entry_id=context.epg_entry_id,
            channel_name=context.channel_name,
            live_status=context.live_status,
            current_program_title=context.current_program_title,
            next_program_title=context.next_program_title,
            has_transcript=context.has_transcript,
            metadata_only=context.metadata_only,
        )

    def _serialize_source(self, chunk: RetrievedChunk) -> AssistantSourceRead:
        return AssistantSourceRead(
            chunk_id=chunk.chunk_id,
            source_type=chunk.source_type,
            title=chunk.title,
            snippet=self._snippet(chunk.text),
        )

    def _snippet(self, text: str, limit: int = 240) -> str:
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3].rstrip() + "..."
