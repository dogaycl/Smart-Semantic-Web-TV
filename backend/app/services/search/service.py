from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
import logging
import math

from sqlalchemy.orm import Session

from app.models.search_document import SearchDocument
from app.models.user import User
from app.repositories.search_document_repository import SearchDocumentRepository
from app.schemas.discovery import SemanticSearchResponse
from app.services.search.embeddings.base import EmbeddingService
from app.services.search.embeddings.gemini import GeminiEmbeddingService
from app.services.search.index_service import SearchIndexService
from app.services.search.mood import MoodProfile, resolve_mood, score_document_for_mood
from app.services.search.query_parser import QueryIntent, QueryParser, normalize_text, tokenize_text
from app.services.search.result_builder import DiscoveryResultBuilder

logger = logging.getLogger(__name__)


class SemanticSearchService:
    def __init__(
        self,
        *,
        embedding_service: EmbeddingService | None = None,
        search_repository: SearchDocumentRepository | None = None,
        index_service: SearchIndexService | None = None,
    ) -> None:
        self.embedding_service = embedding_service or GeminiEmbeddingService()
        self.search_repository = search_repository or SearchDocumentRepository()
        self.index_service = index_service or SearchIndexService(
            embedding_service=self.embedding_service,
            search_repository=self.search_repository,
        )
        self.query_parser = QueryParser()
        self.result_builder = DiscoveryResultBuilder()

    def search(
        self,
        *,
        db: Session,
        user: User | None,
        query: str,
        limit: int,
        window_hours: int | None = None,
        mood: str | None = None,
    ) -> SemanticSearchResponse:
        self.index_service.ensure_ready(db=db)
        intent = self.query_parser.parse(query, now=datetime.now(timezone.utc), window_hours=window_hours)
        mood_profile = resolve_mood(mood)
        documents = self.search_repository.list_active(db=db)
        semantic_scores = self._semantic_scores(db=db, query=intent.raw_query, limit=max(limit * 8, 40))
        profile_terms = self._user_profile_terms(user)

        ranked = []
        for document in documents:
            score, explanation = self._score_document(
                document=document,
                intent=intent,
                semantic_scores=semantic_scores,
                profile_terms=profile_terms,
                mood_profile=mood_profile,
            )
            if score <= 0:
                continue
            ranked.append((document, score, explanation))

        ranked.sort(key=lambda item: (-item[1], item[0].title.lower()))
        results = [
            self.result_builder.build(document=document, score=score, explanation=explanation)
            for document, score, explanation in ranked[:limit]
        ]

        filters = []
        if intent.max_duration_minutes is not None:
            filters.append(f"runtime <= {intent.max_duration_minutes} minutes")
        if intent.prioritize_live and intent.window_end is not None:
            filters.append("prioritize live and upcoming EPG results")
        if intent.preferred_categories:
            filters.append(f"category hints: {', '.join(intent.preferred_categories)}")
        if mood_profile is not None:
            filters.append(f"mood ranking: {mood_profile.label.lower()}")

        return SemanticSearchResponse(
            query=query,
            embedding_enabled=self.embedding_service.is_configured(),
            applied_filters=filters,
            results=results,
        )

    def _semantic_scores(self, *, db: Session, query: str, limit: int) -> dict[str, float]:
        if not self.embedding_service.is_configured():
            return {}

        try:
            query_embedding = self.embedding_service.embed_query(query)
        except Exception as exc:
            # A missing/exhausted embedding quota must not fail the whole search. Lexical,
            # category and profile signals still rank results; only the semantic boost is lost.
            logger.warning("Gemini embedding query failed, ranking search without semantic similarity: %s", exc)
            return {}

        return {
            document.source_key: score
            for document, score in self.search_repository.semantic_candidates(
                db=db,
                query_embedding=query_embedding,
                limit=limit,
            )
        }

    def _score_document(
        self,
        *,
        document: SearchDocument,
        intent: QueryIntent,
        semantic_scores: dict[str, float],
        profile_terms: list[str],
        mood_profile: MoodProfile | None = None,
    ) -> tuple[float, str]:
        if intent.max_duration_minutes is not None and document.duration_minutes is not None:
            if document.duration_minutes > intent.max_duration_minutes:
                return 0.0, ""

        if intent.prioritize_live and document.document_type == "epg":
            availability_end = self._normalize_datetime(document.availability_end)
            availability_start = self._normalize_datetime(document.availability_start)
            if intent.window_start and availability_end and availability_end <= intent.window_start:
                return 0.0, ""
            if intent.window_end and availability_start and availability_start > intent.window_end:
                return 0.0, ""

        document_text = normalize_text(document.searchable_text)
        document_tokens = set(tokenize_text(document_text))
        query_tokens = set(intent.expanded_terms)
        overlap = len(query_tokens & document_tokens)
        lexical_score = overlap / max(len(query_tokens), 1)

        category_score = 0.0
        if intent.preferred_categories:
            categories = {normalize_text(document.category_label or ""), *(normalize_text(genre) for genre in document.genres)}
            matched = sum(1 for category in intent.preferred_categories if normalize_text(category) in categories)
            category_score = matched / len(intent.preferred_categories)

        profile_score = 0.0
        if profile_terms:
            profile_overlap = len(set(profile_terms) & document_tokens)
            profile_score = min(profile_overlap / max(len(set(profile_terms)), 1), 1.0)

        live_bonus = 0.0
        if document.document_type == "epg":
            live_bonus = 0.08
            if intent.prioritize_live:
                live_bonus = 0.24
        vod_penalty = 0.0
        if intent.prioritize_live and document.document_type != "epg":
            vod_penalty = 0.08

        mood_score = 0.0
        mood_reason = ""
        if mood_profile is not None:
            mood_score, mood_reason = score_document_for_mood(
                profile=mood_profile,
                genres=document.genres or [],
                category_label=document.category_label,
                document_tokens=document_tokens,
            )

        semantic_score = max(semantic_scores.get(document.source_key, 0.0), lexical_score)
        base_weight = 0.58 if mood_profile is None else 0.44
        score = (
            (semantic_score * base_weight)
            + (lexical_score * 0.18)
            + (category_score * 0.12)
            + (profile_score * 0.07)
            + live_bonus
            - vod_penalty
        )
        if mood_profile is not None:
            # Mood affinity is a first-class ranking signal: a strong genre/keyword match lifts
            # a title, and matching an avoided genre/keyword pushes it down the list.
            score += mood_score * 0.42
        score = round(min(score, 1.0), 6)
        cutoff = 0.08 if mood_profile is None else 0.05
        if score <= cutoff:
            return 0.0, ""

        reasons = []
        if mood_reason:
            reasons.append(mood_reason)
        if intent.prioritize_live and document.document_type == "epg":
            reasons.append(f"Upcoming on {document.channel_name}.")
        if category_score > 0:
            reasons.append(f"Matches {', '.join(intent.preferred_categories[:2])} themes.")
        if intent.max_duration_minutes is not None and document.duration_minutes is not None:
            reasons.append(f"Fits the under {intent.max_duration_minutes} minute runtime.")
        if semantic_scores.get(document.source_key, 0.0) > 0.5:
            reasons.append("Strong semantic match for your query.")
        if not reasons and lexical_score > 0:
            reasons.append("Matches the topic keywords in your request.")
        if not reasons and mood_profile is not None:
            reasons.append(f"Ranked for your {mood_profile.label.lower()} mood.")

        return score, reasons[0] if reasons else "Matches your search."

    def _user_profile_terms(self, user: User | None) -> list[str]:
        if user is None or user.profile is None:
            return []
        joined = " ".join([*user.profile.interests, *user.profile.preferred_categories])
        return tokenize_text(joined)

    def _normalize_datetime(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    left_list = [float(item) for item in left]
    right_list = [float(item) for item in right]
    if not left_list or not right_list or len(left_list) != len(right_list):
        return 0.0

    numerator = sum(a * b for a, b in zip(left_list, right_list, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left_list))
    right_norm = math.sqrt(sum(b * b for b in right_list))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
