# Vynex

Smart Semantic Web TV Platform demo for CENG384 Project III.

The repository now contains a real FastAPI backend plus a hash-routed frontend prototype. The current implementation includes:

- real user authentication
- real Turkish and English live TV and EPG integration
- real TMDB-backed movie and series metadata
- favorites and watch history
- semantic search and recommendations
- "My Channel": a Gemini-backed personalized live + on-demand planner, and a grounded assistant
- legal in-app playback for a curated subset of content
- Watch Party rooms with synchronized playback and room chat

## Local Development

### Backend

The backend lives under `backend/` and expects environment configuration from a `.env` file in
the repository root. Dependencies are declared in `backend/pyproject.toml`.

Prerequisites:

- Python 3.12+
- A running PostgreSQL server, and a database matching the `DATABASE_URL` in your `.env`

First-time setup on a new machine:

```bash
cp .env.example .env
```

Then edit `.env` and set at minimum `DATABASE_URL` and `JWT_SECRET_KEY` (see Environment Notes).

```bash
createdb smart_semantic_web_tv
```

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The first run populates channels, EPG, and the catalog from the external providers, so the
initial requests to Live TV and On Demand take longer than later ones.

Swagger / OpenAPI:

- `http://127.0.0.1:8000/docs`

### Populating live data manually

The app syncs on demand, but these commands force a refresh:

```bash
python -m app.commands.live_tv_sync sync-channels
```

```bash
python -m app.commands.live_tv_sync refresh-live-status
```

```bash
python -m app.commands.live_tv_sync sync-epg --window-hours 48
```

### Frontend

Use a local web server instead of opening `index.html` with `file://`, because invite links, backend API calls, and Watch Party WebSockets are designed for a normal HTTP origin.

```bash
python3 -m http.server 5500
```

Open:

- `http://127.0.0.1:5500/#/login`

### Backend / Frontend URLs

- Frontend: `http://127.0.0.1:5500/#/login`
- Backend API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

## Environment Notes

The backend reads secrets and connection values from environment variables. Keep real credentials local only.

At minimum, local development may require values such as:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `YOUTUBE_API_KEY`
- `TMDB_API_KEY`
- Gemini-related API settings used by the semantic, planner, and assistant phases

Use `.env.example` as the safe reference template.

## Watch Party Flow

Current Watch Party entry points:

- movie/series detail pages via `Watch Together`
- the playback page via `Watch Together`
- the Live TV page for playable live channels
- direct invite routes such as `#/watch-party/AB12CD`

Current MVP behavior:

- the room creator is the host
- the host controls shared play, pause, and seek
- participants follow the host playback state
- volume and fullscreen stay local to each participant
- room chat is real-time and persisted for recent-history reloads

## Testing

Backend tests:

```bash
cd backend
source .venv/bin/activate
pytest -q
```

Watch Party coverage includes:

- room creation and join flows
- authenticated WebSocket access
- host-only playback control enforcement
- sync-state responses
- chat broadcast
- invalid payload handling
- host disconnect expiry

## Project Notes

- Backend architecture rules are documented in `AGENTS.md`.
- Implementation planning and phase tracking live in `docs/BACKEND_PLAN.md`.
- API response contracts live in `docs/API_CONTRACT.md`.
