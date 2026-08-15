from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.search_document import SearchDocument
from app.models.user import User
from app.models.viewing_plan import ViewingPlan
from app.repositories.search_document_repository import SearchDocumentRepository
from app.repositories.viewing_plan_repository import ViewingPlanRepository
from app.schemas.planner import (
    ViewingPlanChannelRead,
    ViewingPlanGenerateRequest,
    ViewingPlanItemRead,
    ViewingPlanListResponse,
    ViewingPlanRead,
    ViewingPlannerLLMItem,
    ViewingPlannerLLMResponse,
)
from app.services.llm.base import LLMService
from app.services.llm.gemini import GeminiLLMService
from app.services.recommendations.service import RecommendationService, ScoredDocument, UserTasteProfile
from app.services.search.embeddings.base import EmbeddingService
from app.services.search.embeddings.gemini import GeminiEmbeddingService
from app.services.search.index_service import SearchIndexService
from app.services.search.query_parser import normalize_text, tokenize_text
from app.services.search.service import cosine_similarity


@dataclass(slots=True)
class PlannerWindow:
    timezone_name: str
    window_start: datetime
    window_end: datetime
    max_duration_minutes: int
    preferred_categories: list[str]


@dataclass(slots=True)
class PlannerCandidate:
    candidate_id: str
    document: SearchDocument
    result_type: str
    recommendation_score: float
    recommendation_reason: str
    request_score: float
    planner_score: float

    @property
    def duration_minutes(self) -> int:
        return int(self.document.duration_minutes or 0)

    @property
    def availability_start(self) -> datetime | None:
        return self.document.availability_start

    @property
    def availability_end(self) -> datetime | None:
        return self.document.availability_end


@dataclass(slots=True)
class StoredPlanResult:
    plan: ViewingPlan
    used_fallback: bool


class ViewingPlannerService:
    def __init__(
        self,
        *,
        llm_service: LLMService | None = None,
        embedding_service: EmbeddingService | None = None,
        recommendation_service: RecommendationService | None = None,
        search_repository: SearchDocumentRepository | None = None,
        plan_repository: ViewingPlanRepository | None = None,
        index_service: SearchIndexService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.embedding_service = embedding_service or GeminiEmbeddingService()
        self.llm_service = llm_service or GeminiLLMService()
        self.search_repository = search_repository or SearchDocumentRepository()
        self.plan_repository = plan_repository or ViewingPlanRepository()
        self.recommendation_service = recommendation_service or RecommendationService(
            embedding_service=self.embedding_service,
            search_repository=self.search_repository,
        )
        self.index_service = index_service or SearchIndexService(
            embedding_service=self.embedding_service,
            search_repository=self.search_repository,
        )

    def generate_plan(
        self,
        *,
        db: Session,
        user: User,
        payload: ViewingPlanGenerateRequest,
    ) -> ViewingPlanRead:
        self.index_service.ensure_ready(db=db)
        window = self._build_window(payload=payload, user=user)
        documents = self.search_repository.list_active(db=db)
        profile, scored_documents = self.recommendation_service.score_documents(
            db=db,
            user=user,
            documents=documents,
            now=window.window_start,
            window_end=window.window_end,
        )
        candidates = self._select_candidates(
            payload=payload,
            window=window,
            profile=profile,
            documents=documents,
            scored_documents=scored_documents,
        )
        if not candidates:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No real content candidates are available for the requested planning window.",
            )

        llm_repair_applied = False
        used_fallback = False
        plan_output: ViewingPlannerLLMResponse | None = None
        validation_errors: list[str] = []

        if self.llm_service.is_configured():
            prompt = self._build_prompt(
                payload=payload,
                window=window,
                profile=profile,
                candidates=candidates,
            )
            try:
                llm_response = self.llm_service.generate_viewing_plan(prompt=prompt)
                validation_errors = self._validate_llm_plan(
                    llm_response=llm_response,
                    candidates=candidates,
                    window=window,
                )
                if validation_errors:
                    repair_prompt = self._build_prompt(
                        payload=payload,
                        window=window,
                        profile=profile,
                        candidates=candidates,
                        validation_feedback=validation_errors,
                    )
                    llm_repair_applied = True
                    llm_response = self.llm_service.generate_viewing_plan(prompt=repair_prompt)
                    validation_errors = self._validate_llm_plan(
                        llm_response=llm_response,
                        candidates=candidates,
                        window=window,
                    )
                if not validation_errors:
                    plan_output = llm_response
            except Exception:
                plan_output = None

        if plan_output is None or validation_errors:
            used_fallback = True
            plan_output = self._build_fallback_plan(
                payload=payload,
                window=window,
                profile=profile,
                candidates=candidates,
            )

        stored = self._store_plan(
            db=db,
            user=user,
            payload=payload,
            window=window,
            profile=profile,
            candidates=candidates,
            plan_output=plan_output,
            generation_source="fallback" if used_fallback else "gemini",
            llm_repair_applied=llm_repair_applied and not used_fallback,
            llm_model=None if used_fallback else self.settings.gemini_viewing_planner_model,
        )
        return self._serialize_plan(stored.plan)

    def list_plans(self, *, db: Session, user: User) -> ViewingPlanListResponse:
        plans = self.plan_repository.list_for_user(db=db, user_id=user.id)
        return ViewingPlanListResponse(items=[self._serialize_plan(plan) for plan in plans])

    def get_plan(self, *, db: Session, user: User, plan_id: int) -> ViewingPlanRead:
        plan = self.plan_repository.get_for_user(db=db, user_id=user.id, plan_id=plan_id)
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viewing plan not found.")
        return self._serialize_plan(plan)

    def _build_window(self, *, payload: ViewingPlanGenerateRequest, user: User) -> PlannerWindow:
        tz = ZoneInfo(payload.timezone)
        local_start = datetime.combine(payload.plan_date, payload.available_start, tzinfo=tz)
        local_end = datetime.combine(payload.plan_date, payload.available_end, tzinfo=tz)
        window_start = local_start.astimezone(timezone.utc)
        window_end = local_end.astimezone(timezone.utc)
        window_minutes = int((window_end - window_start).total_seconds() // 60)
        max_duration_minutes = min(payload.max_duration_minutes or window_minutes, window_minutes)

        profile_categories = user.profile.preferred_categories if user.profile else []
        preferred_categories = list(dict.fromkeys([*payload.preferred_categories, *profile_categories]))
        return PlannerWindow(
            timezone_name=payload.timezone,
            window_start=window_start,
            window_end=window_end,
            max_duration_minutes=max_duration_minutes,
            preferred_categories=preferred_categories,
        )

    def _select_candidates(
        self,
        *,
        payload: ViewingPlanGenerateRequest,
        window: PlannerWindow,
        profile: UserTasteProfile,
        documents: list[SearchDocument],
        scored_documents: list[ScoredDocument],
    ) -> list[PlannerCandidate]:
        recommendation_map = {item.document.source_key: item for item in scored_documents}
        query_scores = self._request_scores(
            query=payload.preference_text,
            documents=documents,
        )
        category_hints = {normalize_text(item) for item in window.preferred_categories}

        candidates: list[PlannerCandidate] = []
        for document in documents:
            if document.document_type == "epg":
                if not payload.include_live:
                    continue
                start = self._optional_datetime(document.availability_start)
                end = self._optional_datetime(document.availability_end)
                if start is None or end is None:
                    continue
                if start < window.window_start or end > window.window_end:
                    continue
            else:
                if not payload.include_vod:
                    continue
                if not document.duration_minutes or document.duration_minutes > window.max_duration_minutes:
                    continue

            category_score = self._category_hint_score(document=document, category_hints=category_hints)
            request_score = max(query_scores.get(document.source_key, 0.0), category_score)
            recommendation = recommendation_map.get(document.source_key)
            recommendation_score = recommendation.score if recommendation else 0.0
            recommendation_reason = (
                recommendation.explanation
                if recommendation
                else "Available in your requested window and matches the current planner filters."
            )
            planner_score = (
                (recommendation_score * 0.65)
                + (request_score * 0.25)
                + (category_score * 0.10)
            )
            if not payload.preference_text and not category_hints:
                planner_score = recommendation_score

            candidates.append(
                PlannerCandidate(
                    candidate_id=document.source_key,
                    document=document,
                    result_type=self._result_type(document),
                    recommendation_score=recommendation_score,
                    recommendation_reason=recommendation_reason,
                    request_score=request_score,
                    planner_score=round(min(planner_score, 1.0), 6),
                )
            )

        candidates.sort(
            key=lambda item: (
                -item.planner_score,
                self._optional_datetime(item.document.availability_start) or window.window_end,
                item.document.title.lower(),
            )
        )
        return candidates[: self.settings.viewing_planner_candidate_limit]

    def _request_scores(
        self,
        *,
        query: str | None,
        documents: list[SearchDocument],
    ) -> dict[str, float]:
        if not query:
            return {}

        lexical_terms = set(tokenize_text(query))
        scores: dict[str, float] = {}
        if self.embedding_service.is_configured():
            query_embedding = self.embedding_service.embed_query(query)
            for document in documents:
                if document.embedding and len(document.embedding) == len(query_embedding):
                    scores[document.source_key] = cosine_similarity(query_embedding, document.embedding)

        lexical_scores = self._lexical_scores(query_terms=lexical_terms, documents=documents)
        for source_key, lexical_score in lexical_scores.items():
            scores[source_key] = max(scores.get(source_key, 0.0), lexical_score)

        return scores

    def _lexical_scores(
        self,
        *,
        query_terms: set[str],
        documents: list[SearchDocument],
    ) -> dict[str, float]:
        if not query_terms:
            return {}
        scores: dict[str, float] = {}
        for document in documents:
            document_terms = set(tokenize_text(document.searchable_text))
            overlap = len(query_terms & document_terms)
            if overlap:
                scores[document.source_key] = overlap / max(len(query_terms), 1)
        return scores

    def _category_hint_score(self, *, document: SearchDocument, category_hints: set[str]) -> float:
        if not category_hints:
            return 0.0
        categories = {
            normalize_text(document.category_label or ""),
            *(normalize_text(item) for item in document.genres),
        }
        if not categories:
            return 0.0
        matched = len(category_hints & categories)
        return matched / max(len(category_hints), 1)

    def _build_prompt(
        self,
        *,
        payload: ViewingPlanGenerateRequest,
        window: PlannerWindow,
        profile: UserTasteProfile,
        candidates: list[PlannerCandidate],
        validation_feedback: list[str] | None = None,
    ) -> str:
        candidate_payload = [
            {
                "candidate_id": item.candidate_id,
                "result_type": item.result_type,
                "title": item.document.title,
                "category_label": item.document.category_label,
                "genres": item.document.genres,
                "description": item.document.description,
                "duration_minutes": item.document.duration_minutes,
                "recommendation_score": round(item.recommendation_score, 4),
                "recommendation_reason": item.recommendation_reason,
                "availability_start": self._iso_or_none(item.document.availability_start),
                "availability_end": self._iso_or_none(item.document.availability_end),
                "channel_name": item.document.channel_name,
            }
            for item in candidates
        ]
        feedback_block = ""
        if validation_feedback:
            feedback_block = "\nPrevious output was invalid. Fix these problems exactly:\n- " + "\n- ".join(validation_feedback)
        return (
            "You are a personalized TV viewing planner.\n"
            "Return JSON only.\n"
            "Never invent candidate IDs, titles, channels, movies, programs, or times.\n"
            "Use ONLY candidate_id values from the candidates list below.\n"
            "For live_program items, planned_start and planned_end MUST exactly match availability_start and availability_end.\n"
            "For movie or series items, planned_end MUST equal planned_start plus duration_minutes.\n"
            "Do not overlap items.\n"
            "Keep the full schedule inside the request window.\n"
            f"Maximum total planned duration: {window.max_duration_minutes} minutes.\n"
            f"Requested window UTC: {window.window_start.isoformat()} to {window.window_end.isoformat()}.\n"
            f"Requested timezone: {window.timezone_name}.\n"
            f"Requested categories: {', '.join(window.preferred_categories) or 'none'}.\n"
            f"Free-text preference: {payload.preference_text or 'none'}.\n"
            "Use the user profile and recommendation scores to choose the best real content.\n"
            f"Profile summary: {json.dumps(profile.summary)}\n"
            f"Candidates: {json.dumps(candidate_payload, ensure_ascii=True)}"
            f"{feedback_block}"
        )

    def _validate_llm_plan(
        self,
        *,
        llm_response: ViewingPlannerLLMResponse,
        candidates: list[PlannerCandidate],
        window: PlannerWindow,
    ) -> list[str]:
        candidate_map = {item.candidate_id: item for item in candidates}
        errors: list[str] = []
        seen_ids: set[str] = set()
        ordered = sorted(llm_response.plan, key=lambda item: item.planned_start)
        total_minutes = 0
        previous_end: datetime | None = None

        for item in ordered:
            candidate = candidate_map.get(item.candidate_id)
            if candidate is None:
                errors.append(f"Unknown candidate_id: {item.candidate_id}")
                continue
            if item.candidate_id in seen_ids:
                errors.append(f"Candidate used more than once: {item.candidate_id}")
            seen_ids.add(item.candidate_id)

            planned_start = self._normalize_datetime(item.planned_start)
            planned_end = self._normalize_datetime(item.planned_end)
            if planned_start < window.window_start or planned_end > window.window_end:
                errors.append(f"Item {item.candidate_id} is outside the requested window.")
            if planned_end <= planned_start:
                errors.append(f"Item {item.candidate_id} has an invalid time range.")

            duration_minutes = int((planned_end - planned_start).total_seconds() // 60)
            total_minutes += max(duration_minutes, 0)

            if previous_end and planned_start < previous_end:
                errors.append(f"Item {item.candidate_id} overlaps a previous item.")
            previous_end = planned_end

            if candidate.result_type == "live_program":
                live_start = self._normalize_datetime(candidate.availability_start)
                live_end = self._normalize_datetime(candidate.availability_end)
                if planned_start != live_start or planned_end != live_end:
                    errors.append(f"Live item {item.candidate_id} must use the real broadcast start/end.")
            else:
                if duration_minutes != candidate.duration_minutes:
                    errors.append(f"VOD item {item.candidate_id} must use its full runtime of {candidate.duration_minutes} minutes.")

        if total_minutes > window.max_duration_minutes:
            errors.append("The plan exceeds the requested max_duration_minutes.")
        return errors

    def _build_fallback_plan(
        self,
        *,
        payload: ViewingPlanGenerateRequest,
        window: PlannerWindow,
        profile: UserTasteProfile,
        candidates: list[PlannerCandidate],
    ) -> ViewingPlannerLLMResponse:
        live_candidates = [
            item for item in candidates
            if item.result_type == "live_program"
        ]
        vod_candidates = [
            item for item in candidates
            if item.result_type != "live_program"
        ]
        live_candidates.sort(
            key=lambda item: (
                -item.planner_score,
                self._normalize_datetime(item.availability_start),
            )
        )
        selected_live: list[PlannerCandidate] = []
        total_minutes = 0
        for candidate in live_candidates:
            start = self._optional_datetime(candidate.availability_start)
            end = self._optional_datetime(candidate.availability_end)
            if start is None or end is None:
                continue
            if any(
                start < self._normalize_datetime(item.availability_end)
                and end > self._normalize_datetime(item.availability_start)
                for item in selected_live
            ):
                continue
            duration = int((end - start).total_seconds() // 60)
            if total_minutes + duration > window.max_duration_minutes:
                continue
            selected_live.append(candidate)
            total_minutes += duration

        selected_live.sort(key=lambda item: self._normalize_datetime(item.availability_start))

        draft_items: list[ViewingPlannerLLMItem] = []
        used_ids: set[str] = set()
        cursor = window.window_start

        def fill_gap(gap_start: datetime, gap_end: datetime) -> None:
            nonlocal total_minutes
            gap_cursor = gap_start
            while gap_cursor < gap_end and total_minutes < window.max_duration_minutes:
                remaining_gap = int((gap_end - gap_cursor).total_seconds() // 60)
                remaining_budget = window.max_duration_minutes - total_minutes
                best = next(
                    (
                        item for item in vod_candidates
                        if item.candidate_id not in used_ids
                        and item.duration_minutes <= remaining_gap
                        and item.duration_minutes <= remaining_budget
                    ),
                    None,
                )
                if best is None:
                    break
                draft_items.append(
                    ViewingPlannerLLMItem(
                        candidate_id=best.candidate_id,
                        planned_start=gap_cursor,
                        planned_end=gap_cursor + timedelta(minutes=best.duration_minutes),
                        reason=best.recommendation_reason,
                    )
                )
                used_ids.add(best.candidate_id)
                gap_cursor = gap_cursor + timedelta(minutes=best.duration_minutes)
                total_minutes += best.duration_minutes

        for candidate in selected_live:
            live_start = self._optional_datetime(candidate.availability_start)
            live_end = self._optional_datetime(candidate.availability_end)
            if live_start is None or live_end is None:
                continue
            fill_gap(cursor, live_start)
            draft_items.append(
                ViewingPlannerLLMItem(
                    candidate_id=candidate.candidate_id,
                    planned_start=live_start,
                    planned_end=live_end,
                    reason=candidate.recommendation_reason,
                )
            )
            used_ids.add(candidate.candidate_id)
            cursor = live_end

        fill_gap(cursor, window.window_end)
        draft_items.sort(key=lambda item: item.planned_start)

        summary = (
            f"Fallback plan built from {len(draft_items)} real candidates using your profile signals."
            if draft_items
            else "No valid schedule could be generated from the current real content window."
        )
        return ViewingPlannerLLMResponse(summary=summary, plan=draft_items[: self.settings.viewing_planner_max_items])

    def _store_plan(
        self,
        *,
        db: Session,
        user: User,
        payload: ViewingPlanGenerateRequest,
        window: PlannerWindow,
        profile: UserTasteProfile,
        candidates: list[PlannerCandidate],
        plan_output: ViewingPlannerLLMResponse,
        generation_source: str,
        llm_repair_applied: bool,
        llm_model: str | None,
    ) -> StoredPlanResult:
        candidate_map = {item.candidate_id: item for item in candidates}
        plan = self.plan_repository.create_plan(
            user_id=user.id,
            plan_date=payload.plan_date,
            timezone=payload.timezone,
            available_start=window.window_start,
            available_end=window.window_end,
            max_duration_minutes=window.max_duration_minutes,
            include_live=payload.include_live,
            include_vod=payload.include_vod,
            preferred_categories=window.preferred_categories,
            preference_text=payload.preference_text,
            profile_summary=profile.summary,
            summary=plan_output.summary,
            generation_source=generation_source,
            llm_model=llm_model,
            llm_repair_applied=llm_repair_applied,
        )
        db.add(plan)
        db.flush()

        for position, item in enumerate(sorted(plan_output.plan, key=lambda entry: entry.planned_start), start=1):
            candidate = candidate_map[item.candidate_id]
            document = candidate.document
            plan_item = self.plan_repository.create_item(
                plan_id=plan.id,
                position=position,
                candidate_id=item.candidate_id,
                document_type=document.document_type,
                result_type=candidate.result_type,
                content_type=document.content_type,
                catalog_item_id=document.catalog_item_id,
                epg_entry_id=document.epg_entry_id,
                channel_id=document.channel_id,
                title=document.title,
                description=document.description,
                category_label=document.category_label or ("Live TV" if document.document_type == "epg" else "Catalog"),
                genres=document.genres,
                poster_url=document.poster_url,
                backdrop_url=document.backdrop_url,
                content_slug=document.content_slug,
                channel_slug=document.channel_slug,
                channel_name=document.channel_name,
                channel_logo_url=document.channel_logo_url,
                channel_source_type=document.channel_source_type,
                runtime_minutes=document.duration_minutes,
                runtime_display=document.runtime_label or self._runtime_display(document),
                planned_start=self._normalize_datetime(item.planned_start),
                planned_end=self._normalize_datetime(item.planned_end),
                availability_start=self._normalize_datetime(document.availability_start) if document.availability_start else None,
                availability_end=self._normalize_datetime(document.availability_end) if document.availability_end else None,
                recommendation_score=round(candidate.recommendation_score, 4),
                reason=item.reason,
            )
            db.add(plan_item)

        db.commit()
        stored_plan = self.plan_repository.get_for_user(db=db, user_id=user.id, plan_id=plan.id)
        if stored_plan is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Saved viewing plan could not be reloaded.")
        return StoredPlanResult(plan=stored_plan, used_fallback=(generation_source == "fallback"))

    def _serialize_plan(self, plan: ViewingPlan) -> ViewingPlanRead:
        items = []
        for item in plan.items:
            channel = None
            if item.channel_id and item.channel_name:
                channel = ViewingPlanChannelRead(
                    id=item.channel_id,
                    slug=item.channel_slug,
                    name=item.channel_name,
                    logo_url=item.channel_logo_url,
                    source_type=item.channel_source_type,
                )
            items.append(
                ViewingPlanItemRead(
                    id=item.id,
                    candidate_id=item.candidate_id,
                    result_type=item.result_type,
                    title=item.title,
                    description=item.description,
                    category_label=item.category_label,
                    genres=item.genres or [],
                    runtime_minutes=item.runtime_minutes,
                    runtime_display=item.runtime_display,
                    planned_start=self._normalize_datetime(item.planned_start),
                    planned_end=self._normalize_datetime(item.planned_end),
                    availability_start=self._normalize_datetime(item.availability_start) if item.availability_start else None,
                    availability_end=self._normalize_datetime(item.availability_end) if item.availability_end else None,
                    recommendation_score=round(item.recommendation_score, 4) if item.recommendation_score is not None else None,
                    reason=item.reason,
                    poster_url=item.poster_url,
                    backdrop_url=item.backdrop_url,
                    content_slug=item.content_slug,
                    channel=channel,
                )
            )

        return ViewingPlanRead(
            id=plan.id,
            plan_date=plan.plan_date,
            timezone=plan.timezone,
            available_start=self._normalize_datetime(plan.available_start),
            available_end=self._normalize_datetime(plan.available_end),
            max_duration_minutes=plan.max_duration_minutes,
            include_live=plan.include_live,
            include_vod=plan.include_vod,
            preferred_categories=plan.preferred_categories or [],
            preference_text=plan.preference_text,
            profile_summary=plan.profile_summary or [],
            summary=plan.summary,
            generation_source=plan.generation_source,
            llm_model=plan.llm_model,
            llm_repair_applied=plan.llm_repair_applied,
            items=items,
            created_at=self._normalize_datetime(plan.created_at),
            updated_at=self._normalize_datetime(plan.updated_at),
        )

    def _result_type(self, document: SearchDocument) -> str:
        if document.content_type == "movie":
            return "movie"
        if document.content_type == "tv":
            return "series"
        return "live_program"

    def _runtime_display(self, document: SearchDocument) -> str:
        if document.duration_minutes:
            hours, minutes = divmod(document.duration_minutes, 60)
            if hours and minutes:
                return f"{hours}h {minutes}m"
            if hours:
                return f"{hours}h"
            return f"{minutes}m"
        return "Live" if document.document_type == "epg" else "Catalog"

    def _normalize_datetime(self, value: datetime | None) -> datetime:
        if value is None:
            raise ValueError("datetime value is required")
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def _optional_datetime(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return self._normalize_datetime(value)

    def _iso_or_none(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return self._normalize_datetime(value).isoformat()
