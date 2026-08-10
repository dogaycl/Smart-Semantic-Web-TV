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
    core/
    db/
    models/
    repositories/
    schemas/
    services/
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

- channels
- programs
- categories
- EPG schedules
- VoD assets
- recommendation artifacts
- semantic embeddings/vector-backed search data
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

## Development Phases

- Phase 1: Foundation, database, authentication. Status: Complete.
- Phase 2: Channels, programs, categories, EPG, VoD catalog. Status: Not started.
- Phase 3: Favorites, watch history, playlists, profile enrichment. Status: In progress.
- Phase 4: Semantic search, recommendations, Gemini assistant, RAG. Status: Not started.
- Phase 5: Social TV, synchronized watching, WebSockets, admin expansion. Status: Not started.

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
