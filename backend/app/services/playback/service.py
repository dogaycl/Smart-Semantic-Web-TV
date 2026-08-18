from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.catalog_item import CatalogItem
from app.models.catalog_video import CatalogVideo
from app.models.playback_source import PlaybackSource
from app.models.user import User
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.watch_history_repository import WatchHistoryRepository
from app.services.catalog.service import CatalogService
from app.services.playback.health_service import PlaybackHealthService


SOURCE_PRIORITY = {
    "mp4": 0,
    "hls": 1,
    "youtube": 2,
    "external": 3,
}


class CatalogPlaybackService:
    def __init__(
        self,
        *,
        catalog_repository: CatalogRepository | None = None,
        watch_history_repository: WatchHistoryRepository | None = None,
        catalog_service: CatalogService | None = None,
        health_service: PlaybackHealthService | None = None,
    ) -> None:
        self.catalog_repository = catalog_repository or CatalogRepository()
        self.watch_history_repository = watch_history_repository or WatchHistoryRepository()
        self.catalog_service = catalog_service or CatalogService()
        self.health_service = health_service or PlaybackHealthService()

    def build_response(
        self,
        *,
        db: Session,
        item: CatalogItem,
        current_user: User | None = None,
    ) -> dict:
        sources = self._prepare_sources(db=db, item=item)
        trailer = self.catalog_service._preferred_video(item.videos)
        watch_progress = None
        if current_user is not None:
            watch_progress = self.watch_history_repository.get_for_user_content(
                db=db,
                user_id=current_user.id,
                content_id=item.slug,
                content_type="content",
            )

        primary_source = sources[0] if sources else None
        playback_available = primary_source is not None and primary_source.last_error is None
        watch_action = "watch_now" if playback_available else ("watch_trailer" if trailer else "not_available")

        fallback = None
        message = "Legal playback is available for this title."
        if not playback_available:
            if trailer:
                fallback = {
                    "type": "watch_trailer",
                    "label": "Watch Trailer",
                    "message": "A full licensed source is not currently configured for this title.",
                    "embed_url": self.catalog_service.video_embed_url(trailer.site, trailer.video_key),
                }
                message = "This title is not currently playable in full, but an official trailer is available."
            else:
                fallback = {
                    "type": "not_available",
                    "label": "Not Available for Playback",
                    "message": "No legal in-app playback source is currently configured for this title.",
                    "embed_url": None,
                }
                message = "No legal in-app playback source is currently configured for this title."

        return {
            "content_id": item.id,
            "slug": item.slug,
            "title": item.title,
            "playback_available": playback_available,
            "watch_action": watch_action,
            "message": primary_source.last_error if primary_source and primary_source.last_error else message,
            "primary_source": self._build_source(primary_source) if playback_available else None,
            "sources": [self._build_source(source) for source in sources if source.last_error is None or source is primary_source],
            "trailer": self.catalog_service.build_video(trailer) if trailer else None,
            "fallback": fallback,
            "watch_progress": (
                {
                    "watch_position_seconds": watch_progress.watch_position_seconds,
                    "total_watched_duration_seconds": watch_progress.total_watched_duration_seconds,
                    "is_completed": watch_progress.is_completed,
                    "last_watched_at": watch_progress.last_watched_at,
                }
                if watch_progress is not None
                else None
            ),
        }

    def _prepare_sources(self, *, db: Session, item: CatalogItem) -> list[PlaybackSource]:
        sources = [source for source in item.playback_sources if source.is_active]
        touched = False
        for source in sources:
            touched = self.health_service.refresh_source_if_stale(source) or touched
        if touched:
            db.commit()
            db.refresh(item)
            sources = [source for source in item.playback_sources if source.is_active]

        healthy = [source for source in sources if source.last_error is None]
        ordered = healthy or sources
        return sorted(
            ordered,
            key=lambda source: (
                0 if source.last_error is None else 1,
                0 if source.is_primary else 1,
                SOURCE_PRIORITY.get(source.source_type, 99),
                source.name.lower(),
            ),
        )

    def _build_source(self, source: PlaybackSource | None) -> dict | None:
        if source is None:
            return None
        embed_url = source.embed_url
        if source.source_type == "youtube" and source.external_video_id:
            embed_url = f"https://www.youtube.com/embed/{source.external_video_id}"
        return {
            "id": source.id,
            "name": source.name,
            "type": source.source_type,
            "playback_url": source.playback_url,
            "embed_url": embed_url,
            "external_video_id": source.external_video_id,
            "quality": source.quality,
            "language": source.language,
            "is_primary": source.is_primary,
            "provider_name": source.provider_name,
            "provider_url": source.provider_url,
            "license_note": source.license_note,
            "source_note": source.source_note,
            "last_checked_at": source.last_checked_at,
            "error": source.last_error,
            "capabilities": self._capabilities(source),
        }

    def _capabilities(self, source: PlaybackSource) -> dict:
        can_report_progress = source.source_type in {"mp4", "hls", "youtube"} and source.supports_state_tracking
        can_seek = source.supports_seek and source.source_type in {"mp4", "hls", "youtube"}
        return {
            "can_play": True,
            "can_pause": source.source_type in {"mp4", "hls", "youtube"},
            "can_seek": can_seek,
            "can_report_progress": can_report_progress,
            "can_fullscreen": True,
            "supports_seek": source.supports_seek,
            "supports_state_tracking": source.supports_state_tracking,
        }
