from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.catalog_item import CatalogItem
from app.models.playback_source import PlaybackSource
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.playback_source_repository import PlaybackSourceRepository
from app.services.catalog.providers.tmdb_provider import TMDBProvider
from app.services.catalog.sync_service import CatalogSyncService
from app.services.playback.registry import CURATED_PLAYBACK_TITLES, CuratedPlaybackTitle, PlaybackSourceSeed


class PlaybackCatalogSyncService:
    def __init__(
        self,
        *,
        provider: TMDBProvider | None = None,
        catalog_repository: CatalogRepository | None = None,
        playback_repository: PlaybackSourceRepository | None = None,
        catalog_sync_service: CatalogSyncService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.provider = provider or TMDBProvider()
        self.catalog_repository = catalog_repository or CatalogRepository()
        self.playback_repository = playback_repository or PlaybackSourceRepository()
        self.catalog_sync_service = catalog_sync_service or CatalogSyncService(provider=self.provider, repository=self.catalog_repository)

    def ensure_ready(self, *, db: Session) -> None:
        if not self.settings.playback_catalog_auto_sync:
            return
        if not self.provider.is_configured():
            return
        active_sources = self.playback_repository.count_active(db=db)
        if active_sources >= 10:
            return
        self.sync_curated_catalog(db=db)

    def sync_curated_catalog(self, *, db: Session) -> list[CatalogItem]:
        touched = False
        for entry in CURATED_PLAYBACK_TITLES:
            item = self._resolve_item(db=db, entry=entry)
            if item is None:
                continue
            if self._sync_sources(db=db, item=item, entry=entry):
                touched = True
        if touched:
            db.commit()
        return self.catalog_repository.list_active(db=db)

    def _resolve_item(self, *, db: Session, entry: CuratedPlaybackTitle) -> CatalogItem | None:
        item = self.catalog_repository.find_by_title_and_year(
            db=db,
            title_variants=entry.title_variants,
            release_year=entry.release_year,
            content_type=entry.content_type,
        )
        if item is not None:
            return item

        candidate = self.provider.search_catalog_item(
            title=entry.search_title,
            content_type=entry.content_type,
            release_year=entry.release_year,
        )
        if candidate is None:
            return None

        payload = self.provider.fetch_catalog_item(tmdb_id=candidate.tmdb_id, content_type=candidate.content_type)
        item = self.catalog_sync_service.sync_payload(
            db=db,
            payload=payload,
            synced_at=datetime.now(timezone.utc),
        )
        db.flush()
        return item

    def _sync_sources(self, *, db: Session, item: CatalogItem, entry: CuratedPlaybackTitle) -> bool:
        existing_by_name = {source.name: source for source in item.playback_sources}
        now = datetime.now(timezone.utc)
        touched = False

        seen_names = {seed.name for seed in entry.sources}
        for name, source in existing_by_name.items():
            should_be_active = name in seen_names
            if source.is_active != should_be_active:
                source.is_active = should_be_active
                source.updated_at = now
                touched = True

        for seed in entry.sources:
            source = existing_by_name.get(seed.name)
            if source is None:
                source = self.playback_repository.create(
                    content_item_id=item.id,
                    name=seed.name,
                )
                db.add(source)
                item.playback_sources.append(source)
                touched = True

            touched = self._apply_seed(source=source, seed=seed, now=now) or touched

        return touched

    def _apply_seed(self, *, source: PlaybackSource, seed: PlaybackSourceSeed, now: datetime) -> bool:
        updates = {
            "source_type": seed.source_type,
            "playback_url": seed.playback_url,
            "external_video_id": seed.external_video_id,
            "embed_url": seed.embed_url,
            "quality": seed.quality,
            "language": seed.language,
            "is_primary": seed.is_primary,
            "is_active": True,
            "supports_seek": seed.supports_seek,
            "supports_state_tracking": seed.supports_state_tracking,
            "provider_name": seed.provider_name,
            "provider_url": seed.provider_url,
            "license_note": seed.license_note,
            "source_note": seed.source_note,
        }
        changed = False
        for field_name, value in updates.items():
            if getattr(source, field_name) != value:
                setattr(source, field_name, value)
                changed = True

        if source.last_checked_at is None:
            source.last_checked_at = now
            source.last_error = None
            changed = True

        if changed:
            source.updated_at = now
        return changed
