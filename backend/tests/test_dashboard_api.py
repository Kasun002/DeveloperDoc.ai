"""
Integration tests for Dashboard API endpoints.

These tests verify the dashboard API endpoints work correctly with
JWT authentication and proper request/response handling.
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


def test_get_dashboard_with_valid_token(client):
    """Test GET /api/dashboard with valid JWT token."""
    # Register and login to get token
    client.post(
        "/api/auth/register",
        json={"email": "dashboard@example.com", "password": "TestPass123"},
    )

    login_response = client.post(
        "/api/auth/login",
        json={"email": "dashboard@example.com", "password": "TestPass123"},
    )
    access_token = login_response.json()["access_token"]

    # Get dashboard with valid token
    response = client.get(
        "/api/dashboard", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "user_id" in data
    assert "email" in data
    assert "dashboard_data" in data
    assert "message" in data

    # Verify user data
    assert data["email"] == "dashboard@example.com"
    assert data["message"] == "Dashboard data retrieved successfully"

    # Verify dashboard data structure
    assert "summary" in data["dashboard_data"]
    assert "stats" in data["dashboard_data"]
    assert "recent_activity" in data["dashboard_data"]

    # Verify summary structure
    summary = data["dashboard_data"]["summary"]
    assert "total_logins" in summary
    assert "last_login" in summary
    assert "account_created" in summary
    assert summary["total_logins"] == 0
    assert summary["last_login"] is None


def test_get_dashboard_without_token(client):
    """Test GET /api/dashboard without authentication token."""
    response = client.get("/api/dashboard")

    assert response.status_code == 401
    assert "detail" in response.json()


def test_get_dashboard_with_invalid_token(client):
    """Test GET /api/dashboard with invalid JWT token."""
    response = client.get(
        "/api/dashboard", headers={"Authorization": "Bearer invalid.token.here"}
    )

    assert response.status_code == 401
    assert "detail" in response.json()


def test_get_dashboard_with_malformed_token(client):
    """Test GET /api/dashboard with malformed token."""
    response = client.get(
        "/api/dashboard", headers={"Authorization": "Bearer malformed"}
    )

    assert response.status_code == 401


def test_get_dashboard_with_expired_token(client):
    """Test GET /api/dashboard with expired token (simulated)."""
    # This test would require creating an expired token
    # For now, we test with an invalid token which has similar behavior
    response = client.get(
        "/api/dashboard",
        headers={
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid"
        },
    )

    assert response.status_code == 401


def test_get_dashboard_missing_bearer_prefix(client):
    """Test GET /api/dashboard with token missing Bearer prefix."""
    # Register and login
    client.post(
        "/api/auth/register",
        json={"email": "nobearer@example.com", "password": "TestPass123"},
    )

    login_response = client.post(
        "/api/auth/login",
        json={"email": "nobearer@example.com", "password": "TestPass123"},
    )
    access_token = login_response.json()["access_token"]

    # Try without Bearer prefix
    response = client.get("/api/dashboard", headers={"Authorization": access_token})

    assert response.status_code == 401


def test_get_dashboard_response_format(client):
    """Test that dashboard response has correct format and types."""
    # Register and login
    client.post(
        "/api/auth/register",
        json={"email": "format@example.com", "password": "TestPass123"},
    )

    login_response = client.post(
        "/api/auth/login",
        json={"email": "format@example.com", "password": "TestPass123"},
    )
    access_token = login_response.json()["access_token"]

    # Get dashboard
    response = client.get(
        "/api/dashboard", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify types
    assert isinstance(data["user_id"], int)
    assert isinstance(data["email"], str)
    assert isinstance(data["message"], str)
    assert isinstance(data["dashboard_data"], dict)
    assert isinstance(data["dashboard_data"]["summary"], dict)
    assert isinstance(data["dashboard_data"]["stats"], dict)
    assert isinstance(data["dashboard_data"]["recent_activity"], list)
    assert isinstance(data["dashboard_data"]["summary"]["total_logins"], int)


def test_get_dashboard_multiple_users(client):
    """Test that each user gets their own dashboard data."""
    # Register two users
    client.post(
        "/api/auth/register",
        json={"email": "user1@example.com", "password": "TestPass123"},
    )
    client.post(
        "/api/auth/register",
        json={"email": "user2@example.com", "password": "TestPass123"},
    )

    # Login as user1
    login1 = client.post(
        "/api/auth/login",
        json={"email": "user1@example.com", "password": "TestPass123"},
    )
    token1 = login1.json()["access_token"]

    # Login as user2
    login2 = client.post(
        "/api/auth/login",
        json={"email": "user2@example.com", "password": "TestPass123"},
    )
    token2 = login2.json()["access_token"]

    # Get dashboard for user1
    response1 = client.get(
        "/api/dashboard", headers={"Authorization": f"Bearer {token1}"}
    )

    # Get dashboard for user2
    response2 = client.get(
        "/api/dashboard", headers={"Authorization": f"Bearer {token2}"}
    )

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    # Verify each user gets their own data
    assert data1["email"] == "user1@example.com"
    assert data2["email"] == "user2@example.com"
    assert data1["user_id"] != data2["user_id"]


def test_get_dashboard_after_password_change(client):
    """Test dashboard access after password change."""
    # Register and login
    client.post(
        "/api/auth/register",
        json={"email": "pwchange@example.com", "password": "OldPass123"},
    )

    login_response = client.post(
        "/api/auth/login",
        json={"email": "pwchange@example.com", "password": "OldPass123"},
    )
    old_token = login_response.json()["access_token"]

    # Change password
    client.post(
        "/api/auth/change-password",
        json={"current_password": "OldPass123", "new_password": "NewPass456"},
        headers={"Authorization": f"Bearer {old_token}"},
    )

    # Old token should still work (JWT is stateless)
    # In production, you might want token blacklisting
    response = client.get(
        "/api/dashboard", headers={"Authorization": f"Bearer {old_token}"}
    )

    # Current implementation: old token still works
    assert response.status_code == 200
