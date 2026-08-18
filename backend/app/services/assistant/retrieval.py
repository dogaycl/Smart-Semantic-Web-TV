from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.catalog_item import CatalogItem
from app.models.channel import Channel
from app.models.epg_entry import EPGEntry
from app.models.search_document import SearchDocument
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.channel_repository import ChannelRepository
from app.repositories.epg_entry_repository import EPGEntryRepository
from app.repositories.search_document_repository import SearchDocumentRepository
from app.schemas.assistant import AssistantChatRequest, AssistantContextType, AssistantSourceType
from app.schemas.live_tv import ChannelProgramRead
from app.services.catalog.service import CatalogService
from app.services.live_tv.service import LiveTVService
from app.services.search.embeddings.base import EmbeddingService
from app.services.search.embeddings.gemini import GeminiEmbeddingService
from app.services.search.index_service import SearchIndexService
from app.services.search.query_parser import tokenize_text
from app.services.search.service import cosine_similarity


@dataclass(slots=True)
class RetrievedChunk:
    chunk_id: str
    source_type: AssistantSourceType
    title: str
    text: str
    score: float = 0.0


@dataclass(slots=True)
class RetrievedContext:
    context_type: AssistantContextType
    title: str
    description: str | None
    category_label: str | None
    content_slug: str | None
    channel_id: int | None
    epg_entry_id: int | None
    channel_name: str | None = None
    live_status: str | None = None
    current_program_title: str | None = None
    next_program_title: str | None = None
    has_transcript: bool = False
    metadata_only: bool = True
    search_document: SearchDocument | None = None
    chunks: list[RetrievedChunk] = field(default_factory=list)


logger = logging.getLogger(__name__)


class RetrievalService:
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
        self.catalog_repository = CatalogRepository()
        self.channel_repository = ChannelRepository()
        self.epg_entry_repository = EPGEntryRepository()
        self.catalog_service = CatalogService()
        self.live_tv_service = LiveTVService()

    def retrieve(
        self,
        *,
        db: Session,
        payload: AssistantChatRequest,
    ) -> RetrievedContext:
        self.index_service.ensure_ready(db=db)

        if payload.context_type == "catalog":
            context = self._retrieve_catalog_context(db=db, payload=payload)
        elif payload.context_type == "program":
            context = self._retrieve_program_context(db=db, payload=payload)
        else:
            context = self._retrieve_channel_context(db=db, payload=payload)

        context.chunks = self._rank_chunks(
            query=payload.message,
            search_document=context.search_document,
            chunks=context.chunks,
        )
        return context

    def _retrieve_catalog_context(
        self,
        *,
        db: Session,
        payload: AssistantChatRequest,
    ) -> RetrievedContext:
        item = self.catalog_repository.get_by_slug(db=db, slug=payload.content_slug or "")
        if item is None or not item.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found.")

        related_items = self.catalog_repository.list_related(db=db, item=item, limit=4)
        search_document = self.search_repository.get_by_catalog_item_id(db=db, catalog_item_id=item.id)
        chunks = self._catalog_chunks(item=item, related_items=related_items, search_document=search_document)
        return RetrievedContext(
            context_type="catalog",
            title=item.title,
            description=item.overview,
            category_label="Movies" if item.content_type == "movie" else "Series",
            content_slug=item.slug,
            channel_id=None,
            epg_entry_id=None,
            metadata_only=False,
            search_document=search_document,
            chunks=chunks,
        )

    def _retrieve_program_context(
        self,
        *,
        db: Session,
        payload: AssistantChatRequest,
    ) -> RetrievedContext:
        entry = self.epg_entry_repository.get_by_id(db=db, entry_id=payload.epg_entry_id or 0)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program entry not found.")

        channel = self.channel_repository.get_by_id(db=db, channel_id=entry.channel_id)
        if channel is None or not channel.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found.")

        search_document = self.search_repository.get_by_epg_entry_id(db=db, epg_entry_id=entry.id)
        live_read = self.live_tv_service.build_channel_live_read(channel)
        current_program = live_read.current_program
        next_program = live_read.next_program
        chunks = self._program_chunks(
            entry=entry,
            channel=channel,
            current_program=current_program,
            next_program=next_program,
            search_document=search_document,
        )
        return RetrievedContext(
            context_type="program",
            title=entry.title,
            description=entry.description or channel.description,
            category_label=entry.category or channel.category or "Live TV",
            content_slug=None,
            channel_id=channel.id,
            epg_entry_id=entry.id,
            channel_name=channel.name,
            live_status=channel.live_status,
            current_program_title=current_program.title if current_program else None,
            next_program_title=next_program.title if next_program else None,
            metadata_only=True,
            search_document=search_document,
            chunks=chunks,
        )

    def _retrieve_channel_context(
        self,
        *,
        db: Session,
        payload: AssistantChatRequest,
    ) -> RetrievedContext:
        channel = self.channel_repository.get_by_id(db=db, channel_id=payload.channel_id or 0)
        if channel is None or not channel.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found.")

        live_read = self.live_tv_service.build_channel_live_read(channel)
        focus_program = live_read.current_program or live_read.next_program
        search_document = None
        if focus_program is not None:
            search_document = self.search_repository.get_by_epg_entry_id(db=db, epg_entry_id=focus_program.id)

        chunks = self._channel_chunks(
            channel=channel,
            current_program=live_read.current_program,
            next_program=live_read.next_program,
            search_document=search_document,
        )
        return RetrievedContext(
            context_type="channel",
            title=channel.name,
            description=channel.description or channel.live_description,
            category_label=channel.category or "Live TV",
            content_slug=None,
            channel_id=channel.id,
            epg_entry_id=focus_program.id if focus_program else None,
            channel_name=channel.name,
            live_status=channel.live_status,
            current_program_title=live_read.current_program.title if live_read.current_program else None,
            next_program_title=live_read.next_program.title if live_read.next_program else None,
            metadata_only=True,
            search_document=search_document,
            chunks=chunks,
        )

    def _catalog_chunks(
        self,
        *,
        item: CatalogItem,
        related_items: list[CatalogItem],
        search_document: SearchDocument | None,
    ) -> list[RetrievedChunk]:
        genres = [genre.name for genre in item.genres]
        metadata_parts = [
            f"Type: {'Movie' if item.content_type == 'movie' else 'Series'}",
            f"Genres: {', '.join(genres) or 'Unknown'}",
            f"Release date: {item.release_date.isoformat() if item.release_date else 'Unknown'}",
            f"Runtime: {self.catalog_service.runtime_display(item)}",
            f"Language: {item.original_language or 'Unknown'}",
            f"Status: {item.status or 'Unknown'}",
        ]
        chunks = [
            RetrievedChunk(
                chunk_id=f"catalog-metadata:{item.slug}",
                source_type="catalog_metadata",
                title=f"{item.title} metadata",
                text=". ".join(metadata_parts),
            )
        ]

        if item.overview:
            chunks.append(
                RetrievedChunk(
                    chunk_id=f"catalog-overview:{item.slug}",
                    source_type="catalog_metadata",
                    title=f"{item.title} overview",
                    text=item.overview,
                )
            )

        if item.top_cast or item.top_crew:
            chunks.append(
                RetrievedChunk(
                    chunk_id=f"catalog-credits:{item.slug}",
                    source_type="credits_metadata",
                    title=f"{item.title} credits",
                    text=(
                        f"Top cast: {', '.join(item.top_cast[:6]) or 'Unknown'}. "
                        f"Top crew: {', '.join(item.top_crew[:4]) or 'Unknown'}."
                    ),
                )
            )

        if item.seasons:
            season_summary = " ".join(
                f"{season.name} ({season.episode_count or 'unknown'} episodes)"
                for season in item.seasons[:4]
            )
            chunks.append(
                RetrievedChunk(
                    chunk_id=f"catalog-seasons:{item.slug}",
                    source_type="season_metadata",
                    title=f"{item.title} seasons",
                    text=season_summary,
                )
            )

        if related_items:
            related_summary = ", ".join(related.title for related in related_items[:4])
            chunks.append(
                RetrievedChunk(
                    chunk_id=f"catalog-related:{item.slug}",
                    source_type="related_metadata",
                    title=f"Titles related to {item.title}",
                    text=f"Related titles in the local catalog: {related_summary}.",
                )
            )

        if search_document and search_document.searchable_text:
            chunks.append(
                RetrievedChunk(
                    chunk_id=f"search-index:{search_document.source_key}",
                    source_type="search_index",
                    title=f"Indexed description for {item.title}",
                    text=search_document.searchable_text,
                )
            )

        return chunks

    def _program_chunks(
        self,
        *,
        entry: EPGEntry,
        channel: Channel,
        current_program: ChannelProgramRead | None,
        next_program: ChannelProgramRead | None,
        search_document: SearchDocument | None,
    ) -> list[RetrievedChunk]:
        chunks = [
            RetrievedChunk(
                chunk_id=f"program-metadata:{entry.id}",
                source_type="program_metadata",
                title=f"{entry.title} guide metadata",
                text=(
                    f"Program title: {entry.title}. "
                    f"Description: {entry.description or 'No description available'}. "
                    f"Category: {entry.category or 'Unknown'}. "
                    f"Broadcast window: {self._format_time(entry.start_time)} to {self._format_time(entry.end_time)} UTC."
                ),
            ),
            RetrievedChunk(
                chunk_id=f"channel-metadata:{channel.id}",
                source_type="channel_metadata",
                title=f"{channel.name} channel metadata",
                text=(
                    f"Channel: {channel.name}. "
                    f"Description: {channel.description or channel.live_description or 'No description available'}. "
                    f"Category: {channel.category or 'Unknown'}. "
                    f"Country: {channel.country or 'Unknown'}. "
                    f"Language: {channel.language or 'Unknown'}. "
                    f"Source type: {channel.source_type}. "
                    f"Live status: {channel.live_status}."
                ),
            ),
        ]

        schedule_parts = []
        if current_program:
            schedule_parts.append(
                f"Current program: {current_program.title} from {self._format_time(current_program.start_time)} to {self._format_time(current_program.end_time)} UTC."
            )
        if next_program:
            schedule_parts.append(
                f"Next program: {next_program.title} from {self._format_time(next_program.start_time)} to {self._format_time(next_program.end_time)} UTC."
            )
        if schedule_parts:
            chunks.append(
                RetrievedChunk(
                    chunk_id=f"program-schedule:{entry.id}",
                    source_type="program_metadata",
                    title=f"{channel.name} schedule snapshot",
                    text=" ".join(schedule_parts),
                )
            )

        if search_document and search_document.searchable_text:
            chunks.append(
                RetrievedChunk(
                    chunk_id=f"search-index:{search_document.source_key}",
                    source_type="search_index",
                    title=f"Indexed guide text for {entry.title}",
                    text=search_document.searchable_text,
                )
            )

        return chunks

    def _channel_chunks(
        self,
        *,
        channel: Channel,
        current_program: ChannelProgramRead | None,
        next_program: ChannelProgramRead | None,
        search_document: SearchDocument | None,
    ) -> list[RetrievedChunk]:
        chunks = [
            RetrievedChunk(
                chunk_id=f"channel-metadata:{channel.id}",
                source_type="channel_metadata",
                title=f"{channel.name} channel metadata",
                text=(
                    f"Channel: {channel.name}. "
                    f"Description: {channel.description or channel.live_description or 'No description available'}. "
                    f"Category: {channel.category or 'Unknown'}. "
                    f"Country: {channel.country or 'Unknown'}. "
                    f"Language: {channel.language or 'Unknown'}. "
                    f"Source type: {channel.source_type}. "
                    f"Live status: {channel.live_status}."
                ),
            )
        ]

        if current_program:
            chunks.append(
                RetrievedChunk(
                    chunk_id=f"channel-current:{channel.id}:{current_program.id}",
                    source_type="program_metadata",
                    title=f"Current program on {channel.name}",
                    text=(
                        f"Current program: {current_program.title}. "
                        f"Description: {current_program.description or 'No description available'}. "
                        f"Category: {current_program.category or 'Unknown'}. "
                        f"Window: {self._format_time(current_program.start_time)} to {self._format_time(current_program.end_time)} UTC."
                    ),
                )
            )
        if next_program:
            chunks.append(
                RetrievedChunk(
                    chunk_id=f"channel-next:{channel.id}:{next_program.id}",
                    source_type="program_metadata",
                    title=f"Next program on {channel.name}",
                    text=(
                        f"Next program: {next_program.title}. "
                        f"Description: {next_program.description or 'No description available'}. "
                        f"Category: {next_program.category or 'Unknown'}. "
                        f"Window: {self._format_time(next_program.start_time)} to {self._format_time(next_program.end_time)} UTC."
                    ),
                )
            )

        if search_document and search_document.searchable_text:
            chunks.append(
                RetrievedChunk(
                    chunk_id=f"search-index:{search_document.source_key}",
                    source_type="search_index",
                    title=f"Indexed live text for {channel.name}",
                    text=search_document.searchable_text,
                )
            )

        return chunks

    def _rank_chunks(
        self,
        *,
        query: str,
        search_document: SearchDocument | None,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        query_terms = set(tokenize_text(query))
        query_embedding: list[float] | None = None
        if self.embedding_service.is_configured():
            try:
                query_embedding = self.embedding_service.embed_query(query)
            except Exception as exc:
                logger.warning("Gemini embedding query failed, ranking chunks lexically only: %s", exc)
                query_embedding = None

        semantic_score = 0.0
        if query_embedding and search_document and search_document.embedding:
            semantic_score = cosine_similarity(query_embedding, search_document.embedding)

        ranked: list[RetrievedChunk] = []
        for chunk in chunks:
            chunk_terms = set(tokenize_text(chunk.text))
            lexical_score = 0.0
            if query_terms and chunk_terms:
                lexical_score = len(query_terms & chunk_terms) / max(len(query_terms), 1)
            score = lexical_score + (semantic_score * 0.35) + self._chunk_bonus(chunk.source_type)
            ranked.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    source_type=chunk.source_type,
                    title=chunk.title,
                    text=chunk.text,
                    score=round(score, 6),
                )
            )

        ranked.sort(key=lambda item: (-item.score, item.chunk_id))
        return ranked[:6]

    def _chunk_bonus(self, source_type: AssistantSourceType) -> float:
        if source_type in {"catalog_metadata", "program_metadata"}:
            return 0.18
        if source_type in {"credits_metadata", "channel_metadata"}:
            return 0.12
        if source_type == "search_index":
            return 0.08
        return 0.05

    def _format_time(self, value: datetime) -> str:
        normalized = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return normalized.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
