from datetime import date, datetime, timezone

from app.api.routers import catalog as catalog_router
from app.models.catalog_item import CatalogItem
from app.models.catalog_video import CatalogVideo
from app.models.playback_source import PlaybackSource


def _freeze_sync(monkeypatch):
    monkeypatch.setattr(catalog_router.sync_service, "ensure_ready", lambda **kwargs: None)
    monkeypatch.setattr(catalog_router.playback_sync_service, "ensure_ready", lambda **kwargs: None)


def _register_and_login(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "doga",
            "email": "doga@example.com",
            "password": "StrongPass123",
            "display_name": "Doga",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _create_catalog_item(db_session, **overrides):
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
        "top_crew": ["Sacha Goedegebure"],
        "tmdb_url": "https://www.themoviedb.org/movie/10378",
        "is_active": True,
        "last_synced_at": datetime(2026, 8, 17, 8, 0, tzinfo=timezone.utc),
    }
    payload.update(overrides)
    item = CatalogItem(**payload)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def test_playback_endpoint_returns_real_source_and_progress(client, db_session, monkeypatch):
    _freeze_sync(monkeypatch)
    item = _create_catalog_item(db_session)
    db_session.add_all(
        [
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
            ),
            PlaybackSource(
                content_item_id=item.id,
                name="Official Blender Embed",
                source_type="external",
                playback_url="https://video.blender.org/videos/embed/pAQiVCgv2CsLg79KKXUoMw",
                embed_url="https://video.blender.org/videos/embed/pAQiVCgv2CsLg79KKXUoMw",
                supports_seek=False,
                supports_state_tracking=False,
                is_active=True,
                provider_name="Blender Video",
                provider_url="https://video.blender.org/videos/watch/bf1f3fb5-b119-4f9f-9930-8e20e892b898",
            ),
        ]
    )
    db_session.commit()

    token = _register_and_login(client)
    history_response = client.post(
        "/api/users/me/history",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "content_id": item.slug,
            "content_type": "content",
            "watch_position_seconds": 84,
            "total_watched_duration_seconds": 120,
            "is_completed": False,
        },
    )
    assert history_response.status_code == 200

    response = client.get(
        f"/api/catalog/{item.slug}/playback",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["playback_available"] is True
    assert payload["watch_action"] == "watch_now"
    assert payload["primary_source"]["type"] == "hls"
    assert payload["primary_source"]["capabilities"]["can_seek"] is True
    assert len(payload["sources"]) == 2
    assert payload["watch_progress"]["watch_position_seconds"] == 84


def test_playback_endpoint_supports_youtube_sources(client, db_session, monkeypatch):
    _freeze_sync(monkeypatch)
    item = _create_catalog_item(
        db_session,
        slug="movie-tears-of-steel-133701",
        tmdb_id=133701,
        title="Tears of Steel",
        original_title="Tears of Steel",
        release_date=date(2012, 9, 26),
        runtime_minutes=12,
        tmdb_url="https://www.themoviedb.org/movie/133701",
    )
    db_session.add(
        PlaybackSource(
            content_item_id=item.id,
            name="Official YouTube Upload",
            source_type="youtube",
            external_video_id="41hv2tW5Lc4",
            is_primary=True,
            is_active=True,
            provider_name="Blender Foundation YouTube",
            provider_url="https://youtu.be/41hv2tW5Lc4",
        )
    )
    db_session.commit()

    response = client.get(f"/api/catalog/{item.slug}/playback")

    assert response.status_code == 200
    payload = response.json()
    assert payload["playback_available"] is True
    assert payload["primary_source"]["type"] == "youtube"
    assert payload["primary_source"]["external_video_id"] == "41hv2tW5Lc4"
    assert payload["primary_source"]["embed_url"] == "https://www.youtube.com/embed/41hv2tW5Lc4"


def test_playback_endpoint_ignores_invalid_optional_token(client, db_session, monkeypatch):
    _freeze_sync(monkeypatch)
    item = _create_catalog_item(db_session)
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
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/catalog/{item.slug}/playback",
        headers={"Authorization": "Bearer expired-or-invalid-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["playback_available"] is True
    assert payload["watch_progress"] is None


def test_playback_endpoint_falls_back_to_trailer_when_full_source_is_missing(client, db_session, monkeypatch):
    _freeze_sync(monkeypatch)
    item = _create_catalog_item(
        db_session,
        slug="movie-arrival-329865",
        tmdb_id=329865,
        title="Arrival",
        original_title="Arrival",
        runtime_minutes=116,
        tmdb_url="https://www.themoviedb.org/movie/329865",
    )
    db_session.add(
        CatalogVideo(
            content_item_id=item.id,
            tmdb_video_id="arrival-trailer",
            name="Official Trailer",
            site="YouTube",
            type="Trailer",
            video_key="arrivalkey",
            official=True,
        )
    )
    db_session.commit()

    response = client.get(f"/api/catalog/{item.slug}/playback")

    assert response.status_code == 200
    payload = response.json()
    assert payload["playback_available"] is False
    assert payload["watch_action"] == "watch_trailer"
    assert payload["primary_source"] is None
    assert payload["fallback"]["type"] == "watch_trailer"
    assert payload["fallback"]["embed_url"] == "https://www.youtube.com/embed/arrivalkey"


def test_playback_endpoint_reports_not_available_when_no_legal_source_exists(client, db_session, monkeypatch):
    _freeze_sync(monkeypatch)
    item = _create_catalog_item(
        db_session,
        slug="movie-dune-part-two-693134",
        tmdb_id=693134,
        title="Dune: Part Two",
        original_title="Dune: Part Two",
        runtime_minutes=166,
        tmdb_url="https://www.themoviedb.org/movie/693134",
    )

    response = client.get(f"/api/catalog/{item.slug}/playback")

    assert response.status_code == 200
    payload = response.json()
    assert payload["playback_available"] is False
    assert payload["watch_action"] == "not_available"
    assert payload["fallback"]["type"] == "not_available"
