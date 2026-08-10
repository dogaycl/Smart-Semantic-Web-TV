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


def test_register_returns_token_and_user_profile(client):
    response = client.post("/api/auth/register", json=registration_payload())

    assert response.status_code == 201
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["email"] == "doga@example.com"
    assert data["user"]["profile"]["display_name"] == "Doga"
    assert data["user"]["profile"]["interests"] == ["AI", "Sports"]
    assert "hashed_password" not in data["user"]


def test_register_rejects_duplicate_email(client):
    client.post("/api/auth/register", json=registration_payload())
    response = client.post(
        "/api/auth/register",
        json=registration_payload(username="another-user"),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email is already registered."


def test_register_validates_payload_with_400(client):
    response = client.post(
        "/api/auth/register",
        json=registration_payload(email="not-an-email", password="weak"),
    )

    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Validation error."
    assert data["errors"]


def test_login_returns_token_for_valid_credentials(client):
    client.post("/api/auth/register", json=registration_payload())
    response = client.post(
        "/api/auth/login",
        json={"email": "doga@example.com", "password": "StrongPass123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["user"]["username"] == "doga"


def test_login_rejects_invalid_credentials(client):
    client.post("/api/auth/register", json=registration_payload())
    response = client.post(
        "/api/auth/login",
        json={"email": "doga@example.com", "password": "WrongPassword1"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_me_returns_current_user_when_token_is_valid(client):
    register_response = client.post("/api/auth/register", json=registration_payload())
    token = register_response.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["username"] == "doga"


def test_me_requires_authentication(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication credentials were not provided."
