from __future__ import annotations

from datetime import datetime, timezone

from app.models.search_document import SearchDocument


class DiscoveryResultBuilder:
    def build(self, *, document: SearchDocument, score: float, explanation: str) -> dict:
        now = datetime.now(timezone.utc)
        availability = self._build_availability(document=document, now=now)
        result_type = "live_program"
        if document.content_type == "movie":
            result_type = "movie"
        elif document.content_type == "tv":
            result_type = "series"

        payload = {
            "id": document.source_key,
            "result_type": result_type,
            "score": round(score, 4),
            "explanation": explanation,
            "title": document.title,
            "description": document.description,
            "category_label": document.category_label or ("Live TV" if document.document_type == "epg" else "Catalog"),
            "genres": document.genres or [],
            "language": document.language,
            "runtime_minutes": document.duration_minutes,
            "runtime_display": document.runtime_label or self._runtime_label(document),
            "year": document.year,
            "release_date": None,
            "rating": round(document.rating, 1) if document.rating is not None else None,
            "popularity": round(document.popularity, 1) if document.popularity is not None else None,
            "poster_url": document.poster_url,
            "backdrop_url": document.backdrop_url,
            "content_slug": document.content_slug,
            "channel": None,
            "availability": availability,
        }

        if document.channel_id and document.channel_name:
            payload["channel"] = {
                "id": document.channel_id,
                "slug": document.channel_slug,
                "name": document.channel_name,
                "logo_url": document.channel_logo_url,
                "source_type": document.channel_source_type,
            }

        return payload

    def _build_availability(self, *, document: SearchDocument, now: datetime) -> dict:
        if document.document_type != "epg":
            return {
                "kind": "vod",
                "starts_at": None,
                "ends_at": None,
                "label": "On demand",
            }

        starts_at = self._normalize_datetime(document.availability_start)
        ends_at = self._normalize_datetime(document.availability_end)
        if starts_at and ends_at and starts_at <= now < ends_at:
            return {
                "kind": "live",
                "starts_at": starts_at,
                "ends_at": ends_at,
                "label": "Live now",
            }

        label = "Upcoming live"
        if starts_at:
            label = starts_at.astimezone().strftime("%a %H:%M")
        return {
            "kind": "upcoming_live",
            "starts_at": starts_at,
            "ends_at": ends_at,
            "label": label,
        }

    def _runtime_label(self, document: SearchDocument) -> str:
        if document.document_type == "epg":
            if document.duration_minutes:
                return f"{document.duration_minutes}m"
            return "Live"
        if document.duration_minutes:
            hours, minutes = divmod(document.duration_minutes, 60)
            if hours and minutes:
                return f"{hours}h {minutes}m"
            if hours:
                return f"{hours}h"
            return f"{minutes}m"
        return "Catalog"

    def _normalize_datetime(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
