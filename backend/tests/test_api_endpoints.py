"""
Integration tests for API endpoints.

Tests the authentication API endpoints to ensure they work correctly
with proper request/response handling and status codes.
"""

import pytest
from app.core.dependencies import get_db
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client(db_session):
    """Create test client with database session override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_register_endpoint(client):
    """Test POST /api/auth/register endpoint."""
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "TestPass123"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "password_hash" not in data
    assert data["is_active"] is True


def test_register_duplicate_email(client):
    """Test registration with duplicate email returns 409."""
    # Register first user
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "TestPass123"},
    )

    # Try to register with same email
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "DifferentPass456"},
    )

    assert response.status_code == 409
    assert "already registered" in response.json()["detail"].lower()


def test_register_weak_password(client):
    """Test registration with weak password returns 422."""
    response = client.post(
        "/api/auth/register", json={"email": "test@example.com", "password": "short"}
    )

    assert response.status_code == 422


def test_login_endpoint(client):
    """Test POST /api/auth/login endpoint."""
    # Register user first
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "TestPass123"},
    )

    # Login
    response = client.post(
        "/api/auth/login", json={"email": "test@example.com", "password": "TestPass123"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client):
    """Test login with invalid credentials returns 401."""
    response = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "WrongPass123"},
    )

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_change_password_endpoint(client):
    """Test POST /api/auth/change-password endpoint."""
    # Register and login
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "OldPass123"},
    )

    login_response = client.post(
        "/api/auth/login", json={"email": "test@example.com", "password": "OldPass123"}
    )
    access_token = login_response.json()["access_token"]

    # Change password
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "OldPass123", "new_password": "NewPass456"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert "success" in response.json()["message"].lower()


def test_change_password_without_auth(client):
    """Test change password without authentication returns 401."""
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "OldPass123", "new_password": "NewPass456"},
    )

    assert response.status_code == 401  # No credentials provided


def test_change_password_wrong_current(client):
    """Test change password with wrong current password returns 400."""
    # Register and login
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "OldPass123"},
    )

    login_response = client.post(
        "/api/auth/login", json={"email": "test@example.com", "password": "OldPass123"}
    )
    access_token = login_response.json()["access_token"]

    # Try to change with wrong current password
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "WrongPass999", "new_password": "NewPass456"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 400
    assert "incorrect" in response.json()["detail"].lower()


def test_password_reset_request_endpoint(client):
    """Test POST /api/auth/reset-password/request endpoint."""
    # Register user
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "TestPass123"},
    )

    # Request password reset
    response = client.post(
        "/api/auth/reset-password/request", json={"email": "test@example.com"}
    )

    assert response.status_code == 200
    assert "token" in response.json()["message"].lower()


def test_password_reset_confirm_endpoint(client):
    """Test POST /api/auth/reset-password/confirm endpoint."""
    # Register user
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "OldPass123"},
    )

    # Request reset
    reset_response = client.post(
        "/api/auth/reset-password/request", json={"email": "test@example.com"}
    )

    # Extract token from message (in production, this would be sent via email)
    message = reset_response.json()["message"]
    token = message.split("Token: ")[1]

    # Confirm reset
    response = client.post(
        "/api/auth/reset-password/confirm",
        json={"token": token, "new_password": "NewPass456"},
    )

    assert response.status_code == 200
    assert "success" in response.json()["message"].lower()


def test_refresh_token_endpoint(client):
    """Test POST /api/auth/refresh endpoint."""
    # Register and login
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "TestPass123"},
    )

    login_response = client.post(
        "/api/auth/login", json={"email": "test@example.com", "password": "TestPass123"}
    )
    refresh_token = login_response.json()["refresh_token"]

    # Refresh access token
    response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_with_invalid_token(client):
    """Test refresh with invalid token returns 401."""
    response = client.post(
        "/api/auth/refresh", json={"refresh_token": "invalid.token.here"}
    )

    assert response.status_code == 401
