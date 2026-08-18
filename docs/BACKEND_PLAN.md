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
- WebSockets for real-time watch-party rooms and chat

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
      assistant/
      catalog/
      epg/
      llm/
      live_tv/
      planner/
      recommendations/
      search/
      watch_party/
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
- Context-aware assistant retrieval and response orchestration service with grounded RAG over trusted metadata
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

### Phase 10

- `playback_sources`
  - `id`
  - `content_item_id`
  - `name`
  - `source_type`
  - `playback_url`
  - `external_video_id`
  - `embed_url`
  - `quality`
  - `language`
  - `is_primary`
  - `is_active`
  - `supports_seek`
  - `supports_state_tracking`
  - `provider_name`
  - `provider_url`
  - `license_note`
  - `source_note`
  - `last_checked_at`
  - `last_error`
  - `created_at`
  - `updated_at`

### Phase 11

- `watch_rooms`
  - `id`
  - `room_code`
  - `host_user_id`
  - `target_type`
  - `content_slug`
  - `channel_id`
  - `title_snapshot`
  - `status`
  - `privacy`
  - `current_position`
  - `playback_state`
  - `host_last_seen_at`
  - `created_at`
  - `updated_at`
- `watch_room_participants`
  - `id`
  - `room_id`
  - `user_id`
  - `is_host`
  - `is_active`
  - `joined_at`
  - `last_seen_at`
  - `left_at`
- `watch_room_messages`
  - `id`
  - `room_id`
  - `user_id`
  - `message_text`
  - `created_at`

## Development Phases

- Phase 1: Foundation, database, authentication. Status: Complete.
- Phase 2: Programs, categories, movies, series, and broader VoD catalog domain. Status: Not started.
- Phase 3: Favorites, watch history, playlists, profile enrichment. Status: Complete.
- Phase 4: Real Live TV sources and real EPG ingestion. Status: Complete.
- Phase 5: Real movie and TV series catalog powered by TMDB metadata. Status: Complete.
- Phase 6: Semantic search and transparent personalized recommendations. Status: Complete.
- Phase 7: Gemini-powered personalized viewing planner. Status: Complete for validated schedule generation and persistence.
- Phase 8: Context-aware AI content assistant with grounded retrieval and Gemini response generation. Status: Complete.
- Phase 9: English-language Live TV and EPG curation for the demo experience. Status: Complete (superseded by Phase 12's bilingual curation).
- Phase 10: Real movie playback with legal source abstraction, unified player adapters, and watch-progress-aware catalog playback. Status: Complete.
- Phase 11: Watch Party with synchronized playback, host-controlled rooms, and real-time chat over FastAPI WebSockets. Status: Complete.
- Phase 12: Turkish + English Live TV/EPG expansion, and "My Channel" personalized live+on-demand planner rename/hardening. Status: Complete.

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

## Phase 9 Deliverables

- English-first curated live channel catalog for the university demo, kept intentionally small and manually verified instead of importing hundreds of unstable IPTV entries.
- `LiveTVSyncService` enrichment updated to use current iptv-org `channels`, `feeds`, `streams`, `logos`, `guides`, and `countries` metadata rather than assuming deprecated fields.
- Browser-safe HLS candidate ranking that prefers:
  - English-language feeds
  - preferred demo regions
  - feed/guide metadata when available
  - public playback without custom headers
- Default sync behavior now deactivates non-curated legacy records instead of deleting them, so the demo catalog stays clean while preserving historical rows internally.
- Live TV frontend filter chips for:
  - `All`
  - `News`
  - `Entertainment`
  - `Documentary`
  - `Business`
  - `Education`
  - `Sports`
  - `Technology`
  - `General TV`
- Clear `Schedule unavailable` states when a channel has no verified real guide data in the active window.
- Automated sync tests covering curated-channel activation, English-language preference, and browser-safe stream candidate selection.

## Phase 9 Architecture Notes

- Seed metadata is the source of truth for demo-facing category labels and English-language curation; iptv-org data is used to enrich logos, country metadata, feed language hints, guide hints, and public stream candidates.
- The default demo catalog now prioritizes a diverse English-language mix across News, Business, Technology, Documentary, Sports, Education, Entertainment, and General TV.
- HLS verification remains backend-driven through `HLSStreamProvider`, but frontend smoke testing is still necessary because some manifests that are technically reachable can remain browser-sensitive.
- Channels without trustworthy XMLTV coverage remain visible only if playback is verified; their schedule UI must explicitly state `Schedule unavailable`.
- YouTube provider support remains in the architecture, but YouTube channels stay excluded from the default local demo experience when `YOUTUBE_API_KEY` is not configured.

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
- Search and recommendation endpoints return explanations so the frontend can show why a result appeared even before the dedicated assistant layer is involved.

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

## Phase 8 Deliverables

- `AssistantService` behind `POST /api/assistant/chat` for context-aware questions about the currently viewed catalog title, program, or live channel.
- `RetrievalService` that:
  - resolves trusted current-content context from catalog slugs, EPG entry IDs, or channel IDs
  - collects grounded context chunks from real catalog metadata, EPG metadata, channel metadata, and existing search-index text
  - ranks retrieved chunks with lexical signals and embeddings when available
- Extended provider-independent `LLMService` with assistant-specific structured JSON generation through `GeminiLLMService`.
- Deterministic fallback assistant behavior when Gemini is unavailable or returns unusable output.
- Frontend “Ask Vynex AI” dock connected to the real backend for:
  - content detail pages
  - live TV program/channel context
- Automated tests for grounded assistant service behavior and API responses using mocked Gemini outputs.

## Phase 8 Architecture Notes

- The assistant is intentionally not a generic chatbot. Every request must be tied to a real current content context in the database.
- Retrieval happens before Gemini is called. The backend resolves the current catalog item, EPG program, or live channel and passes only trusted chunks into the LLM prompt.
- The assistant never claims transcript-level or scene-level knowledge when no trusted transcript exists. For live/program questions, answers are explicitly limited to guide and channel metadata when necessary.
- Existing `search_documents` and embeddings are reused as a retrieval layer instead of creating a duplicate assistant-only vector store.
- Gemini remains environment-configurable through `GEMINI_ASSISTANT_MODEL`, and the backend validates/filters chunk citations before returning source snippets to the frontend.

## Phase 10 Deliverables

- Real `PlaybackSource` persistence model plus Alembic migration for attaching legal playable sources to catalog items.
- Dedicated playback services under `app/services/playback/`:
  - curated legal source registry
  - catalog synchronization/enrichment service
  - source health/status checker
  - catalog playback response builder
- Backend playback API:
  - `GET /api/catalog/{slug}/playback`
- Curated demo playback catalog spanning multiple legal source types:
  - public HLS
  - direct MP4
  - official YouTube embeds
  - official external embeds
- Frontend playback route and unified adapter layer for:
  - HTML5 MP4
  - HLS
  - YouTube
  - external iframe embeds
- Existing content detail and catalog flows updated so titles without a legal full source now fall back to:
  - `Watch Trailer`
  - `Not Available for Playback`
- Watch-progress integration reused from Phase 3 so supported player types can resume and persist progress against the authenticated user.
- Automated tests for playback API responses, curated sync behavior, and watch-progress-aware playback payloads.

## Phase 10 Architecture Notes

- TMDB remains metadata-only. Playback is attached through a separate `playback_sources` table so commercial catalog metadata is never mistaken for a licensed stream.
- Playback availability is normalized per content item through a single backend response that tells the frontend:
  - whether real playback is available
  - which source type to initialize
  - which fallback action to show when playback is unavailable
- Source-specific logic is isolated from page components:
  - backend services choose and validate sources
  - frontend adapters normalize `play`, `pause`, `seek`, `getCurrentTime`, `getDuration`, and state reporting
- Public-domain, open-license, and officially embeddable sources are intentionally curated in a small demo-safe subset rather than pretending the entire TMDB catalog is streamable.
- Health checks are lightweight and advisory. A reachable source is marked as healthy, but the frontend still needs visible playback error states because browser-level media compatibility can differ from server-side reachability.
- The normalized adapter contract is intentionally designed so a future Watch Party / synchronized playback phase can reuse one consistent control surface across HLS, MP4, YouTube, and external embeds.

## Phase 11 Deliverables

- Real-time Watch Party backend under `app/services/watch_party/` with:
  - room lifecycle service
  - room connection manager
  - persisted chat messages
  - host disconnect grace handling
- New persisted social-watch models and Alembic migration for:
  - watch rooms
  - room participants
  - room messages
- Watch Party REST APIs:
  - `POST /api/watch-party/rooms`
  - `GET /api/watch-party/rooms/{room_code}`
  - `POST /api/watch-party/rooms/{room_code}/join`
  - `POST /api/watch-party/rooms/{room_code}/leave`
  - `DELETE /api/watch-party/rooms/{room_code}`
- Watch Party WebSocket endpoint:
  - `GET /api/watch-party/ws/{room_code}?token=<jwt>` via WebSocket upgrade
- Host-controlled synchronized playback over the existing normalized player adapter surface for:
  - HLS
  - MP4
  - YouTube
  - external embeds with limited shared controls
- Real-time room chat restricted to authenticated room members.
- Frontend Watch Party UI connected to:
  - content detail pages
  - playback pages
  - live TV channels
  - invite-link based `#/watch-party/{roomCode}` routing
- Automated backend tests for room creation, membership, WebSocket authorization, host controls, sync state, chat broadcast, invalid payload handling, and host disconnect expiry.

## Phase 11 Architecture Notes

- The backend keeps Watch Party single-server and intentionally in-memory for active WebSocket connections. Horizontal scaling would require shared connection state and pub-sub later.
- Authentication is reused from the existing JWT stack. The WebSocket endpoint validates the bearer token before accepting the connection and never trusts a frontend-supplied `user_id`.
- The backend stores authoritative room playback state (`playback_state`, `current_position`, `updated_at`) so reconnecting clients can resynchronize immediately.
- The host is the only user allowed to emit shared playback control events in the MVP. Participants can still use local-only controls such as volume and fullscreen.
- Drift correction is lightweight by design:
  - participants periodically request `SYNC_STATE`
  - seekable sources are corrected only when drift exceeds a threshold
  - non-seekable live sources follow play/pause state without constant forced seeks
- Room chat is persisted to PostgreSQL so reconnecting participants can load recent conversation history.
- The frontend uses the existing player adapter abstraction rather than binding WebSocket logic to a single player implementation. This keeps the Phase 10 playback architecture reusable for future collaborative features.

## Phase 12 Deliverables

- Curated Turkish live channel catalog added to `LIVE_TV_CHANNEL_SEEDS`: TRT Haber, TRT 1, TRT Muzik, TRT Belgesel, Bloomberg HT, Haberturk, TGRT Haber, DHA, and Dream Turk (all individually verified with a real HTTP + HLS manifest + browser-CORS check before being marked active), plus ATV, Kanal D, Star TV, TV8, and NTV kept `is_active=False` with a documented reason (official stream reachable, but the broadcaster's CDN does not send `Access-Control-Allow-Origin`, so playback is not proxied around that restriction), plus CNN Turk, Show TV, and TRT Spor defined as YouTube-sourced channels that activate automatically once `YOUTUBE_API_KEY` is configured.
- International catalog additions: DW English, France 24 English (News), Red Bull TV and Trace Urban (new `Youth` category), and More Than Sports TV (`Sports`).
- New `Music` and `Youth` channel categories end to end (seed data, repository/API filters, frontend filter chips).
- `GET /api/channels` gained optional `category` and `language` query filters (`ChannelRepository.list_active`).
- `LiveTVSyncService` HLS stream ranking now prefers each channel's own declared language (`ChannelSeed.language`) instead of unconditionally preferring English, and `DEMO_PREFERRED_COUNTRIES` now includes `TR`.
- `LiveTVSyncService.refresh_live_status` now checks channels concurrently (`ThreadPoolExecutor`) instead of sequentially - with the catalog now spanning 20+ channels, the old sequential sweep could take long enough to trip the frontend's request timeout whenever the staleness TTL expired mid-session.
- Real XMLTV EPG mapping wired for every new Turkish channel via the existing `epgshare01.online` `TR3` region feed (the same source already used by `trt-world`); channels with no genuine EPG match (e.g. `dha-tv`, the wire-service feed) intentionally have no `epg_channel_id` and correctly surface `Schedule unavailable` instead of invented data.
- `components/EPGGuide.js` now computes and highlights the real current time slot (`NOW`) and the next upcoming entry per channel (`NEXT`), instead of only highlighting the selected channel's row.
- `pages/LiveTvPage.js` gained a second, independent language filter row (`All` / `Turkish` / `English`) alongside the existing category filter chips, and the category chip list grew to include `Music` and `Youth`.
- The Gemini integration (`GeminiLLMService`) was audited end-to-end against the installed `google-genai` SDK: added an explicit request timeout and retry/backoff (`HttpOptions`/`HttpRetryOptions`, retrying `408/429/5xx`), explicit handling (with logging, not silent swallowing) for API errors (with HTTP status, and a distinct message for `429` rate limits), timeouts/connection errors, malformed JSON, and Pydantic schema validation failures. The planner and assistant services, and every Gemini-embedding call site (`SearchIndexService`, `RecommendationService`, `ViewingPlannerService`, `RetrievalService`), now log a warning and degrade gracefully instead of raising when Gemini is unavailable or returns something unusable.
- `RecommendationService`'s EPG match explanation ("Live tonight and matches your X preference") now reports the category that actually matched instead of always reporting the user's first preferred category.
- `ViewingPlannerService._select_candidates` now also excludes: EPG candidates on a channel whose `stream_status` is not `healthy`, VOD candidates with no active/healthy `PlaybackSource`, and VOD candidates the user has already fully watched (`WatchHistory.is_completed`).
- The user-facing "AI Planner" feature is renamed "My Channel" throughout the frontend (nav, page copy, route). A new `POST /api/my-channel/generate` (+ `GET /api/my-channel`, `GET /api/my-channel/{id}`) adapts the existing `ViewingPlannerService` rather than duplicating it - `/api/viewing-plans/*` and the `/ai` frontend route both keep working unchanged. `pages/MyChannelPage.js` replaces `pages/AIHubPage.js` with a schedule-style UI: When (Now/Tonight/Tomorrow/Custom) + How much time (1h/2h/3h/Custom) + mood/category chips instead of raw form fields, an auto-computed "Using your interests: ..." line, LIVE/MOVIE/SERIES/DOCUMENTARY badges, and LIVE NOW / "Starts at HH:MM" / "Already ended" framing per item computed against the real current time.
- New/updated automated tests: `test_gemini_llm_service.py` (structured-output parsing, malformed JSON, schema validation failures, rate-limit/server-error handling, all via a fake SDK - no live network calls), `test_my_channel_api.py` (My Channel delegates to the same planner as `/api/viewing-plans`, and falls back deterministically when Gemini is unavailable), extended `test_viewing_planner_service.py` coverage (unhealthy-channel exclusion, no-playback-source exclusion, already-completed-content exclusion), and a channel category/language filter test in `test_live_tv_api.py`.

## Phase 12 Architecture Notes

- Turkish channel curation deliberately favors official broadcaster domains/CDNs (e.g. `medya.trt.com.tr`) over third-party relay mirrors, even when a mirror technically passes the HLS/CORS health check - a handful of real, publicly reachable streams (S Sport, the only found TRT Spor candidate) were excluded because the only working URL was served from an unrelated third-party domain rather than the broadcaster's own infrastructure, and could not be confirmed as authorized.
- No stream URL is proxied to work around a missing `Access-Control-Allow-Origin` header. A channel whose only known stream fails the browser-CORS check is disabled (`is_active=False`), not faked or routed through a backend relay.
- My Channel intentionally still has no dedicated request schema of its own - it reuses `ViewingPlanGenerateRequest` unchanged, because the existing fields (`plan_date`, `available_start`, `available_end`, `max_duration_minutes`, `preferred_categories`, `preference_text`, `include_live`, `include_vod`) already cover every input the new quick-controls UI needs to compute client-side before calling the API.

## Phase 12 Real-Credentials Activation Pass

Once `GEMINI_API_KEY`, `TMDB_API_KEY`, and `YOUTUBE_API_KEY` were configured locally, this pass verified every provider against the real API and fixed two real bugs it surfaced:

- **Catalog reactivation gap (fixed):** `CatalogSyncService.sync_catalog()` correctly deactivates any catalog item TMDB's popularity-sorted discover results no longer surface - but the curated legal-playback demo titles (Big Buck Bunny, Tears of Steel, etc.) never appear in that popularity list, so a bulk resync was silently deactivating them, hiding the only content with a real `PlaybackSource` from `GET /api/catalog`. No code change was needed - `catalog.py`'s router already calls `sync_service.ensure_ready()` immediately followed by `playback_sync_service.ensure_ready()` on every relevant request, and the latter correctly re-resolves and reactivates curated titles by TMDB id. Added `test_playback_sync_service_reactivates_curated_item_after_bulk_catalog_sync` to lock this sequence in as a regression test.
- **Embedding rate-limit hardening:** `GeminiEmbeddingService._embed_text()` had no retry logic at all; a single 429 from the free-tier embedding quota permanently left a search document unembedded. Added retry with exponential backoff (`MAX_ATTEMPTS = 3`, 2s/4s/8s, honoring a `Retry-After` header when present). Tuned deliberately conservative (not the 5-attempt/30s-cap version tried first) because `httpx.post()` here is a *synchronous* call inside an async FastAPI request handler - a long retry chain blocks the whole event loop, not just the one request, which was directly observed (`/api/channels` and `/api/search/semantic` both stalled while an unrelated embedding retry was in flight). A full sync-to-async migration of the catalog/live-tv/embedding HTTP clients would remove this class of issue entirely but is out of scope for an activation/verification pass.
- Real TMDB sync populated 245 active catalog items (140 movies / 105 series) across the existing 10 curated buckets; the curated playback-catalog sync separately resolved 14 of 16 registry titles to real `PlaybackSource` rows once TMDB search actually worked.
- Real YouTube Data API activation confirmed the existing provider already reports `offline` (not `broken`) for a resolvable channel with no current broadcast, exactly as designed - used this to move `atv-tr`, `kanal-d`, `star-tv`, `tv8-tr`, and `ntv-tr` from a CORS-blocked-inactive-HLS seed to a verified-official-YouTube-channel seed (`source_type="youtube"`) instead of leaving them permanently inactive, since all five resolve to genuine official channels even when not currently live.
- A real, unmocked Gemini call against the production `ViewingPlannerService` prompt/schema confirmed `gemini-3.6-flash` works correctly with structured output on the currently-installed `google-genai` SDK; no model change was made per the explicit instruction to trust a working real API call over assumption.
