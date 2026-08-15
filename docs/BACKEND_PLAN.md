# Backend Plan

## Scope

This repository currently contains a frontend-first prototype. The backend will be added as an independent FastAPI application under `backend/`, with clean API boundaries so the frontend does not depend on internal backend implementation details.

## Planned Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic
- JWT authentication
- `pgvector` for semantic features in later phases
- Gemini API and embeddings through abstracted AI services in later phases
- WebSockets in later phases

## Target Backend Structure

```text
backend/
  alembic/
  app/
    api/
      deps/
      routers/
    commands/
    core/
    db/
    models/
    repositories/
    schemas/
    services/
      catalog/
      epg/
      llm/
      live_tv/
      planner/
      recommendations/
      search/
    main.py
  tests/
```

## Architectural Modules

### Core

- Settings and environment management
- Security utilities
- Shared constants and error handling

### API

- Versioned REST routers under `/api`
- Reusable dependencies for database sessions and authentication

### Persistence

- SQLAlchemy models
- Repository layer for database access
- Alembic migrations for schema evolution

### Services

- Authentication service
- User and profile service
- TMDB-backed movie and TV catalog provider and synchronization service
- Live TV provider abstraction and synchronization service
- EPG ingestion and normalization service
- Gemini-backed embedding service abstraction and semantic search index synchronization
- Transparent weighted recommendation service that combines VOD and live availability
- Gemini-backed viewing planner service with strict candidate validation and deterministic fallback
- Future AI services isolated behind interfaces

## Database Entities

### Phase 1

- `users`
  - `id`
  - `username`
  - `email`
  - `hashed_password`
  - `role`
  - `created_at`
- `user_profiles`
  - `id`
  - `user_id`
  - `display_name`
  - `avatar_url`
  - `interests`
  - `preferred_categories`
  - `created_at`
  - `updated_at`

### Future Phases

- programs
- categories
- VoD assets
- recommendation artifacts
- semantic embeddings/vector-backed search data
- saved viewing-plan schedules
- social watch rooms and events
- admin-specific resources

### Phase 3

- `favorites`
  - `id`
  - `user_id`
  - `content_id`
  - `added_at`
- `watch_history`
  - `id`
  - `user_id`
  - `content_id`
  - `content_type`
  - `watch_position_seconds`
  - `total_watched_duration_seconds`
  - `is_completed`
  - `last_watched_at`
  - `created_at`
  - `updated_at`

Phase 3 intentionally uses generic content references (`content_id`, `content_type`) so private personalization data can be collected before catalog entities from Phase 2 are fully implemented.

### Phase 4

- `channels`
  - `id`
  - `slug`
  - `name`
  - `description`
  - `category`
  - `logo_url`
  - `country`
  - `language`
  - `source_type`
  - `iptv_org_channel_id`
  - `youtube_handle`
  - `youtube_channel_id`
  - `youtube_video_id`
  - `stream_url`
  - `quality`
  - `is_active`
  - `stream_status`
  - `stream_error`
  - `epg_channel_id`
  - `epg_source_url`
  - `live_status`
  - `live_title`
  - `live_description`
  - `thumbnail_url`
  - `scheduled_start_time`
  - `scheduled_end_time`
  - `last_checked_at`
- `epg_entries`
  - `id`
  - `channel_id`
  - `external_id`
  - `title`
  - `description`
  - `category`
  - `start_time`
  - `end_time`
  - `source`
  - `last_updated_at`

### Phase 5

- `catalog_items`
  - `id`
  - `slug`
  - `content_type`
  - `tmdb_id`
  - `title`
  - `original_title`
  - `overview`
  - `release_date`
  - `runtime_minutes`
  - `poster_url`
  - `backdrop_url`
  - `vote_average`
  - `popularity`
  - `original_language`
  - `status`
  - `top_cast`
  - `top_crew`
  - `number_of_seasons`
  - `number_of_episodes`
  - `tmdb_url`
  - `is_active`
  - `last_synced_at`
- `catalog_genres`
  - `id`
  - `content_item_id`
  - `tmdb_genre_id`
  - `name`
- `catalog_seasons`
  - `id`
  - `content_item_id`
  - `tmdb_season_id`
  - `season_number`
  - `name`
  - `overview`
  - `air_date`
  - `episode_count`
  - `poster_url`
- `catalog_videos`
  - `id`
  - `content_item_id`
  - `tmdb_video_id`
  - `name`
  - `site`
  - `type`
  - `video_key`
  - `official`
  - `language`
  - `country`
  - `published_at`

### Phase 6

- `search_documents`
  - `id`
  - `source_key`
  - `document_type`
  - `content_type`
  - `catalog_item_id`
  - `epg_entry_id`
  - `channel_id`
  - `content_slug`
  - `channel_slug`
  - `channel_name`
  - `channel_logo_url`
  - `channel_source_type`
  - `title`
  - `description`
  - `category_label`
  - `genres`
  - `language`
  - `duration_minutes`
  - `runtime_label`
  - `year`
  - `rating`
  - `popularity`
  - `poster_url`
  - `backdrop_url`
  - `availability_start`
  - `availability_end`
  - `searchable_text`
  - `content_hash`
  - `embedding`
  - `embedding_model`
  - `embedding_dimensions`
  - `is_active`
  - `last_indexed_at`
  - `embedding_updated_at`

### Phase 7

- `viewing_plans`
  - `id`
  - `user_id`
  - `plan_date`
  - `timezone`
  - `available_start`
  - `available_end`
  - `max_duration_minutes`
  - `include_live`
  - `include_vod`
  - `preferred_categories`
  - `preference_text`
  - `profile_summary`
  - `summary`
  - `generation_source`
  - `llm_model`
  - `llm_repair_applied`
  - `created_at`
  - `updated_at`
- `viewing_plan_items`
  - `id`
  - `plan_id`
  - `position`
  - `candidate_id`
  - `document_type`
  - `result_type`
  - `content_type`
  - `catalog_item_id`
  - `epg_entry_id`
  - `channel_id`
  - `title`
  - `description`
  - `category_label`
  - `genres`
  - `poster_url`
  - `backdrop_url`
  - `content_slug`
  - `channel_slug`
  - `channel_name`
  - `channel_logo_url`
  - `channel_source_type`
  - `runtime_minutes`
  - `runtime_display`
  - `planned_start`
  - `planned_end`
  - `availability_start`
  - `availability_end`
  - `recommendation_score`
  - `reason`
  - `created_at`

## Development Phases

- Phase 1: Foundation, database, authentication. Status: Complete.
- Phase 2: Programs, categories, movies, series, and broader VoD catalog domain. Status: Not started.
- Phase 3: Favorites, watch history, playlists, profile enrichment. Status: Complete.
- Phase 4: Real Live TV sources and real EPG ingestion. Status: Complete.
- Phase 5: Real movie and TV series catalog powered by TMDB metadata. Status: Complete.
- Phase 6: Semantic search, recommendations, Gemini assistant, RAG. Status: Complete for semantic search and transparent recommendations; Gemini assistant and RAG remain pending.
- Phase 7: Gemini-powered personalized viewing planner. Status: Complete for validated schedule generation and persistence.
- Phase 8: Social TV, synchronized watching, WebSockets, admin expansion. Status: Not started.

## Phase 1 Deliverables

- FastAPI application bootstrap
- Typed settings and environment loading
- PostgreSQL-ready SQLAlchemy setup
- Alembic configuration and initial migration
- User and user profile models
- Password hashing
- JWT access tokens
- Register, login, and current-user endpoints
- Protected-route dependency
- Automated authentication tests

## Phase 1 Completion Notes

- Implemented under `backend/` without modifying frontend application code.
- Added typed settings, modular routers/services/repositories/schemas, SQLAlchemy models, and Alembic migration scaffolding.
- Verified authentication tests with `pytest`.
- Verified migration flow with `alembic upgrade head` against a local SQLite verification database.

## Phase 3 Progress Notes

- Implemented authenticated favorites endpoints for add, list, and remove.
- Implemented authenticated watch history upsert/list endpoints with position, cumulative duration, completion state, and last watched timestamp.
- Implemented authenticated profile patching for `display_name`, `avatar_url`, `interests`, and `preferred_categories`.
- Kept personalization isolated per user through `/api/users/me/...` routes and auth dependencies.
- Structured service/repository layers so favorites and watch history can later feed recommendation services without coupling recommendation logic into this phase.
- Personal TV playlists remain pending within the broader Phase 3 bucket.

## Phase 4 Deliverables

- Real `Channel` and `EPGEntry` persistence models plus Alembic migration.
- Live TV provider abstraction:
  - `YouTubeLiveProvider` for official YouTube Data API discovery
  - `HLSStreamProvider` for direct public HLS/IPTV streams
- EPG provider abstraction:
  - `XMLTVProvider` for XMLTV and `.xml.gz` feeds
  - `YouTubeScheduleProvider` for upcoming YouTube live broadcasts
- `LiveTVSyncService` with repeatable commands for:
  - `sync-channels`
  - `refresh-live-status`
  - `sync-epg`
- Channel and EPG APIs under `/api/channels` and `/api/epg`
- Frontend Live TV page switched from mock data to backend-backed real channel, player, and guide data
- Automated tests for provider parsing, EPG normalization, timezone handling, API responses, and stream status behavior

## Phase 4 Architecture Notes

- Live playback is normalized behind a backend `playback` object so the frontend can decide between official YouTube embed playback and direct HLS playback without knowing provider internals.
- YouTube playback only uses embeddable video IDs and official embed URLs; no direct YouTube stream extraction is used.
- XMLTV and YouTube schedule data are normalized into PostgreSQL so current and upcoming program queries stay fast and testable.
- Synchronization is service-based and callable on demand today, while remaining compatible with future periodic/background execution.
- The initial live catalog is intentionally curated to a small set of public demo-safe channels instead of bulk-importing unstable IPTV lists.

## Phase 5 Deliverables

- Real `CatalogItem`, `CatalogGenre`, `CatalogSeason`, and `CatalogVideo` persistence models plus Alembic migration.
- Catalog provider abstraction:
  - `CatalogProvider`
  - `TMDBProvider`
- `CatalogSyncService` with repeatable synchronization/update support through `python -m app.commands.catalog_sync`.
- Catalog REST APIs for:
  - listing all catalog items
  - movie-only listing
  - series-only listing
  - title search
  - category/genre filtering
  - detail retrieval with seasons, trailers, and related items
- Frontend catalog pages switched from mock metadata to backend-backed real metadata for:
  - home shelves
  - on-demand page
  - movies library
  - series library
  - content detail page
  - favorites/history content resolution
- TMDB attribution surfaced in content detail views.
- Automated tests for TMDB parsing, sync/upsert behavior, category filtering, and catalog API responses.

## Phase 5 Architecture Notes

- TMDB is treated as the source of truth for movie and TV metadata; the backend persists external IDs so refreshes update existing records instead of duplicating them.
- The initial catalog uses curated TMDB discover buckets to keep the demo dataset high quality and intentionally limited to roughly 100-300 titles rather than bulk-importing a massive catalog.
- Official trailer metadata is persisted, but playback is limited to official embedded trailer providers such as YouTube/Vimeo. No copyrighted movie playback is implemented.
- Watch-provider deep streaming URLs are intentionally not treated as playable video sources in this phase.
- Frontend catalog rendering now uses real rating, popularity, images, genres, runtime, and season data instead of fictional view or match percentages.

## Phase 6 Deliverables

- PostgreSQL `pgvector`-backed `search_documents` index table plus Alembic migration.
- Provider-independent `EmbeddingService` abstraction with `GeminiEmbeddingService`.
- `SearchIndexService` that normalizes active catalog items and upcoming EPG programs into one searchable semantic index.
- `SemanticSearchService` behind `POST /api/search/semantic` for natural-language search across:
  - upcoming EPG programs
  - movies
  - TV series
- `RecommendationService` behind `GET /api/recommendations` using:
  - profile interests
  - preferred categories
  - favorites
  - watch history
  - semantic similarity
  - popularity
  - live availability windows
- Frontend Discover page switched from mock semantic search to backend results.
- Home recommendation shelf switched from local-only filtering to backend recommendations with live and VOD mixing when relevant.
- Automated ranking and API tests for semantic search and recommendations.

## Phase 6 Architecture Notes

- Search indexing is intentionally separate from catalog and EPG source tables so Live TV programs and VOD titles can share one semantic retrieval plane.
- The backend stores denormalized search metadata plus embeddings so search and recommendation queries do not need to understand TMDB, XMLTV, or channel-specific internals.
- Gemini embeddings are abstracted behind `EmbeddingService`, and the model name stays environment-configurable so the project is not locked to an outdated embedding identifier.
- PostgreSQL uses `pgvector` distance queries when available, while tests and lightweight local fallbacks can still rank with Python cosine similarity against the same stored vectors.
- The Phase 6 migration requires the `vector` PostgreSQL extension to be installed on the database server before `20260815_0005` can be applied successfully.
- Recommendation scoring is transparent and weighted rather than delegated to an LLM:
  - semantic similarity
  - category and interest overlap
  - genre affinity from favorites/history
  - popularity
  - live availability bonus
- Search and recommendation endpoints return explanations so the frontend can show why a result appeared without relying on a separate Gemini chat layer.

## Phase 7 Deliverables

- `ViewingPlan` and `ViewingPlanItem` persistence models plus Alembic migration.
- Provider-independent `LLMService` abstraction with `GeminiLLMService`.
- `ViewingPlannerService` that:
  - builds a real candidate pool from upcoming EPG entries and duration-fitting VOD titles
  - attaches recommendation scores and user profile context
  - sends only real candidate IDs and metadata to Gemini
  - validates every returned schedule against the candidate set and requested time window
  - retries once with validation feedback if the first Gemini output is invalid
  - falls back deterministically if Gemini fails or still returns invalid output
- Planner APIs for:
  - `POST /api/viewing-plans/generate`
  - `GET /api/viewing-plans`
  - `GET /api/viewing-plans/{id}`
- Frontend AI Planner UI connected to the real backend on the existing AI page.
- Automated tests for candidate selection, overlap prevention, invalid IDs, duration validation, fallback behavior, and saved-plan API flows.

## Phase 7 Architecture Notes

- The planner never lets Gemini invent content. Candidate selection happens entirely inside the backend before any LLM call.
- Upcoming live candidates are restricted to EPG items fully contained inside the requested viewing window, so live items can be validated against exact broadcast times.
- VOD candidates are restricted to titles with known runtimes that fit inside the user’s total requested free-time budget.
- Gemini is used only for sequencing and explanation. Basic personalization, recommendation scoring, and final rule enforcement remain deterministic backend responsibilities.
- The planner stores saved schedules in PostgreSQL so the frontend can reopen previous plans without re-running Gemini.
- The current official Gemini integration path uses the GA `google-genai` SDK, with the planner model kept environment-configurable. The default local configuration targets `gemini-3.6-flash`.
