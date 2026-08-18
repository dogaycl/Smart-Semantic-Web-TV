from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.types import configure_pgvector_support
from app.models.catalog_item import CatalogItem
from app.models.channel import Channel
from app.models.epg_entry import EPGEntry
from app.models.search_document import SearchDocument
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.channel_repository import ChannelRepository
from app.repositories.epg_entry_repository import EPGEntryRepository
from app.repositories.search_document_repository import SearchDocumentRepository
from app.services.catalog.service import CatalogService
from app.services.search.embeddings.base import EmbeddingService
from app.services.search.embeddings.gemini import GeminiEmbeddingService

logger = logging.getLogger(__name__)


class SearchIndexService:
    def __init__(
        self,
        *,
        embedding_service: EmbeddingService | None = None,
        search_repository: SearchDocumentRepository | None = None,
    ) -> None:
        self.settings = get_settings()
        self.embedding_service = embedding_service or GeminiEmbeddingService()
        self.search_repository = search_repository or SearchDocumentRepository()
        self.catalog_repository = CatalogRepository()
        self.channel_repository = ChannelRepository()
        self.epg_entry_repository = EPGEntryRepository()
        self.catalog_service = CatalogService()

    def ensure_ready(self, *, db: Session) -> None:
        if not self.settings.search_index_auto_sync:
            return
        self.sync_documents(db=db)

    def embedding_enabled(self) -> bool:
        return self.embedding_service.is_configured()

    def sync_documents(self, *, db: Session) -> list[SearchDocument]:
        configure_pgvector_support(db.get_bind())
        now = datetime.now(timezone.utc)
        existing = {document.source_key: document for document in self.search_repository.list_all(db=db)}
        active_source_keys: set[str] = set()
        documents_to_embed: list[tuple[SearchDocument, str | None, str]] = []

        for item in self.catalog_repository.list_active(db=db):
            document, should_embed = self._upsert_catalog_document(
                db=db,
                item=item,
                existing=existing,
                now=now,
            )
            active_source_keys.add(document.source_key)
            if should_embed:
                documents_to_embed.append((document, document.title, document.searchable_text))

        channels = self.channel_repository.list_active(db=db)
        channel_by_id = {channel.id: channel for channel in channels}
        epg_end = now + timedelta(hours=self.settings.search_index_epg_window_hours)
        epg_entries = self.epg_entry_repository.list_for_window(
            db=db,
            channel_ids=list(channel_by_id.keys()),
            start=now,
            end=epg_end,
        )
        for entry in epg_entries:
            channel = channel_by_id.get(entry.channel_id)
            end_time = self._normalize_datetime(entry.end_time)
            if channel is None or end_time <= now:
                continue
            document, should_embed = self._upsert_epg_document(
                db=db,
                entry=entry,
                channel=channel,
                existing=existing,
                now=now,
            )
            active_source_keys.add(document.source_key)
            if should_embed:
                documents_to_embed.append((document, document.title, document.searchable_text))

        for source_key, document in existing.items():
            if source_key not in active_source_keys:
                db.delete(document)

        if self.embedding_service.is_configured():
            for document, title, text in documents_to_embed:
                try:
                    embedding = self.embedding_service.embed_document(title=title, text=text)
                except Exception as exc:
                    logger.warning(
                        "Gemini embedding failed for search document %s, leaving it unembedded: %s",
                        document.source_key,
                        exc,
                    )
                    continue
                document.embedding = embedding
                document.embedding_model = self.settings.gemini_embedding_model
                document.embedding_dimensions = self.settings.gemini_embedding_dimensions
                document.embedding_updated_at = now

        db.commit()
        return self.search_repository.list_active(db=db)

    def _upsert_catalog_document(
        self,
        *,
        db: Session,
        item: CatalogItem,
        existing: dict[str, SearchDocument],
        now: datetime,
    ) -> tuple[SearchDocument, bool]:
        source_key = f"catalog:{item.slug}"
        genres = [genre.name for genre in item.genres]
        searchable_text = self._catalog_search_text(item=item, genres=genres)
        content_hash = sha256(searchable_text.encode("utf-8")).hexdigest()
        document = existing.get(source_key)
        should_embed = False

        if document is None:
            document = self.search_repository.create(
                source_key=source_key,
                document_type="catalog",
                content_type=item.content_type,
                content_hash=content_hash,
                searchable_text=searchable_text,
                title=item.title,
            )
            db.add(document)

        if document.content_hash != content_hash:
            should_embed = True

        document.catalog_item_id = item.id
        document.epg_entry_id = None
        document.channel_id = None
        document.content_slug = item.slug
        document.channel_slug = None
        document.channel_name = None
        document.channel_logo_url = None
        document.channel_source_type = None
        document.title = item.title
        document.description = item.overview
        document.category_label = "Movies" if item.content_type == "movie" else "Series"
        document.genres = genres
        document.language = item.original_language
        document.duration_minutes = item.runtime_minutes
        document.runtime_label = self.catalog_service.runtime_display(item)
        document.year = item.release_date.year if item.release_date else None
        document.rating = item.vote_average
        document.popularity = item.popularity
        document.poster_url = item.poster_url
        document.backdrop_url = item.backdrop_url
        document.availability_start = None
        document.availability_end = None
        document.searchable_text = searchable_text
        document.content_hash = content_hash
        document.is_active = True
        document.last_indexed_at = now

        if document.embedding_model != self.settings.gemini_embedding_model or document.embedding_dimensions != self.settings.gemini_embedding_dimensions:
            should_embed = True
        if document.embedding is None and self.embedding_service.is_configured():
            should_embed = True

        return document, should_embed

    def _upsert_epg_document(
        self,
        *,
        db: Session,
        entry: EPGEntry,
        channel: Channel,
        existing: dict[str, SearchDocument],
        now: datetime,
    ) -> tuple[SearchDocument, bool]:
        source_key = f"epg:{channel.id}:{entry.source}:{entry.external_id}"
        genres = [value for value in [entry.category, channel.category] if value]
        start_time = self._normalize_datetime(entry.start_time)
        end_time = self._normalize_datetime(entry.end_time)
        duration_minutes = max(int((end_time - start_time).total_seconds() // 60), 1)
        searchable_text = self._epg_search_text(entry=entry, channel=channel, genres=genres)
        content_hash = sha256(searchable_text.encode("utf-8")).hexdigest()
        document = existing.get(source_key)
        should_embed = False

        if document is None:
            document = self.search_repository.create(
                source_key=source_key,
                document_type="epg",
                content_type="program",
                content_hash=content_hash,
                searchable_text=searchable_text,
                title=entry.title,
            )
            db.add(document)

        if document.content_hash != content_hash:
            should_embed = True

        document.catalog_item_id = None
        document.epg_entry_id = entry.id
        document.channel_id = channel.id
        document.content_slug = None
        document.channel_slug = channel.slug
        document.channel_name = channel.name
        document.channel_logo_url = channel.logo_url
        document.channel_source_type = channel.source_type
        document.title = entry.title
        document.description = entry.description or channel.description
        document.category_label = "Live TV"
        document.genres = genres
        document.language = channel.language
        document.duration_minutes = duration_minutes
        document.runtime_label = f"{duration_minutes}m"
        document.year = None
        document.rating = None
        document.popularity = None
        document.poster_url = channel.logo_url or channel.thumbnail_url
        document.backdrop_url = channel.thumbnail_url or channel.logo_url
        document.availability_start = start_time
        document.availability_end = end_time
        document.searchable_text = searchable_text
        document.content_hash = content_hash
        document.is_active = True
        document.last_indexed_at = now

        if document.embedding_model != self.settings.gemini_embedding_model or document.embedding_dimensions != self.settings.gemini_embedding_dimensions:
            should_embed = True
        if document.embedding is None and self.embedding_service.is_configured():
            should_embed = True

        return document, should_embed

    def _catalog_search_text(self, *, item: CatalogItem, genres: list[str]) -> str:
        parts = [
            f"title: {item.title}",
            f"original title: {item.original_title or 'none'}",
            f"type: {'movie' if item.content_type == 'movie' else 'series'}",
            f"genres: {', '.join(genres) or 'none'}",
            f"overview: {item.overview or 'none'}",
            f"cast: {', '.join(item.top_cast[:5]) or 'none'}",
            f"crew: {', '.join(item.top_crew[:3]) or 'none'}",
            f"language: {item.original_language or 'unknown'}",
            f"status: {item.status or 'unknown'}",
        ]
        if item.runtime_minutes:
            parts.append(f"runtime minutes: {item.runtime_minutes}")
        return " | ".join(parts)

    def _epg_search_text(self, *, entry: EPGEntry, channel: Channel, genres: list[str]) -> str:
        return " | ".join(
            [
                f"title: {entry.title}",
                f"description: {entry.description or 'none'}",
                f"program category: {entry.category or 'none'}",
                f"channel: {channel.name}",
                f"channel category: {channel.category or 'none'}",
                f"channel country: {channel.country or 'none'}",
                f"channel language: {channel.language or 'none'}",
                f"live source: {channel.source_type}",
                f"genres: {', '.join(genres) or 'none'}",
            ]
        )

    def _normalize_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
