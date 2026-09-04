def registration_payload(**overrides):
    payload = {
        "username": "doga",
        "email": "doga@example.com",
        "password": "StrongPass123",
        "display_name": "Doga",
        "avatar_url": "https://example.com/avatar.png",
        "interests": ["AI", "Sports"],
        "preferred_categories": ["Technology", "Documentary"],
    }
    payload.update(overrides)
    return payload


def register_and_login(client, **overrides):
    response = client.post("/api/auth/register", json=registration_payload(**overrides))
    assert response.status_code == 201
    data = response.json()
    return data["access_token"], data["user"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_favorites_can_be_added_listed_and_removed(client):
    token, _ = register_and_login(client)

    add_response = client.post("/api/users/me/favorites/movie-123", headers=auth_header(token))
    assert add_response.status_code == 200
    assert add_response.json()["content_id"] == "movie-123"

    list_response = client.get("/api/users/me/favorites", headers=auth_header(token))
    assert list_response.status_code == 200
    assert [item["content_id"] for item in list_response.json()] == ["movie-123"]

    remove_response = client.delete("/api/users/me/favorites/movie-123", headers=auth_header(token))
    assert remove_response.status_code == 204

    list_after_delete = client.get("/api/users/me/favorites", headers=auth_header(token))
    assert list_after_delete.json() == []


def test_favorites_are_private_per_user(client):
    token_one, _ = register_and_login(client)
    token_two, _ = register_and_login(
        client,
        username="rumeysa",
        email="rumeysa@example.com",
    )

    client.post("/api/users/me/favorites/series-99", headers=auth_header(token_one))

    response_user_one = client.get("/api/users/me/favorites", headers=auth_header(token_one))
    response_user_two = client.get("/api/users/me/favorites", headers=auth_header(token_two))

    assert [item["content_id"] for item in response_user_one.json()] == ["series-99"]
    assert response_user_two.json() == []


def test_removing_unknown_favorite_returns_404(client):
    token, _ = register_and_login(client)

    response = client.delete("/api/users/me/favorites/missing-item", headers=auth_header(token))

    assert response.status_code == 404
    assert response.json()["detail"] == "Favorite not found."


def test_history_is_upserted_and_listed(client):
    token, _ = register_and_login(client)

    first_response = client.post(
        "/api/users/me/history",
        headers=auth_header(token),
        json={
            "content_id": "program-7",
            "content_type": "program",
            "watch_position_seconds": 120,
            "total_watched_duration_seconds": 600,
            "is_completed": False,
        },
    )
    assert first_response.status_code == 200
    assert first_response.json()["content_type"] == "program"

    second_response = client.post(
        "/api/users/me/history",
        headers=auth_header(token),
        json={
            "content_id": "program-7",
            "content_type": "program",
            "watch_position_seconds": 480,
            "total_watched_duration_seconds": 1200,
            "is_completed": True,
        },
    )
    assert second_response.status_code == 200
    assert second_response.json()["watch_position_seconds"] == 480
    assert second_response.json()["is_completed"] is True

    history_response = client.get("/api/users/me/history", headers=auth_header(token))
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["content_id"] == "program-7"
    assert history[0]["total_watched_duration_seconds"] == 1200


def test_history_is_private_per_user(client):
    token_one, _ = register_and_login(client)
    token_two, _ = register_and_login(
        client,
        username="naz",
        email="naz@example.com",
    )

    client.post(
        "/api/users/me/history",
        headers=auth_header(token_one),
        json={
            "content_id": "movie-2",
            "watch_position_seconds": 30,
            "total_watched_duration_seconds": 90,
            "is_completed": False,
        },
    )

    response_user_one = client.get("/api/users/me/history", headers=auth_header(token_one))
    response_user_two = client.get("/api/users/me/history", headers=auth_header(token_two))

    assert len(response_user_one.json()) == 1
    assert response_user_two.json() == []


def test_profile_patch_updates_interest_and_categories(client):
    token, _ = register_and_login(client)

    response = client.patch(
        "/api/users/me/profile",
        headers=auth_header(token),
        json={
            "display_name": "Doga Yucel",
            "interests": ["Semantic Search", "Cinema"],
            "preferred_categories": ["Drama", "Technology"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["display_name"] == "Doga Yucel"
    assert data["profile"]["interests"] == ["Semantic Search", "Cinema"]
    assert data["profile"]["preferred_categories"] == ["Drama", "Technology"]


def test_profile_patch_persists_preset_avatar(client):
    token, user = register_and_login(client)
    assert user["profile"]["avatar_url"] == "https://example.com/avatar.png"

    response = client.patch(
        "/api/users/me/profile",
        headers=auth_header(token),
        json={"avatar_url": "preset:aurora"},
    )
    assert response.status_code == 200
    assert response.json()["profile"]["avatar_url"] == "preset:aurora"

    # A follow-up save that omits the avatar must not wipe it.
    client.patch(
        "/api/users/me/profile",
        headers=auth_header(token),
        json={"display_name": "Renamed"},
    )
    me_response = client.get("/api/auth/me", headers=auth_header(token))
    assert me_response.status_code == 200
    assert me_response.json()["profile"]["avatar_url"] == "preset:aurora"


def test_profile_patch_rejects_invalid_avatar_reference(client):
    token, _ = register_and_login(client)

    response = client.patch(
        "/api/users/me/profile",
        headers=auth_header(token),
        json={"avatar_url": "javascript:alert(1)"},
    )
    assert response.status_code in {400, 422}


def test_personalization_endpoints_require_authentication(client):
    favorites_response = client.get("/api/users/me/favorites")
    history_response = client.get("/api/users/me/history")
    profile_response = client.patch("/api/users/me/profile", json={"display_name": "Anon"})

    assert favorites_response.status_code == 401
    assert history_response.status_code == 401
    assert profile_response.status_code == 401
