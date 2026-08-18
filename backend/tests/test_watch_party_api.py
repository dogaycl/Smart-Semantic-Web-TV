from datetime import date, datetime, timezone

from app.models.catalog_item import CatalogItem
from app.models.playback_source import PlaybackSource


def _register_user(client, *, username: str, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "StrongPass123",
            "display_name": username.title(),
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _create_playable_catalog_item(db_session, **overrides):
    payload = {
        "slug": "movie-big-buck-bunny-10378",
        "content_type": "movie",
        "tmdb_id": 10378,
        "title": "Big Buck Bunny",
        "original_title": "Big Buck Bunny",
        "overview": "A giant rabbit gets even.",
        "release_date": date(2008, 4, 10),
        "runtime_minutes": 10,
        "poster_url": "https://example.com/bunny-poster.jpg",
        "backdrop_url": "https://example.com/bunny-backdrop.jpg",
        "vote_average": 7.3,
        "popularity": 44.2,
        "original_language": "en",
        "status": "Released",
        "top_cast": [],
        "top_crew": ["Blender Foundation"],
        "tmdb_url": "https://www.themoviedb.org/movie/10378",
        "is_active": True,
        "last_synced_at": datetime(2026, 8, 17, 8, 0, tzinfo=timezone.utc),
    }
    payload.update(overrides)
    item = CatalogItem(**payload)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    db_session.add(
        PlaybackSource(
            content_item_id=item.id,
            name="Open HLS Stream",
            source_type="hls",
            playback_url="https://example.com/bunny.m3u8",
            quality="auto",
            is_primary=True,
            is_active=True,
            provider_name="Mux Test Streams",
            provider_url="https://test-streams.mux.dev/",
            last_checked_at=datetime(2026, 8, 17, 8, 5, tzinfo=timezone.utc),
        )
    )
    db_session.commit()
    return item


def test_watch_room_creation_returns_invite_and_host_membership(client, db_session):
    item = _create_playable_catalog_item(db_session)
    token = _register_user(client, username="host", email="host@example.com")

    response = client.post(
        "/api/watch-party/rooms",
        headers={"Authorization": f"Bearer {token}"},
        json={"target_type": "catalog", "content_slug": item.slug},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["joined"] is True
    assert payload["role"] == "host"
    assert payload["room"]["status"] == "active"
    assert payload["room"]["playback_state"] == "paused"
    assert payload["target"]["content_slug"] == item.slug
    assert payload["invite_path"].startswith("#/watch-party/")
    assert payload["websocket_url"].endswith(payload["room"]["room_code"])
    assert payload["participants"][0]["username"] == "host"
    assert payload["participants"][0]["is_host"] is True


def test_watch_room_join_marks_participant_joined(client, db_session):
    item = _create_playable_catalog_item(db_session)
    host_token = _register_user(client, username="host", email="host@example.com")
    guest_token = _register_user(client, username="guest", email="guest@example.com")
    create_response = client.post(
        "/api/watch-party/rooms",
        headers={"Authorization": f"Bearer {host_token}"},
        json={"target_type": "catalog", "content_slug": item.slug},
    )
    room_code = create_response.json()["room"]["room_code"]

    response = client.post(
        f"/api/watch-party/rooms/{room_code}/join",
        headers={"Authorization": f"Bearer {guest_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["joined"] is True
    assert payload["role"] == "participant"
    assert len(payload["participants"]) == 2
    assert {entry["username"] for entry in payload["participants"]} == {"host", "guest"}


def test_watch_room_invalid_room_returns_404(client):
    token = _register_user(client, username="guest", email="guest@example.com")

    response = client.get(
        "/api/watch-party/rooms/ZZZZZZ",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Watch room not found."


def test_watch_room_requires_playable_target(client, db_session):
    item = CatalogItem(
        slug="movie-arrival-329865",
        content_type="movie",
        tmdb_id=329865,
        title="Arrival",
        original_title="Arrival",
        overview="A linguist works with the military.",
        release_date=date(2016, 11, 10),
        runtime_minutes=116,
        poster_url="https://example.com/arrival-poster.jpg",
        backdrop_url="https://example.com/arrival-backdrop.jpg",
        vote_average=7.8,
        popularity=200.0,
        original_language="en",
        status="Released",
        top_cast=[],
        top_crew=["Denis Villeneuve"],
        tmdb_url="https://www.themoviedb.org/movie/329865",
        is_active=True,
        last_synced_at=datetime(2026, 8, 17, 8, 0, tzinfo=timezone.utc),
    )
    db_session.add(item)
    db_session.commit()
    token = _register_user(client, username="host", email="host@example.com")

    response = client.post(
        "/api/watch-party/rooms",
        headers={"Authorization": f"Bearer {token}"},
        json={"target_type": "catalog", "content_slug": item.slug},
    )

    assert response.status_code == 409
    assert "not available for synchronized playback" in response.json()["detail"]
