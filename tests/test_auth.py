import jwt

from app.core.config import settings
from tests.conftest import login


def test_login_and_me(client, regular_user):
    tokens = login(client, "user@example.com", "user123")
    response = client.get(
        "/api/auth/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == regular_user.email
    assert response.json()["id"] == str(regular_user.id)


def test_invalid_credentials(client, regular_user):
    response = client.post(
        "/api/auth/jwt/login",
        json={"email": "user@example.com", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_invalid_access_token(client):
    response = client.get(
        "/api/auth/users/me",
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_invalid_access_token_with_malformed_uuid_claim(client):
    token = jwt.encode(
        {
            "sub": "not-a-uuid",
            "jti": "test-jti",
            "sid": "test-session",
            "type": "access",
            "exp": 4102444800,
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response = client.get(
        "/api/auth/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_refresh_rotates_tokens(client, regular_user):
    tokens = login(client, "user@example.com", "user123")
    response = client.post(
        "/api/auth/jwt/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 200
    refreshed = response.json()
    assert refreshed["access_token"] != tokens["access_token"]
    assert refreshed["refresh_token"] != tokens["refresh_token"]


def test_logout_invalidates_current_access_token(client, regular_user):
    tokens = login(client, "user@example.com", "user123")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    logout_response = client.post("/api/auth/logout", headers=headers)
    me_response = client.get("/api/auth/users/me", headers=headers)

    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "ok"
    assert me_response.status_code == 401
    assert me_response.json()["error"]["code"] == "invalid_token"


def test_logout_invalidates_refresh_token(client, regular_user):
    tokens = login(client, "user@example.com", "user123")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    logout_response = client.post("/api/auth/logout", headers=headers)
    refresh_response = client.post(
        "/api/auth/jwt/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert logout_response.status_code == 200
    assert refresh_response.status_code == 401
    assert refresh_response.json()["error"]["code"] == "invalid_token"
