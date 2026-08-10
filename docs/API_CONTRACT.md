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

## Reserved for Future Phases

- `/api/channels`
- `/api/programs`
- `/api/categories`
- `/api/epg`
- `/api/vod`
- `/api/recommendations`
- `/api/search`
- `/api/assistant`

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
