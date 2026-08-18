from datetime import date, datetime, timezone

import pytest
from starlette.websockets import WebSocketDisconnect

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


def _create_playable_catalog_item(db_session):
    item = CatalogItem(
        slug="movie-big-buck-bunny-10378",
        content_type="movie",
        tmdb_id=10378,
        title="Big Buck Bunny",
        original_title="Big Buck Bunny",
        overview="A giant rabbit gets even.",
        release_date=date(2008, 4, 10),
        runtime_minutes=10,
        poster_url="https://example.com/bunny-poster.jpg",
        backdrop_url="https://example.com/bunny-backdrop.jpg",
        vote_average=7.3,
        popularity=44.2,
        original_language="en",
        status="Released",
        top_cast=[],
        top_crew=["Blender Foundation"],
        tmdb_url="https://www.themoviedb.org/movie/10378",
        is_active=True,
        last_synced_at=datetime(2026, 8, 17, 8, 0, tzinfo=timezone.utc),
    )
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


def _create_room(client, token: str, slug: str) -> str:
    response = client.post(
        "/api/watch-party/rooms",
        headers={"Authorization": f"Bearer {token}"},
        json={"target_type": "catalog", "content_slug": slug},
    )
    assert response.status_code == 201
    return response.json()["room"]["room_code"]


def _join_room(client, token: str, room_code: str) -> None:
    response = client.post(
        f"/api/watch-party/rooms/{room_code}/join",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_websocket_requires_authentication(client, db_session):
    item = _create_playable_catalog_item(db_session)
    token = _register_user(client, username="host", email="host@example.com")
    room_code = _create_room(client, token, item.slug)

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/watch-party/ws/{room_code}") as websocket:
            websocket.receive_json()


def test_websocket_rejects_non_member(client, db_session):
    item = _create_playable_catalog_item(db_session)
    host_token = _register_user(client, username="host", email="host@example.com")
    outsider_token = _register_user(client, username="outsider", email="outsider@example.com")
    room_code = _create_room(client, host_token, item.slug)

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/watch-party/ws/{room_code}?token={outsider_token}") as websocket:
            websocket.receive_json()


def test_host_play_pause_seek_and_chat_broadcast(client, db_session):
    item = _create_playable_catalog_item(db_session)
    host_token = _register_user(client, username="host", email="host@example.com")
    guest_token = _register_user(client, username="guest", email="guest@example.com")
    room_code = _create_room(client, host_token, item.slug)
    _join_room(client, guest_token, room_code)

    with client.websocket_connect(f"/api/watch-party/ws/{room_code}?token={host_token}") as host_ws:
        host_state = host_ws.receive_json()
        assert host_state["type"] == "ROOM_STATE"
        with client.websocket_connect(f"/api/watch-party/ws/{room_code}?token={guest_token}") as guest_ws:
            guest_state = guest_ws.receive_json()
            assert guest_state["type"] == "ROOM_STATE"
            joined_event = host_ws.receive_json()
            assert joined_event["type"] == "USER_JOINED"
            assert joined_event["participant"]["username"] == "guest"

            host_ws.send_json({"type": "PLAY", "position": 12.5})
            host_play = host_ws.receive_json()
            guest_play = guest_ws.receive_json()
            assert host_play["type"] == "PLAY"
            assert guest_play["type"] == "PLAY"
            assert guest_play["playback_state"] == "playing"
            assert guest_play["authoritative_position"] >= 12.5

            host_ws.send_json({"type": "PAUSE", "position": 18.0})
            assert host_ws.receive_json()["type"] == "PAUSE"
            pause_payload = guest_ws.receive_json()
            assert pause_payload["type"] == "PAUSE"
            assert pause_payload["playback_state"] == "paused"

            host_ws.send_json({"type": "SEEK", "position": 24.0})
            assert host_ws.receive_json()["type"] == "SEEK"
            seek_payload = guest_ws.receive_json()
            assert seek_payload["type"] == "SEEK"
            assert seek_payload["authoritative_position"] == 24.0

            guest_ws.send_json({"type": "CHAT_MESSAGE", "message": "This scene is great"})
            host_chat = host_ws.receive_json()
            guest_chat = guest_ws.receive_json()
            assert host_chat["type"] == "CHAT_MESSAGE"
            assert guest_chat["type"] == "CHAT_MESSAGE"
            assert guest_chat["message"]["message_text"] == "This scene is great"


def test_participant_control_rejected_and_invalid_payload_returns_error(client, db_session):
    item = _create_playable_catalog_item(db_session)
    host_token = _register_user(client, username="host", email="host@example.com")
    guest_token = _register_user(client, username="guest", email="guest@example.com")
    room_code = _create_room(client, host_token, item.slug)
    _join_room(client, guest_token, room_code)

    with client.websocket_connect(f"/api/watch-party/ws/{room_code}?token={host_token}") as host_ws:
        host_ws.receive_json()
        with client.websocket_connect(f"/api/watch-party/ws/{room_code}?token={guest_token}") as guest_ws:
            guest_ws.receive_json()
            host_ws.receive_json()

            guest_ws.send_json({"type": "PLAY", "position": 4})
            rejection = guest_ws.receive_json()
            assert rejection["type"] == "ERROR"
            assert rejection["code"] == "room_event_rejected"

            guest_ws.send_json({"type": "PLAY"})
            invalid = guest_ws.receive_json()
            assert invalid["type"] == "ERROR"
            assert invalid["code"] == "invalid_payload"


def test_sync_request_and_disconnect_flow(client, db_session):
    item = _create_playable_catalog_item(db_session)
    host_token = _register_user(client, username="host", email="host@example.com")
    guest_token = _register_user(client, username="guest", email="guest@example.com")
    room_code = _create_room(client, host_token, item.slug)
    _join_room(client, guest_token, room_code)

    with client.websocket_connect(f"/api/watch-party/ws/{room_code}?token={host_token}") as host_ws:
        host_ws.receive_json()
        with client.websocket_connect(f"/api/watch-party/ws/{room_code}?token={guest_token}") as guest_ws:
            guest_ws.receive_json()
            host_ws.receive_json()

            host_ws.send_json({"type": "PLAY", "position": 31})
            host_ws.receive_json()
            guest_ws.receive_json()

            guest_ws.send_json({"type": "SYNC_REQUEST"})
            sync_payload = guest_ws.receive_json()
            assert sync_payload["type"] == "SYNC_STATE"
            assert sync_payload["playback_state"] == "playing"
            assert sync_payload["authoritative_position"] >= 31

            guest_ws.close()
            left_event = host_ws.receive_json()
            assert left_event["type"] == "USER_LEFT"
            assert left_event["participant"]["username"] == "guest"


def test_host_disconnect_ends_room_after_grace_period(client, db_session):
    item = _create_playable_catalog_item(db_session)
    host_token = _register_user(client, username="host", email="host@example.com")
    guest_token = _register_user(client, username="guest", email="guest@example.com")
    room_code = _create_room(client, host_token, item.slug)
    _join_room(client, guest_token, room_code)

    with client.websocket_connect(f"/api/watch-party/ws/{room_code}?token={host_token}") as host_ws:
        host_ws.receive_json()
        with client.websocket_connect(f"/api/watch-party/ws/{room_code}?token={guest_token}") as guest_ws:
            guest_ws.receive_json()
            host_ws.receive_json()

            host_ws.close()
            left_event = guest_ws.receive_json()
            assert left_event["type"] == "USER_LEFT"
            ended_event = guest_ws.receive_json()
            assert ended_event["type"] == "ROOM_ENDED"
            assert ended_event["room_code"] == room_code
