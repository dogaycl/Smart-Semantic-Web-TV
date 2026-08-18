from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
import unicodedata

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.catalog_genre import CatalogGenre
from app.models.catalog_item import CatalogItem
from app.models.catalog_season import CatalogSeason
from app.models.catalog_video import CatalogVideo
from app.repositories.catalog_repository import CatalogRepository
from app.services.catalog.providers.base import CatalogProvider, ExternalCatalogItemPayload
from app.services.catalog.providers.tmdb_provider import TMDBProvider


class CatalogSyncService:
    def __init__(
        self,
        *,
        provider: CatalogProvider | None = None,
        repository: CatalogRepository | None = None,
    ) -> None:
        self.settings = get_settings()
        self.provider = provider or TMDBProvider()
        self.repository = repository or CatalogRepository()

    def ensure_ready(self, *, db: Session) -> None:
        if not self.settings.catalog_auto_sync or not self.provider.is_configured():
            return

        active_count = self.repository.count_active(db=db)
        latest_sync = self.repository.latest_sync_at(db=db)
        is_stale = latest_sync is None or latest_sync < datetime.now(timezone.utc) - timedelta(minutes=self.settings.catalog_sync_ttl_minutes)
        if active_count == 0 or is_stale:
            self.sync_catalog(db=db)

    def sync_catalog(self, *, db: Session, target_items: int | None = None) -> list[CatalogItem]:
        if not self.provider.is_configured():
            return self.repository.list_active(db=db)

        now = datetime.now(timezone.utc)
        target = target_items or self.settings.catalog_sync_target_items
        candidates = self.provider.discover_catalog_candidates(target_items=target)
        if not candidates:
            return self.repository.list_active(db=db)
        synced_keys: set[tuple[str, int]] = set()

        for candidate in candidates:
            payload = self.provider.fetch_catalog_item(tmdb_id=candidate.tmdb_id, content_type=candidate.content_type)
            item = self._upsert_item(db=db, payload=payload, synced_at=now)
            synced_keys.add((item.content_type, item.tmdb_id))

        if synced_keys:
            for existing in self.repository.list_active(db=db):
                if (existing.content_type, existing.tmdb_id) not in synced_keys:
                    existing.is_active = False

        db.commit()
        return self.repository.list_active(db=db)

    def sync_payload(
        self,
        *,
        db: Session,
        payload: ExternalCatalogItemPayload,
        synced_at: datetime | None = None,
    ) -> CatalogItem:
        return self._upsert_item(
            db=db,
            payload=payload,
            synced_at=synced_at or datetime.now(timezone.utc),
        )

    def _upsert_item(self, *, db: Session, payload: ExternalCatalogItemPayload, synced_at: datetime) -> CatalogItem:
        item = self.repository.get_by_tmdb(db=db, content_type=payload.content_type, tmdb_id=payload.tmdb_id)
        if item is None:
            item = self.repository.create(
                slug=self._build_slug(payload.content_type, payload.title, payload.tmdb_id),
                content_type=payload.content_type,
                tmdb_id=payload.tmdb_id,
                title=payload.title,
                tmdb_url=payload.tmdb_url,
            )
            db.add(item)
        else:
            item.genres.clear()
            item.seasons.clear()
            item.videos.clear()
            db.flush()

        item.slug = self._build_slug(payload.content_type, payload.title, payload.tmdb_id)
        item.content_type = payload.content_type
        item.tmdb_id = payload.tmdb_id
        item.title = payload.title
        item.original_title = payload.original_title
        item.overview = payload.overview
        item.release_date = payload.release_date
        item.runtime_minutes = payload.runtime_minutes
        item.poster_url = payload.poster_url
        item.backdrop_url = payload.backdrop_url
        item.vote_average = payload.vote_average
        item.popularity = payload.popularity
        item.original_language = payload.original_language
        item.status = payload.status
        item.top_cast = payload.top_cast
        item.top_crew = payload.top_crew
        item.number_of_seasons = payload.number_of_seasons
        item.number_of_episodes = payload.number_of_episodes
        item.tmdb_url = payload.tmdb_url
        item.is_active = True
        item.last_synced_at = synced_at
        item.genres = [
            CatalogGenre(tmdb_genre_id=genre_id, name=name)
            for genre_id, name in payload.genres
        ]
        item.seasons = [
            CatalogSeason(
                tmdb_season_id=season.tmdb_season_id,
                season_number=season.season_number,
                name=season.name,
                overview=season.overview,
                air_date=season.air_date,
                episode_count=season.episode_count,
                poster_url=season.poster_url,
            )
            for season in payload.seasons
        ]
        item.videos = [
            CatalogVideo(
                tmdb_video_id=video.tmdb_video_id,
                name=video.name,
                site=video.site,
                type=video.type,
                video_key=video.video_key,
                official=video.official,
                language=video.language,
                country=video.country,
                published_at=video.published_at,
            )
            for video in payload.videos
        ]
        return item

    def _build_slug(self, content_type: str, title: str, tmdb_id: int) -> str:
        normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
        normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
        normalized = re.sub(r"-{2,}", "-", normalized)
        prefix = "movie" if content_type == "movie" else "series"
        return f"{prefix}-{normalized or tmdb_id}-{tmdb_id}"
