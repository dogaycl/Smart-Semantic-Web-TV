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

Playback contract:

- `playback.type = "hls"` means the frontend should play `playback.stream_url`
- `playback.type = "youtube"` means the frontend should render an official YouTube embed using `playback.embed_url`
- `playback.type = "unavailable"` means the frontend should show a clear unavailable state

### `GET /api/channels`

Query parameters:

- `start` optional ISO datetime used to resolve `current_program` and `next_program`
- `end` optional ISO datetime used with `start` to warm the EPG window

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
  "plan_date": "2026-08-15",
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

- `plan_date` cannot be in the past. For example, because the current date is `2026-08-15`, a date like `2026-08-14` is invalid.
- `max_duration_minutes` is optional, but when provided it cannot exceed the requested availability window.
- At least one of `include_live` or `include_vod` must be `true`.
- The backend will validate Gemini output and may fall back deterministically if the LLM output is invalid or unavailable.

Success response `201`:

```json
{
  "id": 7,
  "plan_date": "2026-08-15",
  "timezone": "Europe/Istanbul",
  "available_start": "2026-08-15T16:00:00Z",
  "available_end": "2026-08-15T20:00:00Z",
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
      "candidate_id": "epg:4:xmltv:ai-tonight-2026-08-15T16:00:00Z",
      "result_type": "live_program",
      "title": "AI Tonight",
      "description": "Live technology documentary coverage about robotics and space.",
      "category_label": "Live TV",
      "genres": ["Documentary"],
      "runtime_minutes": 60,
      "runtime_display": "60m",
      "planned_start": "2026-08-15T16:00:00Z",
      "planned_end": "2026-08-15T17:00:00Z",
      "availability_start": "2026-08-15T16:00:00Z",
      "availability_end": "2026-08-15T17:00:00Z",
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
      "planned_start": "2026-08-15T17:00:00Z",
      "planned_end": "2026-08-15T19:00:00Z",
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
  "created_at": "2026-08-15T13:05:00Z",
  "updated_at": "2026-08-15T13:05:00Z"
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
      "plan_date": "2026-08-15",
      "timezone": "Europe/Istanbul",
      "available_start": "2026-08-15T16:00:00Z",
      "available_end": "2026-08-15T20:00:00Z",
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
      "created_at": "2026-08-15T13:05:00Z",
      "updated_at": "2026-08-15T13:05:00Z"
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
## Reserved for Future Phases

- `/api/programs`
- `/api/categories`
- `/api/vod`
- `/api/assistant`
