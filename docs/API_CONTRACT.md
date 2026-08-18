# API Contract

## Principles

- Base prefix: `/api`
- JSON request and response bodies
- Frontend must only rely on documented API shapes, not database or service internals
- Authenticated endpoints use `Authorization: Bearer <token>`

## Phase 1 Endpoints

### `POST /api/auth/register`

Request:

```json
{
  "username": "doga",
  "email": "doga@example.com",
  "password": "StrongPass123!",
  "display_name": "Doga",
  "avatar_url": "https://example.com/avatar.png",
  "interests": ["AI", "Sports"],
  "preferred_categories": ["Technology", "Documentary"]
}
```

Success response `201`:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "doga",
    "email": "doga@example.com",
    "role": "user",
    "created_at": "2026-08-09T18:00:00Z",
    "profile": {
      "display_name": "Doga",
      "avatar_url": "https://example.com/avatar.png",
      "interests": ["AI", "Sports"],
      "preferred_categories": ["Technology", "Documentary"]
    }
  }
}
```

Errors:

- `400` invalid request body
- `409` username or email already exists

Validation error shape:

```json
{
  "detail": "Validation error.",
  "errors": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error"
    }
  ]
}
```

### `POST /api/auth/login`

Request:

```json
{
  "email": "doga@example.com",
  "password": "StrongPass123!"
}
```

Success response `200`:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "doga",
    "email": "doga@example.com",
    "role": "user",
    "created_at": "2026-08-09T18:00:00Z",
    "profile": {
      "display_name": "Doga",
      "avatar_url": "https://example.com/avatar.png",
      "interests": ["AI", "Sports"],
      "preferred_categories": ["Technology", "Documentary"]
    }
  }
}
```

Errors:

- `400` invalid request body
- `401` invalid credentials

### `GET /api/auth/me`

Headers:

```text
Authorization: Bearer <token>
```

Success response `200`:

```json
{
  "id": 1,
  "username": "doga",
  "email": "doga@example.com",
  "role": "user",
  "created_at": "2026-08-09T18:00:00Z",
  "profile": {
    "display_name": "Doga",
    "avatar_url": "https://example.com/avatar.png",
    "interests": ["AI", "Sports"],
    "preferred_categories": ["Technology", "Documentary"]
  }
}
```

Errors:

- `401` missing or invalid token

## Phase 3 Endpoints

Phase 3 currently stores personalization against generic catalog references so the frontend can start persisting private user data before full content/program models are implemented.

### `GET /api/users/me/favorites`

Headers:

```text
Authorization: Bearer <token>
```

Success response `200`:

```json
[
  {
    "content_id": "movie-123",
    "added_at": "2026-08-09T18:15:00Z"
  }
]
```

Errors:

- `401` missing or invalid token

### `POST /api/users/me/favorites/{content_id}`

Headers:

```text
Authorization: Bearer <token>
```

Success response `200`:

```json
{
  "content_id": "movie-123",
  "added_at": "2026-08-09T18:15:00Z"
}
```

Errors:

- `401` missing or invalid token
- `409` conflicting favorite state

### `DELETE /api/users/me/favorites/{content_id}`

Headers:

```text
Authorization: Bearer <token>
```

Success response `204`

Errors:

- `401` missing or invalid token
- `404` favorite not found

### `GET /api/users/me/history`

Headers:

```text
Authorization: Bearer <token>
```

Success response `200`:

```json
[
  {
    "content_id": "program-7",
    "content_type": "program",
    "watch_position_seconds": 480,
    "total_watched_duration_seconds": 1200,
    "is_completed": true,
    "last_watched_at": "2026-08-09T18:30:00Z",
    "created_at": "2026-08-09T18:00:00Z",
    "updated_at": "2026-08-09T18:30:00Z"
  }
]
```

Errors:

- `401` missing or invalid token

### `POST /api/users/me/history`

Headers:

```text
Authorization: Bearer <token>
```

Request:

```json
{
  "content_id": "program-7",
  "content_type": "program",
  "watch_position_seconds": 480,
  "total_watched_duration_seconds": 1200,
  "is_completed": true,
  "last_watched_at": "2026-08-09T18:30:00Z"
}
```

Notes:

- `content_type` defaults to `"content"`.
- Posting the same `content_id` + `content_type` for the same user updates the existing history record instead of creating a duplicate.

Success response `200`:

```json
{
  "content_id": "program-7",
  "content_type": "program",
  "watch_position_seconds": 480,
  "total_watched_duration_seconds": 1200,
  "is_completed": true,
  "last_watched_at": "2026-08-09T18:30:00Z",
  "created_at": "2026-08-09T18:00:00Z",
  "updated_at": "2026-08-09T18:30:00Z"
}
```

Errors:

- `400` invalid request body
- `401` missing or invalid token

## Phase 4 Endpoints

Phase 4 exposes real live channel metadata, playback instructions, and normalized EPG windows. All date-time query parameters and response timestamps use timezone-aware ISO 8601 values.

Phase 9 refines the default Live TV contract for the demo experience; Phase 12 expands it to a curated bilingual (Turkish + English) catalog:

- the default `GET /api/channels` catalog is curated across Turkish and English public channels
- inactive legacy or non-demo records are excluded instead of deleted
- frontend clients should treat missing guide data as `Schedule unavailable`, not as a signal to synthesize mock EPG rows
- curated category labels currently used by the frontend are:
  - `News`
  - `Business`
  - `Technology`
  - `Entertainment`
  - `Documentary`
  - `Sports`
  - `Education`
  - `General TV`
  - `Music`
  - `Youth`
- `GET /api/channels` accepts optional `category` and `language` query filters (Phase 12); omitting both returns every active channel, unchanged from Phase 9

Playback contract:

- `playback.type = "hls"` means the frontend should play `playback.stream_url`
- `playback.type = "youtube"` means the frontend should render an official YouTube embed using `playback.embed_url`
- `playback.type = "unavailable"` means the frontend should show a clear unavailable state

### `GET /api/channels`

Query parameters:

- `start` optional ISO datetime used to resolve `current_program` and `next_program`
- `end` optional ISO datetime used with `start` to warm the EPG window
- `category` optional exact category label (e.g. `Music`, `Youth`, `News`); Phase 12
- `language` optional exact language code (e.g. `tr`, `en`); Phase 12

Response notes:

- `language` is normalized to a frontend-friendly code such as `en` or `tr`
- `stream_status = "healthy"` means the backend selected a currently reachable public candidate, but frontend playback should still show a visible unavailable/error state if the browser cannot render that stream
- if both `current_program` and `next_program` are `null`, the frontend should render a schedule-unavailable state rather than fallback/mock programming

Success response `200`:

```json
[
  {
    "id": 1,
    "slug": "abc-news-live",
    "name": "ABC News Live",
    "description": "US rolling news channel with live breaking coverage and headline updates.",
    "category": "News",
    "logo_url": "https://example.com/logo.png",
    "country": "US",
    "language": "en",
    "source_type": "hls",
    "youtube_channel_id": null,
    "youtube_video_id": null,
    "stream_url": "https://example.com/live.m3u8",
    "quality": "auto",
    "is_active": true,
    "stream_status": "healthy",
    "stream_error": null,
    "epg_channel_id": "ABC.News.Live.us2",
    "last_checked_at": "2026-08-15T10:30:00Z",
    "live_status": "live",
    "live_title": "20/20",
    "live_description": "Current live or guide-backed title for the channel.",
    "thumbnail_url": null,
    "scheduled_start_time": "2026-08-15T10:00:00Z",
    "scheduled_end_time": "2026-08-15T12:00:00Z",
    "playback": {
      "type": "hls",
      "youtube_video_id": null,
      "embed_url": null,
      "stream_url": "https://example.com/live.m3u8"
    },
    "current_program": {
      "id": 10,
      "external_id": "ABC.News.Live.us2:2026-08-15T10:00:00Z",
      "title": "20/20",
      "description": null,
      "category": "News",
      "start_time": "2026-08-15T10:00:00Z",
      "end_time": "2026-08-15T12:00:00Z",
      "source": "xmltv"
    },
    "next_program": {
      "id": 11,
      "external_id": "ABC.News.Live.us2:2026-08-15T12:00:00Z",
      "title": "ABC Secret Savings: Sizzling Summer Savings",
      "description": null,
      "category": "News",
      "start_time": "2026-08-15T12:00:00Z",
      "end_time": "2026-08-15T14:30:00Z",
      "source": "xmltv"
    }
  }
]
```

Errors:

- `400` invalid query parameters

### `GET /api/channels/{channel_id}`

Success response `200`:

- Same body shape as `GET /api/channels` for a single channel

Errors:

- `404` channel not found

### `GET /api/channels/{channel_id}/live`

Success response `200`:

```json
{
  "id": 1,
  "slug": "abc-news-live",
  "name": "ABC News Live",
  "source_type": "hls",
  "live_status": "live",
  "live_title": "20/20",
  "live_description": "Current live or guide-backed title for the channel.",
  "thumbnail_url": null,
  "youtube_channel_id": null,
  "youtube_video_id": null,
  "stream_url": "https://example.com/live.m3u8",
  "quality": "auto",
  "scheduled_start_time": "2026-08-15T10:00:00Z",
  "scheduled_end_time": "2026-08-15T12:00:00Z",
  "playback": {
    "type": "hls",
    "youtube_video_id": null,
    "embed_url": null,
    "stream_url": "https://example.com/live.m3u8"
  },
  "current_program": {
    "id": 10,
    "external_id": "ABC.News.Live.us2:2026-08-15T10:00:00Z",
    "title": "20/20",
    "description": null,
    "category": "News",
    "start_time": "2026-08-15T10:00:00Z",
    "end_time": "2026-08-15T12:00:00Z",
    "source": "xmltv"
  },
  "next_program": {
    "id": 11,
    "external_id": "ABC.News.Live.us2:2026-08-15T12:00:00Z",
    "title": "ABC Secret Savings: Sizzling Summer Savings",
    "description": null,
    "category": "News",
    "start_time": "2026-08-15T12:00:00Z",
    "end_time": "2026-08-15T14:30:00Z",
    "source": "xmltv"
  }
}
```

Errors:

- `404` channel not found

### `GET /api/epg`

Query parameters:

- `start` optional ISO datetime
- `end` optional ISO datetime
- `slot_minutes` optional integer between `15` and `180`, default `60`

If `start` and `end` are omitted, the backend returns a default 4-hour window.

Response notes:

- channels without verified guide data can still appear in the `channels` array with an empty `entries` list
- when `entries` is empty for a channel or no entry overlaps a visible slot, the frontend should render `Schedule unavailable`
- the backend never fabricates missing EPG rows

Success response `200`:

```json
{
  "start": "2026-08-15T10:00:00Z",
  "end": "2026-08-15T14:00:00Z",
  "slot_minutes": 60,
  "slots": [
    "2026-08-15T10:00:00Z",
    "2026-08-15T11:00:00Z",
    "2026-08-15T12:00:00Z",
    "2026-08-15T13:00:00Z"
  ],
  "channels": [
    {
      "channel": {
        "id": 1,
        "slug": "abc-news-live",
        "name": "ABC News Live",
        "description": "US rolling news channel with live breaking coverage and headline updates.",
        "category": "News",
        "logo_url": "https://example.com/logo.png",
        "country": "US",
        "language": "en",
        "source_type": "hls",
        "youtube_channel_id": null,
        "youtube_video_id": null,
        "stream_url": "https://example.com/live.m3u8",
        "quality": "auto",
        "is_active": true,
        "stream_status": "healthy",
        "stream_error": null,
        "epg_channel_id": "ABC.News.Live.us2",
        "last_checked_at": "2026-08-15T10:30:00Z",
        "live_status": "live",
        "live_title": "20/20",
        "live_description": "Current live or guide-backed title for the channel.",
        "thumbnail_url": null,
        "scheduled_start_time": "2026-08-15T10:00:00Z",
        "scheduled_end_time": "2026-08-15T12:00:00Z",
        "playback": {
          "type": "hls",
          "youtube_video_id": null,
          "embed_url": null,
          "stream_url": "https://example.com/live.m3u8"
        },
        "current_program": {
          "id": 10,
          "external_id": "ABC.News.Live.us2:2026-08-15T10:00:00Z",
          "title": "20/20",
          "description": null,
          "category": "News",
          "start_time": "2026-08-15T10:00:00Z",
          "end_time": "2026-08-15T12:00:00Z",
          "source": "xmltv"
        },
        "next_program": {
          "id": 11,
          "external_id": "ABC.News.Live.us2:2026-08-15T12:00:00Z",
          "title": "ABC Secret Savings: Sizzling Summer Savings",
          "description": null,
          "category": "News",
          "start_time": "2026-08-15T12:00:00Z",
          "end_time": "2026-08-15T14:30:00Z",
          "source": "xmltv"
        }
      },
      "entries": [
        {
          "id": 10,
          "channel_id": 1,
          "external_id": "ABC.News.Live.us2:2026-08-15T10:00:00Z",
          "title": "20/20",
          "description": null,
          "category": "News",
          "start_time": "2026-08-15T10:00:00Z",
          "end_time": "2026-08-15T12:00:00Z",
          "source": "xmltv",
          "last_updated_at": "2026-08-15T10:25:00Z"
        }
      ]
    }
  ]
}
```

Errors:

- `400` invalid query parameters

### `GET /api/epg/{channel_id}`

Query parameters:

- `start` optional ISO datetime
- `end` optional ISO datetime
- `slot_minutes` optional integer between `15` and `180`, default `60`

Success response `200`:

- Same body shape as `GET /api/epg`, limited to a single channel in the `channels` array

Errors:

- `404` channel not found

### `PATCH /api/users/me/profile`

Headers:

```text
Authorization: Bearer <token>
```

Request:

```json
{
  "display_name": "Doga Yucel",
  "avatar_url": "https://example.com/avatar.png",
  "interests": ["Semantic Search", "Cinema"],
  "preferred_categories": ["Drama", "Technology"]
}
```

Success response `200`:

```json
{
  "id": 1,
  "username": "doga",
  "email": "doga@example.com",
  "role": "user",
  "created_at": "2026-08-09T18:00:00Z",
  "profile": {
    "display_name": "Doga Yucel",
    "avatar_url": "https://example.com/avatar.png",
    "interests": ["Semantic Search", "Cinema"],
    "preferred_categories": ["Drama", "Technology"]
  }
}
```

Errors:

- `400` invalid request body
- `401` missing or invalid token

## Phase 5 Endpoints

Phase 5 replaces fictional movie and TV series metadata with real catalog data normalized from TMDB. List responses include TMDB attribution metadata so the frontend can surface the required credits/about notice.

Sort options:

- `popularity_desc`
- `rating_desc`
- `release_date_desc`
- `title_asc`

Category filter values currently normalized by the backend:

- `Documentary` / `Documentaries`
- `Science Fiction` / `Science`
- `Drama`
- `Action`
- `Comedy`

### `GET /api/catalog`

Query parameters:

- `content_type` optional `movie` or `tv`
- `category` optional app-level category alias
- `genre` optional exact genre name from TMDB metadata
- `search` optional title/original-title search string
- `sort` optional sort value, default `popularity_desc`
- `limit` optional integer `1..300`, default `48`
- `offset` optional integer, default `0`
- `slugs` optional comma-separated slug list for resolving saved favorites/history items

Success response `200`:

```json
{
  "items": [
    {
      "id": 1,
      "slug": "movie-dune-part-two-693134",
      "content_type": "movie",
      "tmdb_id": 693134,
      "title": "Dune: Part Two",
      "original_title": "Dune: Part Two",
      "overview": "Paul Atreides unites with Chani and the Fremen.",
      "genres": ["Adventure", "Science Fiction"],
      "release_date": "2024-02-27",
      "year": 2024,
      "runtime_minutes": 166,
      "runtime_display": "2h 46m",
      "poster_url": "https://image.tmdb.org/t/p/w500/example.jpg",
      "backdrop_url": "https://image.tmdb.org/t/p/original/example.jpg",
      "rating": 8.2,
      "popularity": 445.6,
      "language": "en",
      "status": "Released",
      "number_of_seasons": null,
      "number_of_episodes": null,
      "category_label": "Movies",
      "primary_genre": "Adventure",
      "tmdb_url": "https://www.themoviedb.org/movie/693134",
      "has_trailer": true,
      "last_synced_at": "2026-08-15T11:00:00+00:00"
    }
  ],
  "total": 1,
  "limit": 48,
  "offset": 0,
  "attribution": {
    "source": "TMDB",
    "notice": "This product uses the TMDB API but is not endorsed or certified by TMDB.",
    "url": "https://www.themoviedb.org",
    "logo_url": "https://www.themoviedb.org/assets/...svg"
  }
}
```

Errors:

- `400` invalid query parameters

### `GET /api/catalog/movies`

Query parameters:

- Same filtering parameters as `GET /api/catalog`, but results are limited to movie records

Success response `200`:

- Same body shape as `GET /api/catalog`

### `GET /api/catalog/series`

Query parameters:

- Same filtering parameters as `GET /api/catalog`, but results are limited to TV series records

Success response `200`:

- Same body shape as `GET /api/catalog`

### `GET /api/catalog/{slug}`

Success response `200`:

```json
{
  "id": 1,
  "slug": "movie-dune-part-two-693134",
  "content_type": "movie",
  "tmdb_id": 693134,
  "title": "Dune: Part Two",
  "original_title": "Dune: Part Two",
  "overview": "Paul Atreides unites with Chani and the Fremen.",
  "genres": ["Adventure", "Science Fiction"],
  "release_date": "2024-02-27",
  "year": 2024,
  "runtime_minutes": 166,
  "runtime_display": "2h 46m",
  "poster_url": "https://image.tmdb.org/t/p/w500/example.jpg",
  "backdrop_url": "https://image.tmdb.org/t/p/original/example.jpg",
  "rating": 8.2,
  "popularity": 445.6,
  "language": "en",
  "status": "Released",
  "number_of_seasons": null,
  "number_of_episodes": null,
  "category_label": "Movies",
  "primary_genre": "Adventure",
  "tmdb_url": "https://www.themoviedb.org/movie/693134",
  "has_trailer": true,
  "last_synced_at": "2026-08-15T11:00:00+00:00",
  "top_cast": ["Timothee Chalamet", "Zendaya"],
  "top_crew": ["Denis Villeneuve"],
  "videos": [
    {
      "name": "Official Trailer",
      "site": "YouTube",
      "type": "Trailer",
      "official": true,
      "published_at": "2024-01-01T10:00:00+00:00",
      "embed_url": "https://www.youtube.com/embed/abcd1234"
    }
  ],
  "seasons": [],
  "trailer": {
    "name": "Official Trailer",
    "site": "YouTube",
    "type": "Trailer",
    "official": true,
    "published_at": "2024-01-01T10:00:00+00:00",
    "embed_url": "https://www.youtube.com/embed/abcd1234"
  },
  "related_items": [
    {
      "id": 2,
      "slug": "movie-arrival-329865",
      "content_type": "movie",
      "tmdb_id": 329865,
      "title": "Arrival",
      "original_title": "Arrival",
      "overview": "A linguist works with the military.",
      "genres": ["Drama", "Science Fiction"],
      "release_date": "2016-11-10",
      "year": 2016,
      "runtime_minutes": 116,
      "runtime_display": "1h 56m",
      "poster_url": "https://image.tmdb.org/t/p/w500/example-2.jpg",
      "backdrop_url": "https://image.tmdb.org/t/p/original/example-2.jpg",
      "rating": 7.8,
      "popularity": 200.0,
      "language": "en",
      "status": "Released",
      "number_of_seasons": null,
      "number_of_episodes": null,
      "category_label": "Movies",
      "primary_genre": "Drama",
      "tmdb_url": "https://www.themoviedb.org/movie/329865",
      "has_trailer": true,
      "last_synced_at": "2026-08-15T11:00:00+00:00"
    }
  ],
  "attribution": {
    "source": "TMDB",
    "notice": "This product uses the TMDB API but is not endorsed or certified by TMDB.",
    "url": "https://www.themoviedb.org",
    "logo_url": "https://www.themoviedb.org/assets/...svg"
  }
}
```

Errors:

- `404` catalog item not found

## Phase 10 Endpoints

Phase 10 adds real catalog playback over legally usable sources. TMDB remains metadata-only; full playback is available only when the backend has at least one active `PlaybackSource` for the requested catalog item.

Playback behavior notes:

- `watch_action = "watch_now"` means the frontend should initialize a real player using `primary_source`
- `watch_action = "watch_trailer"` means no legal full playback source is configured, but an official trailer fallback is available
- `watch_action = "not_available"` means the UI must show a clear unavailable state instead of a fake or broken Watch button
- authenticated requests may include `watch_progress`; unauthenticated requests should treat it as `null`
- source types currently normalized by the backend are:
  - `hls`
  - `mp4`
  - `youtube`
  - `external`

### `GET /api/catalog/{slug}/playback`

Headers:

```text
Authorization: Bearer <token>
```

Notes:

- the `Authorization` header is optional
- when a valid token is present and the source supports progress reporting, the backend includes the user’s saved watch progress
- the frontend should prefer `primary_source` for default playback and may surface the additional `sources` array as optional alternatives

Success response `200`:

```json
{
  "content_id": 1,
  "slug": "movie-big-buck-bunny-10378",
  "title": "Big Buck Bunny",
  "playback_available": true,
  "watch_action": "watch_now",
  "message": "Legal playback is available for this title.",
  "primary_source": {
    "id": 10,
    "name": "Open HLS Stream",
    "type": "hls",
    "playback_url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
    "embed_url": null,
    "external_video_id": null,
    "quality": "auto",
    "language": "en",
    "is_primary": true,
    "provider_name": "Mux Test Streams",
    "provider_url": "https://test-streams.mux.dev/",
    "license_note": "Open Big Buck Bunny sample stream used for browser HLS playback testing.",
    "source_note": "Curated demo HLS source for legal playback validation.",
    "last_checked_at": "2026-08-17T08:10:00Z",
    "error": null,
    "capabilities": {
      "can_play": true,
      "can_pause": true,
      "can_seek": true,
      "can_report_progress": true,
      "can_fullscreen": true,
      "supports_seek": true,
      "supports_state_tracking": true
    }
  },
  "sources": [
    {
      "id": 10,
      "name": "Open HLS Stream",
      "type": "hls",
      "playback_url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
      "embed_url": null,
      "external_video_id": null,
      "quality": "auto",
      "language": "en",
      "is_primary": true,
      "provider_name": "Mux Test Streams",
      "provider_url": "https://test-streams.mux.dev/",
      "license_note": "Open Big Buck Bunny sample stream used for browser HLS playback testing.",
      "source_note": "Curated demo HLS source for legal playback validation.",
      "last_checked_at": "2026-08-17T08:10:00Z",
      "error": null,
      "capabilities": {
        "can_play": true,
        "can_pause": true,
        "can_seek": true,
        "can_report_progress": true,
        "can_fullscreen": true,
        "supports_seek": true,
        "supports_state_tracking": true
      }
    },
    {
      "id": 11,
      "name": "Open MP4 File",
      "type": "mp4",
      "playback_url": "https://example.com/big-buck-bunny.mp4",
      "embed_url": null,
      "external_video_id": null,
      "quality": "2160p",
      "language": "en",
      "is_primary": false,
      "provider_name": "Microsoft PlayReady Test Content",
      "provider_url": "https://learn.microsoft.com/playready/advanced/testcontent/playready-3x-test-content",
      "license_note": "Public Big Buck Bunny MP4 test asset documented by Microsoft.",
      "source_note": "Alternative HTML5 MP4 playback source for the demo.",
      "last_checked_at": "2026-08-17T08:10:00Z",
      "error": null,
      "capabilities": {
        "can_play": true,
        "can_pause": true,
        "can_seek": true,
        "can_report_progress": true,
        "can_fullscreen": true,
        "supports_seek": true,
        "supports_state_tracking": true
      }
    }
  ],
  "trailer": null,
  "fallback": null,
  "watch_progress": {
    "watch_position_seconds": 84,
    "total_watched_duration_seconds": 120,
    "is_completed": false,
    "last_watched_at": "2026-08-17T08:20:00Z"
  }
}
```

Trailer-fallback response example:

```json
{
  "content_id": 22,
  "slug": "movie-arrival-329865",
  "title": "Arrival",
  "playback_available": false,
  "watch_action": "watch_trailer",
  "message": "A legal full playback source is not configured, but an official trailer is available.",
  "primary_source": null,
  "sources": [],
  "trailer": {
    "name": "Official Trailer",
    "site": "YouTube",
    "type": "Trailer",
    "official": true,
    "published_at": "2026-08-17T08:00:00Z",
    "embed_url": "https://www.youtube.com/embed/arrivalkey"
  },
  "fallback": {
    "type": "watch_trailer",
    "label": "Watch Trailer",
    "message": "Official trailer playback is available for this title.",
    "embed_url": "https://www.youtube.com/embed/arrivalkey"
  },
  "watch_progress": null
}
```

Unavailable response example:

```json
{
  "content_id": 42,
  "slug": "movie-dune-part-two-693134",
  "title": "Dune: Part Two",
  "playback_available": false,
  "watch_action": "not_available",
  "message": "This title is not currently available for in-app playback.",
  "primary_source": null,
  "sources": [],
  "trailer": null,
  "fallback": {
    "type": "not_available",
    "label": "Not Available for Playback",
    "message": "No legal full playback source is currently configured for this title.",
    "embed_url": null
  },
  "watch_progress": null
}
```

Errors:

- `404` catalog item not found

## Phase 6 Endpoints

Phase 6 adds semantic search and personalized recommendations over real catalog and upcoming live EPG data. Both endpoints return real existing content only; no fictional items are generated.

### `POST /api/search/semantic`

Request:

```json
{
  "query": "Find a science documentary about space tonight.",
  "limit": 8,
  "window_hours": 6
}
```

Notes:

- `limit` defaults to `12` and is capped at `30`
- `window_hours` is optional and can be used to bias or constrain live-program retrieval windows
- `Authorization: Bearer <token>` is optional. When present, the backend can lightly personalize ranking with saved interests and preferred categories.

Success response `200`:

```json
{
  "query": "Find a science documentary about space tonight.",
  "embedding_enabled": true,
  "applied_filters": [
    "prioritize live and upcoming EPG results",
    "category hints: Documentary, Science Fiction"
  ],
  "results": [
    {
      "id": "epg:4:xmltv:space-lab-2026-08-15T20:00:00Z",
      "result_type": "live_program",
      "score": 0.8193,
      "explanation": "Upcoming on Science World TV.",
      "title": "Space Lab: AI on Mars",
      "description": "A science documentary about space missions and artificial intelligence.",
      "category_label": "Live TV",
      "genres": ["Documentary"],
      "language": "en",
      "runtime_minutes": 90,
      "runtime_display": "90m",
      "year": null,
      "release_date": null,
      "rating": null,
      "popularity": null,
      "poster_url": "https://example.com/channel-logo.jpg",
      "backdrop_url": "https://example.com/channel-thumb.jpg",
      "content_slug": null,
      "channel": {
        "id": 4,
        "slug": "science-world-tv",
        "name": "Science World TV",
        "logo_url": "https://example.com/channel-logo.jpg",
        "source_type": "hls"
      },
      "availability": {
        "kind": "upcoming_live",
        "starts_at": "2026-08-15T20:00:00Z",
        "ends_at": "2026-08-15T21:30:00Z",
        "label": "Sat 20:00"
      }
    },
    {
      "id": "movie-journey-to-space-1",
      "result_type": "movie",
      "score": 0.7311,
      "explanation": "Strong semantic match for your query.",
      "title": "Journey to Space",
      "description": "A science documentary about space exploration and the cosmos.",
      "category_label": "Movies",
      "genres": ["Documentary", "Science Fiction"],
      "language": "en",
      "runtime_minutes": 95,
      "runtime_display": "1h 35m",
      "year": 2024,
      "release_date": null,
      "rating": 8.0,
      "popularity": 120.0,
      "poster_url": "https://example.com/poster.jpg",
      "backdrop_url": "https://example.com/backdrop.jpg",
      "content_slug": "movie-journey-to-space-1",
      "channel": null,
      "availability": {
        "kind": "vod",
        "starts_at": null,
        "ends_at": null,
        "label": "On demand"
      }
    }
  ]
}
```

Errors:

- `400` invalid request body
- `401` missing or invalid token

### `GET /api/recommendations`

Headers:

```text
Authorization: Bearer <token>
```

Query parameters:

- `limit` optional integer `1..30`, default `12`
- `window_hours` optional integer `1..72` to control how far ahead live programs should be considered

Success response `200`:

```json
{
  "generated_at": "2026-08-15T18:30:00Z",
  "embedding_enabled": true,
  "profile_summary": [
    "Preferred categories: Documentary, Technology",
    "Interests: Artificial Intelligence, Space",
    "Frequent genres: Documentary, Science Fiction"
  ],
  "results": [
    {
      "id": "epg:4:xmltv:ai-tonight",
      "result_type": "live_program",
      "score": 0.8441,
      "explanation": "Live tonight and matches your Documentary preference.",
      "title": "AI Tonight",
      "description": "Live technology documentary coverage about robotics and space.",
      "category_label": "Live TV",
      "genres": ["Documentary"],
      "language": "en",
      "runtime_minutes": 90,
      "runtime_display": "90m",
      "year": null,
      "release_date": null,
      "rating": null,
      "popularity": null,
      "poster_url": "https://example.com/channel-logo.jpg",
      "backdrop_url": "https://example.com/channel-thumb.jpg",
      "content_slug": null,
      "channel": {
        "id": 4,
        "slug": "science-world-tv",
        "name": "Science World TV",
        "logo_url": "https://example.com/channel-logo.jpg",
        "source_type": "hls"
      },
      "availability": {
        "kind": "upcoming_live",
        "starts_at": "2026-08-15T20:00:00Z",
        "ends_at": "2026-08-15T21:30:00Z",
        "label": "Sat 20:00"
      }
    },
    {
      "id": "movie-deep-space-machines-4",
      "result_type": "movie",
      "score": 0.7812,
      "explanation": "Similar to Journey to Space.",
      "title": "Deep Space Machines",
      "description": "A technology documentary about AI systems for space travel.",
      "category_label": "Movies",
      "genres": ["Documentary", "Science Fiction"],
      "language": "en",
      "runtime_minutes": 104,
      "runtime_display": "1h 44m",
      "year": 2024,
      "release_date": null,
      "rating": 8.0,
      "popularity": 180.0,
      "poster_url": "https://example.com/poster.jpg",
      "backdrop_url": "https://example.com/backdrop.jpg",
      "content_slug": "movie-deep-space-machines-4",
      "channel": null,
      "availability": {
        "kind": "vod",
        "starts_at": null,
        "ends_at": null,
        "label": "On demand"
      }
    }
  ]
}
```

Errors:

- `401` missing or invalid token

## Phase 7 Endpoints

Phase 7 adds a Gemini-powered personalized viewing planner. The planner only uses real candidates that already exist in the database; Gemini does not invent content, channels, or broadcast times.

### `POST /api/viewing-plans/generate`

Headers:

```text
Authorization: Bearer <token>
```

Request:

```json
{
  "plan_date": "2026-08-17",
  "available_start": "19:00:00",
  "available_end": "23:00:00",
  "timezone": "Europe/Istanbul",
  "max_duration_minutes": 180,
  "preferred_categories": ["Documentary", "Technology"],
  "include_live": true,
  "include_vod": true,
  "preference_text": "Use live TV first, then add something about science or AI."
}
```

Notes:

- `plan_date` cannot be in the past. Because the current date is `2026-08-16`, a date like `2026-08-15` is invalid, while `2026-08-17` is valid.
- `max_duration_minutes` is optional, but when provided it cannot exceed the requested availability window.
- At least one of `include_live` or `include_vod` must be `true`.
- The backend will validate Gemini output and may fall back deterministically if the LLM output is invalid or unavailable.

Success response `201`:

```json
{
  "id": 7,
  "plan_date": "2026-08-17",
  "timezone": "Europe/Istanbul",
  "available_start": "2026-08-17T16:00:00Z",
  "available_end": "2026-08-17T20:00:00Z",
  "max_duration_minutes": 180,
  "include_live": true,
  "include_vod": true,
  "preferred_categories": ["Documentary", "Technology"],
  "preference_text": "Use live TV first, then add something about science or AI.",
  "profile_summary": [
    "Preferred categories: Documentary, Technology",
    "Interests: Artificial Intelligence, Space"
  ],
  "summary": "Start with a live technology bulletin, then continue with a science documentary.",
  "generation_source": "gemini",
  "llm_model": "gemini-3.6-flash",
  "llm_repair_applied": false,
  "items": [
    {
      "id": 31,
      "candidate_id": "epg:4:xmltv:ai-tonight-2026-08-17T16:00:00Z",
      "result_type": "live_program",
      "title": "AI Tonight",
      "description": "Live technology documentary coverage about robotics and space.",
      "category_label": "Live TV",
      "genres": ["Documentary"],
      "runtime_minutes": 60,
      "runtime_display": "60m",
      "planned_start": "2026-08-17T16:00:00Z",
      "planned_end": "2026-08-17T17:00:00Z",
      "availability_start": "2026-08-17T16:00:00Z",
      "availability_end": "2026-08-17T17:00:00Z",
      "recommendation_score": 0.8441,
      "reason": "Start with the live science bulletin while it is available.",
      "poster_url": "https://example.com/channel-logo.jpg",
      "backdrop_url": "https://example.com/channel-thumb.jpg",
      "content_slug": null,
      "channel": {
        "id": 4,
        "slug": "science-world-tv",
        "name": "Science World TV",
        "logo_url": "https://example.com/channel-logo.jpg",
        "source_type": "hls"
      }
    },
    {
      "id": 32,
      "candidate_id": "catalog:movie-journey-to-space-1",
      "result_type": "movie",
      "title": "Journey to Space",
      "description": "A science documentary about space exploration and the cosmos.",
      "category_label": "Movies",
      "genres": ["Documentary", "Science Fiction"],
      "runtime_minutes": 120,
      "runtime_display": "2h",
      "planned_start": "2026-08-17T17:00:00Z",
      "planned_end": "2026-08-17T19:00:00Z",
      "availability_start": null,
      "availability_end": null,
      "recommendation_score": 0.7812,
      "reason": "Continue with a high-signal documentary that matches your technology interests.",
      "poster_url": "https://example.com/poster.jpg",
      "backdrop_url": "https://example.com/backdrop.jpg",
      "content_slug": "movie-journey-to-space-1",
      "channel": null
    }
  ],
  "created_at": "2026-08-16T13:05:00Z",
  "updated_at": "2026-08-16T13:05:00Z"
}
```

Errors:

- `400` invalid request body
- `401` missing or invalid token
- `404` no real candidates available for the requested window

### `GET /api/viewing-plans`

Headers:

```text
Authorization: Bearer <token>
```

Success response `200`:

```json
{
  "items": [
    {
      "id": 7,
      "plan_date": "2026-08-17",
      "timezone": "Europe/Istanbul",
      "available_start": "2026-08-17T16:00:00Z",
      "available_end": "2026-08-17T20:00:00Z",
      "max_duration_minutes": 180,
      "include_live": true,
      "include_vod": true,
      "preferred_categories": ["Documentary", "Technology"],
      "preference_text": "Use live TV first, then add something about science or AI.",
      "profile_summary": [
        "Preferred categories: Documentary, Technology"
      ],
      "summary": "Start with a live technology bulletin, then continue with a science documentary.",
      "generation_source": "gemini",
      "llm_model": "gemini-3.6-flash",
      "llm_repair_applied": false,
      "items": [],
      "created_at": "2026-08-16T13:05:00Z",
      "updated_at": "2026-08-16T13:05:00Z"
    }
  ]
}
```

Errors:

- `401` missing or invalid token

### `GET /api/viewing-plans/{id}`

Headers:

```text
Authorization: Bearer <token>
```

Success response `200`:

- Same shape as `POST /api/viewing-plans/generate`

Errors:

- `401` missing or invalid token
- `404` viewing plan not found

## Phase 8 Endpoints

Phase 8 adds a grounded, context-aware AI assistant. It is not a generic chatbot: every request must point to the currently viewed catalog title, live channel, or EPG program that already exists in the backend.

### `POST /api/assistant/chat`

Headers:

```text
Authorization: Bearer <token>
```

Request for a catalog title:

```json
{
  "message": "What is this title about and who are the main contributors?",
  "context_type": "catalog",
  "content_slug": "movie-journey-to-space-1"
}
```

Request for the currently viewed live program:

```json
{
  "message": "What can you confirm about this program right now?",
  "context_type": "program",
  "epg_entry_id": 41
}
```

Notes:

- `context_type` must be one of `catalog`, `channel`, or `program`.
- `content_slug` is required for `catalog`.
- `channel_id` is required for `channel`.
- `epg_entry_id` is required for `program`.
- The assistant only answers from trusted backend context. It must not invent scenes, speakers, or live-broadcast moments.
- When transcript-level context is unavailable, the backend will clearly limit the answer to metadata/guide information.

Success response `200`:

```json
{
  "answer": "Journey to Space is a science documentary about space exploration and future missions. The trusted metadata also identifies the main cast and director-level contributors that were indexed with the title.",
  "limitation_note": null,
  "grounded": true,
  "used_rag": true,
  "generation_source": "gemini",
  "model": "gemini-3.6-flash",
  "context": {
    "context_type": "catalog",
    "title": "Journey to Space",
    "description": "A science documentary about space exploration and the cosmos.",
    "category_label": "Movies",
    "content_slug": "movie-journey-to-space-1",
    "channel_id": null,
    "epg_entry_id": null,
    "channel_name": null,
    "live_status": null,
    "current_program_title": null,
    "next_program_title": null,
    "has_transcript": false,
    "metadata_only": false
  },
  "sources": [
    {
      "chunk_id": "catalog-overview:movie-journey-to-space-1",
      "source_type": "catalog_metadata",
      "title": "Journey to Space overview",
      "snippet": "A science documentary about space exploration and future missions."
    },
    {
      "chunk_id": "catalog-credits:movie-journey-to-space-1",
      "source_type": "credits_metadata",
      "title": "Journey to Space credits",
      "snippet": "Top cast: Lead Actor. Top crew: Director."
    }
  ],
  "follow_up_questions": [
    "Who are the main contributors?",
    "What genres define this title?"
  ]
}
```

Example live-program response with explicit limitation:

```json
{
  "answer": "According to the guide metadata, AI Tonight is a live technology documentary coverage segment about robotics and space on Science World TV.",
  "limitation_note": "No trusted transcript or moment-by-moment live feed context is available right now, so this answer is limited to guide and channel metadata.",
  "grounded": true,
  "used_rag": true,
  "generation_source": "fallback",
  "model": null,
  "context": {
    "context_type": "program",
    "title": "AI Tonight",
    "description": "Live technology documentary coverage about robotics and space.",
    "category_label": "Documentary",
    "content_slug": null,
    "channel_id": 4,
    "epg_entry_id": 41,
    "channel_name": "Science World TV",
    "live_status": "live",
    "current_program_title": "AI Tonight",
    "next_program_title": "Space Bulletin",
    "has_transcript": false,
    "metadata_only": true
  },
  "sources": [
    {
      "chunk_id": "program-metadata:41",
      "source_type": "program_metadata",
      "title": "AI Tonight guide metadata",
      "snippet": "Program title: AI Tonight. Description: Live technology documentary coverage about robotics and space."
    }
  ],
  "follow_up_questions": [
    "What is this program about?",
    "What is on next on this channel?"
  ]
}
```

Errors:

- `400` invalid request body
- `401` missing or invalid token
- `404` content context could not be resolved

## Phase 11 Endpoints

Phase 11 adds authenticated Watch Party rooms with host-controlled playback synchronization and real-time room chat.

### `POST /api/watch-party/rooms`

Creates a new watch room for a playable catalog title or live channel.

Headers:

```text
Authorization: Bearer <token>
```

Request body:

```json
{
  "target_type": "catalog",
  "content_slug": "movie-big-buck-bunny-10378",
  "privacy": "invite_only"
}
```

Live-channel example:

```json
{
  "target_type": "channel",
  "channel_id": 4,
  "privacy": "invite_only"
}
```

Success response `201`:

```json
{
  "room": {
    "id": 1,
    "room_code": "AB12CD",
    "host_user_id": 7,
    "status": "active",
    "privacy": "invite_only",
    "playback_state": "paused",
    "current_position": 0.0,
    "authoritative_position": 0.0,
    "created_at": "2026-08-17T12:00:00Z",
    "updated_at": "2026-08-17T12:00:00Z"
  },
  "target": {
    "target_type": "catalog",
    "content_slug": "movie-big-buck-bunny-10378",
    "channel_id": null,
    "title": "Big Buck Bunny",
    "subtitle": "MOVIE • 2008",
    "poster_url": "https://example.com/poster.jpg",
    "backdrop_url": "https://example.com/backdrop.jpg",
    "live_status": null,
    "playback_supported": true
  },
  "role": "host",
  "joined": true,
  "invite_path": "#/watch-party/AB12CD",
  "websocket_url": "/api/watch-party/ws/AB12CD",
  "participants": [
    {
      "user_id": 7,
      "username": "host",
      "display_name": "Host User",
      "avatar_url": null,
      "is_host": true,
      "joined_at": "2026-08-17T12:00:00Z",
      "last_seen_at": "2026-08-17T12:00:00Z",
      "is_connected": false
    }
  ],
  "recent_messages": [],
  "host_reconnect_grace_seconds": 20
}
```

Errors:

- `401` missing or invalid token
- `404` room target not found
- `409` target is not available for synchronized playback

### `GET /api/watch-party/rooms/{room_code}`

Returns the current room metadata, participants, and recent chat history for an authenticated user.

Headers:

```text
Authorization: Bearer <token>
```

Notes:

- `joined = false` means the user can still join with the explicit join endpoint if the room is active
- `recent_messages` is only populated for active room members

### `POST /api/watch-party/rooms/{room_code}/join`

Joins the authenticated user to the room and returns the same response structure as room creation.

Headers:

```text
Authorization: Bearer <token>
```

Errors:

- `401` missing or invalid token
- `404` room not found
- `409` room is no longer active

### `POST /api/watch-party/rooms/{room_code}/leave`

Leaves the room as a participant.

Headers:

```text
Authorization: Bearer <token>
```

Success response `204` with an empty body.

Notes:

- if the host calls the leave action through REST, the backend ends the room
- the frontend should normally use `DELETE /api/watch-party/rooms/{room_code}` for an intentional host end-room action

### `DELETE /api/watch-party/rooms/{room_code}`

Ends the room. Host only.

Headers:

```text
Authorization: Bearer <token>
```

Success response `204` with an empty body.

Errors:

- `401` missing or invalid token
- `403` only the room host can end the room
- `404` room not found

## Phase 11 WebSocket Contract

### `WS /api/watch-party/ws/{room_code}?token=<jwt>`

The WebSocket connection requires the JWT as a query parameter. The server validates the token before accepting the socket and only allows active room members to connect.

Close codes used by the backend:

- `4401` authentication required or invalid token
- `4403` user is not a room member
- `4404` room not found
- `4409` room is not active
- `4002` room ended or expired

### Client → Server Events

#### `SYNC_REQUEST`

```json
{
  "type": "SYNC_REQUEST"
}
```

#### `PLAY`

```json
{
  "type": "PLAY",
  "position": 625.4
}
```

#### `PAUSE`

```json
{
  "type": "PAUSE",
  "position": 742.1
}
```

#### `SEEK`

```json
{
  "type": "SEEK",
  "position": 900.0
}
```

#### `CHAT_MESSAGE`

```json
{
  "type": "CHAT_MESSAGE",
  "message": "This scene is great"
}
```

#### `CONTENT_CHANGE`

Host-only room target switch:

```json
{
  "type": "CONTENT_CHANGE",
  "target_type": "catalog",
  "content_slug": "movie-big-buck-bunny-10378"
}
```

Notes:

- only the host may emit `PLAY`, `PAUSE`, `SEEK`, or `CONTENT_CHANGE`
- participants may emit `SYNC_REQUEST` and `CHAT_MESSAGE`
- all positions are seconds from the logical start of the room target

### Server → Client Events

#### `ROOM_STATE`

Initial room snapshot when a socket connects.

```json
{
  "type": "ROOM_STATE",
  "room": {
    "id": 1,
    "room_code": "AB12CD",
    "host_user_id": 7,
    "status": "active",
    "privacy": "invite_only",
    "playback_state": "playing",
    "current_position": 625.4,
    "authoritative_position": 628.1,
    "created_at": "2026-08-17T12:00:00Z",
    "updated_at": "2026-08-17T12:10:00Z"
  },
  "target": {
    "target_type": "catalog",
    "content_slug": "movie-big-buck-bunny-10378",
    "channel_id": null,
    "title": "Big Buck Bunny",
    "subtitle": "MOVIE • 2008",
    "poster_url": "https://example.com/poster.jpg",
    "backdrop_url": "https://example.com/backdrop.jpg",
    "live_status": null,
    "playback_supported": true
  },
  "participants": [],
  "recent_messages": [],
  "server_timestamp": "2026-08-17T12:10:03Z",
  "drift_threshold_seconds": 1.5
}
```

#### `USER_JOINED` / `USER_LEFT`

```json
{
  "type": "USER_JOINED",
  "participant": {
    "user_id": 11,
    "username": "guest",
    "display_name": "Guest User",
    "avatar_url": null,
    "is_host": false,
    "joined_at": "2026-08-17T12:02:00Z",
    "last_seen_at": "2026-08-17T12:10:03Z",
    "is_connected": true
  },
  "server_timestamp": "2026-08-17T12:10:03Z"
}
```

#### `PLAY` / `PAUSE` / `SEEK`

```json
{
  "type": "SEEK",
  "room_code": "AB12CD",
  "playback_state": "playing",
  "authoritative_position": 900.0,
  "server_timestamp": "2026-08-17T12:14:00Z",
  "participant": {
    "user_id": 7,
    "username": "host",
    "display_name": "Host User",
    "avatar_url": null,
    "is_host": true,
    "joined_at": "2026-08-17T12:00:00Z",
    "last_seen_at": "2026-08-17T12:14:00Z",
    "is_connected": true
  }
}
```

#### `SYNC_STATE`

```json
{
  "type": "SYNC_STATE",
  "room_code": "AB12CD",
  "playback_state": "playing",
  "authoritative_position": 900.8,
  "server_timestamp": "2026-08-17T12:14:04Z",
  "drift_threshold_seconds": 1.5
}
```

#### `CHAT_MESSAGE`

```json
{
  "type": "CHAT_MESSAGE",
  "message": {
    "id": 33,
    "user_id": 11,
    "username": "guest",
    "display_name": "Guest User",
    "avatar_url": null,
    "message_text": "This scene is great",
    "created_at": "2026-08-17T12:15:00Z"
  },
  "server_timestamp": "2026-08-17T12:15:00Z"
}
```

#### `ROOM_ENDED`

```json
{
  "type": "ROOM_ENDED",
  "room_code": "AB12CD",
  "message": "The host ended the room.",
  "server_timestamp": "2026-08-17T12:20:00Z"
}
```

#### `ERROR`

```json
{
  "type": "ERROR",
  "code": "room_event_rejected",
  "message": "Only the room host can control shared playback."
}
```

Behavior notes:

- the backend is authoritative for room membership, playback state, and chat persistence
- clients must not trust self-supplied `user_id` values
- the frontend should suppress event loops when applying remote playback events
- seek correction should happen only when drift exceeds the threshold provided by the server
- live/non-seekable sources should follow play/pause state and perform best-effort current-position sync rather than constant forced seeks

## Phase 12 Endpoints

Phase 12 renames the user-facing "AI Planner" to "My Channel" and adds an equivalent API surface under `/api/my-channel` that adapts the existing Phase 7 `ViewingPlannerService` rather than duplicating it. `/api/viewing-plans/*` keeps working unchanged; a plan created through either path is visible through both (same underlying storage).

### `POST /api/my-channel/generate`

Headers, request body, validation rules, and response shape are identical to `POST /api/viewing-plans/generate` (see Phase 7). Success response `201`, same `ViewingPlanRead` shape.

### `GET /api/my-channel`

Identical to `GET /api/viewing-plans` - lists the authenticated user's saved plans (most recent first).

### `GET /api/my-channel/{plan_id}`

Identical to `GET /api/viewing-plans/{id}`.

## Reserved for Future Phases

- `/api/programs`
- `/api/categories`
- `/api/vod`
- `/api/social`
