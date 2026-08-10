# AGENTS.md

Read this file, `docs/BACKEND_PLAN.md`, and `docs/API_CONTRACT.md` before making changes.

## Project Context

- Project: Smart Semantic Web TV Platform
- Frontend and backend are intentionally separated.
- Existing frontend code in the repository should remain stable unless a task explicitly requires a frontend change.

## Permanent Architectural Rules

- Keep backend code under `backend/`.
- Do not place business logic in `main.py`; use routers, services, repositories, models, and schemas.
- Expose backend functionality through REST APIs first; add WebSockets only in the phase that explicitly requires them.
- Keep AI and LLM integrations behind dedicated service abstractions.
- Never hardcode API keys, secrets, or database credentials.
- Load configuration from environment variables and typed settings.
- Keep modules testable, small, and replaceable.
- Use SQLAlchemy models for persistence, Pydantic schemas for API IO, and Alembic for schema migrations.
- Prefer explicit dependency injection over hidden globals.
- Use consistent `/api` route prefixes.
- Protect authenticated routes through reusable auth dependencies.
- Write or update tests for any backend behavior that is implemented.
- Update docs when architecture, contracts, or implemented phases change.

## Delivery Rules

- Respect the active backend phase in `docs/BACKEND_PLAN.md`.
- Do not implement future-phase modules early.
- When backend work is requested, summarize:
  - architecture impact
  - files created/modified
  - endpoints added or changed
  - unfinished issues or assumptions
