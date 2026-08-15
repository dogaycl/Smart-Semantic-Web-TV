from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.search_document import SearchDocument
from app.models.user import User
from app.repositories.favorite_repository import FavoriteRepository
from app.repositories.search_document_repository import SearchDocumentRepository
from app.repositories.watch_history_repository import WatchHistoryRepository
from app.schemas.discovery import RecommendationResponse
from app.services.search.embeddings.base import EmbeddingService
from app.services.search.embeddings.gemini import GeminiEmbeddingService
from app.services.search.index_service import SearchIndexService
from app.services.search.query_parser import normalize_text, tokenize_text
from app.services.search.result_builder import DiscoveryResultBuilder
from app.services.search.service import cosine_similarity


@dataclass(slots=True)
class UserTasteProfile:
    summary: list[str]
    source_keys: list[str]
    recent_titles: list[str]
    top_genres: list[str]
    preferred_categories: list[str]
    interest_terms: list[str]

    def semantic_query(self) -> str:
        parts = []
        if self.preferred_categories:
            parts.append(f"preferred categories: {', '.join(self.preferred_categories)}")
        if self.top_genres:
            parts.append(f"frequently watched genres: {', '.join(self.top_genres[:4])}")
        if self.recent_titles:
            parts.append(f"favorite and recent titles: {', '.join(self.recent_titles[:6])}")
        if self.interest_terms:
            parts.append(f"interests: {' '.join(self.interest_terms[:8])}")
        return " | ".join(parts) or "popular high quality movies series and live programs"


@dataclass(slots=True)
class ScoredDocument:
    document: SearchDocument
    score: float
    explanation: str


class RecommendationService:
    def __init__(
        self,
        *,
        embedding_service: EmbeddingService | None = None,
        search_repository: SearchDocumentRepository | None = None,
        index_service: SearchIndexService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.embedding_service = embedding_service or GeminiEmbeddingService()
        self.search_repository = search_repository or SearchDocumentRepository()
        self.index_service = index_service or SearchIndexService(
            embedding_service=self.embedding_service,
            search_repository=self.search_repository,
        )
        self.favorite_repository = FavoriteRepository()
        self.watch_history_repository = WatchHistoryRepository()
        self.result_builder = DiscoveryResultBuilder()

    def recommend(
        self,
        *,
        db: Session,
        user: User,
        limit: int,
        window_hours: int | None,
    ) -> RecommendationResponse:
        self.index_service.ensure_ready(db=db)
        documents = self.search_repository.list_active(db=db)
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(hours=window_hours or self.settings.recommendation_default_window_hours)
        profile, ranked = self.score_documents(
            db=db,
            user=user,
            documents=documents,
            now=now,
            window_end=window_end,
        )
        results = [
            self.result_builder.build(document=item.document, score=item.score, explanation=item.explanation)
            for item in ranked[:limit]
        ]

        return RecommendationResponse(
            generated_at=now,
            embedding_enabled=self.embedding_service.is_configured(),
            profile_summary=profile.summary,
            results=results,
        )

    def build_profile(self, *, db: Session, user: User) -> UserTasteProfile:
        return self._build_profile(db=db, user=user)

    def score_documents(
        self,
        *,
        db: Session,
        user: User,
        documents: list[SearchDocument],
        now: datetime,
        window_end: datetime,
    ) -> tuple[UserTasteProfile, list[ScoredDocument]]:
        profile = self._build_profile(db=db, user=user)
        source_documents = {
            document.source_key: document
            for document in self.search_repository.list_by_source_keys(db=db, source_keys=profile.source_keys)
        }
        semantic_scores = self._semantic_scores(
            db=db,
            query=profile.semantic_query(),
            limit=max(max(len(documents), 1) * 2, 60),
        )

        ranked: list[ScoredDocument] = []
        for document in documents:
            score, explanation = self._score_document(
                document=document,
                profile=profile,
                source_documents=source_documents,
                semantic_scores=semantic_scores,
                now=now,
                window_end=window_end,
            )
            if score <= 0:
                continue
            ranked.append(ScoredDocument(document=document, score=score, explanation=explanation))

        ranked.sort(key=lambda item: (-item.score, item.document.title.lower()))
        return profile, ranked

    def _build_profile(self, *, db: Session, user: User) -> UserTasteProfile:
        preferred_categories = user.profile.preferred_categories if user.profile else []
        interests = user.profile.interests if user.profile else []

        favorites = self.favorite_repository.list_for_user(db=db, user_id=user.id)
        watch_history = self.watch_history_repository.list_for_user(db=db, user_id=user.id)

        source_keys = [f"catalog:{favorite.content_id}" for favorite in favorites]
        source_keys.extend(
            f"catalog:{entry.content_id}"
            for entry in watch_history
            if entry.content_type == "content"
        )
        deduped_source_keys = list(dict.fromkeys(source_keys))
        source_documents = self.search_repository.list_by_source_keys(db=db, source_keys=deduped_source_keys)

        recent_titles = [document.title for document in source_documents]
        genre_counter = Counter(
            genre
            for document in source_documents
            for genre in document.genres
        )
        top_genres = [genre for genre, _ in genre_counter.most_common(5)]
        interest_terms = tokenize_text(" ".join([*preferred_categories, *interests]))

        summary = []
        if preferred_categories:
            summary.append(f"Preferred categories: {', '.join(preferred_categories[:3])}")
        if interests:
            summary.append(f"Interests: {', '.join(interests[:4])}")
        if top_genres:
            summary.append(f"Frequent genres: {', '.join(top_genres[:4])}")
        if recent_titles:
            summary.append(f"Recent anchors: {', '.join(recent_titles[:3])}")

        return UserTasteProfile(
            summary=summary or ["No explicit taste signals yet; using popularity and availability."],
            source_keys=deduped_source_keys,
            recent_titles=recent_titles,
            top_genres=top_genres,
            preferred_categories=preferred_categories,
            interest_terms=interest_terms,
        )

    def _semantic_scores(self, *, db: Session, query: str, limit: int) -> dict[str, float]:
        if not self.embedding_service.is_configured():
            return {}
        embedding = self.embedding_service.embed_query(query)
        return {
            document.source_key: score
            for document, score in self.search_repository.semantic_candidates(
                db=db,
                query_embedding=embedding,
                limit=limit,
            )
        }

    def _score_document(
        self,
        *,
        document: SearchDocument,
        profile: UserTasteProfile,
        source_documents: dict[str, SearchDocument],
        semantic_scores: dict[str, float],
        now: datetime,
        window_end: datetime,
    ) -> tuple[float, str]:
        if document.document_type == "epg":
            availability_start = self._normalize_datetime(document.availability_start)
            availability_end = self._normalize_datetime(document.availability_end)
            if availability_start and availability_start > window_end:
                return 0.0, ""
            if availability_end and availability_end <= now:
                return 0.0, ""

        document_tokens = set(tokenize_text(document.searchable_text))
        category_terms = {normalize_text(item) for item in profile.preferred_categories}
        interest_terms = set(profile.interest_terms)
        genre_terms = {normalize_text(item) for item in profile.top_genres}
        document_categories = {normalize_text(document.category_label or ""), *(normalize_text(item) for item in document.genres)}

        semantic_score = semantic_scores.get(document.source_key, 0.0)
        category_score = 1.0 if category_terms & document_categories else 0.0
        interest_overlap = len(interest_terms & document_tokens)
        interest_score = interest_overlap / max(len(interest_terms), 1) if interest_terms else 0.0
        genre_score = 1.0 if genre_terms & document_categories else 0.0
        popularity_score = min((document.popularity or 0.0) / 500.0, 1.0)
        availability_score = 0.0
        if document.document_type == "epg":
            availability_start = self._normalize_datetime(document.availability_start)
            availability_score = 1.0 if availability_start and availability_start <= now else 0.8

        repeat_penalty = 0.0
        if document.source_key in source_documents:
            repeat_penalty = 0.15

        related_title = self._closest_anchor_title(document=document, source_documents=source_documents)
        score = (
            (semantic_score * 0.4)
            + (category_score * 0.18)
            + (interest_score * 0.15)
            + (genre_score * 0.15)
            + (popularity_score * 0.07)
            + (availability_score * 0.05)
            - repeat_penalty
        )
        score = round(min(max(score, 0.0), 1.0), 6)
        if score <= 0.06:
            return 0.0, ""

        if document.document_type == "epg" and category_score > 0 and profile.preferred_categories:
            return score, f"Live tonight and matches your {profile.preferred_categories[0]} preference."
        if related_title and related_title != document.title:
            return score, f"Similar to {related_title}."
        if profile.top_genres:
            return score, f"Because you frequently watch {profile.top_genres[0].lower()} titles."
        if profile.interest_terms:
            return score, "Matches your saved interests."
        return score, "Popular right now and aligned with your current profile."

    def _closest_anchor_title(
        self,
        *,
        document: SearchDocument,
        source_documents: dict[str, SearchDocument],
    ) -> str | None:
        best_title: str | None = None
        best_score = 0.0
        for anchor in source_documents.values():
            if anchor.embedding and document.embedding:
                score = cosine_similarity(anchor.embedding, document.embedding)
            else:
                overlap = len(set(anchor.genres) & set(document.genres))
                score = overlap / max(len(set(anchor.genres) | set(document.genres)), 1)
            if score > best_score:
                best_score = score
                best_title = anchor.title
        if best_score < 0.15:
            return None
        return best_title

    def _normalize_datetime(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
