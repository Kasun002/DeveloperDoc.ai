"""
Tests for global exception handlers.

Validates that custom exceptions are properly mapped to HTTP status codes
and that error responses follow a consistent format without leaking sensitive data.
"""

import pytest
from app.core.exceptions import (
    AuthenticationError,
    EmailAlreadyExistsError,
    IncorrectPasswordError,
    InvalidResetTokenError,
    InvalidTokenError,
    WeakPasswordError,
)
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_authentication_error_returns_401():
    """Test that AuthenticationError returns 401 with proper format."""

    # Create a test endpoint that raises AuthenticationError
    @app.get("/test/auth-error")
    async def test_auth_error():
        raise AuthenticationError("Invalid credentials")

    response = client.get("/test/auth-error")
    assert response.status_code == 401
    assert "detail" in response.json()
    assert response.json()["detail"] == "Invalid credentials"


def test_invalid_token_error_returns_401():
    """Test that InvalidTokenError returns 401 with proper format."""

    @app.get("/test/token-error")
    async def test_token_error():
        raise InvalidTokenError("Token expired")

    response = client.get("/test/token-error")
    assert response.status_code == 401
    assert "detail" in response.json()
    assert response.json()["detail"] == "Token expired"


def test_weak_password_error_returns_422():
    """Test that WeakPasswordError returns 422 with validation format."""

    @app.get("/test/weak-password")
    async def test_weak_password():
        raise WeakPasswordError("Password must be at least 8 characters")

    response = client.get("/test/weak-password")
    assert response.status_code == 422
    assert "detail" in response.json()
    assert isinstance(response.json()["detail"], list)
    assert response.json()["detail"][0]["loc"] == ["body", "password"]


def test_email_exists_error_returns_409():
    """Test that EmailAlreadyExistsError returns 409 with proper format."""

    @app.get("/test/email-exists")
    async def test_email_exists():
        raise EmailAlreadyExistsError()

    response = client.get("/test/email-exists")
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


def test_invalid_reset_token_error_returns_400():
    """Test that InvalidResetTokenError returns 400 with proper format."""

    @app.get("/test/reset-token-error")
    async def test_reset_token_error():
        raise InvalidResetTokenError("Reset token has expired")

    response = client.get("/test/reset-token-error")
    assert response.status_code == 400
    assert "detail" in response.json()
    assert response.json()["detail"] == "Reset token has expired"


def test_incorrect_password_error_returns_400():
    """Test that IncorrectPasswordError returns 400 with proper format."""

    @app.get("/test/incorrect-password")
    async def test_incorrect_password():
        raise IncorrectPasswordError("Current password is incorrect")

    response = client.get("/test/incorrect-password")
    assert response.status_code == 400
    assert "detail" in response.json()
    assert response.json()["detail"] == "Current password is incorrect"


def test_general_exception_returns_500_sanitized():
    """Test that unexpected exceptions return 500 with sanitized message."""
    # Note: This test verifies that the general exception handler is registered
    # In a real scenario, the handler would catch unhandled exceptions
    # For testing purposes, we verify the handler exists and would work
    # Simulate an exception being caught
    import asyncio

    from app.main import general_exception_handler
    from fastapi import Request

    class MockRequest:
        pass

    exc = ValueError("Database connection string: postgresql://user:pass@host/db")
    response = asyncio.run(general_exception_handler(MockRequest(), exc))

    assert response.status_code == 500
    assert response.body.decode() == '{"detail":"An internal server error occurred"}'
    # Verify sensitive data is NOT in response
    assert b"postgresql" not in response.body
    assert b"password" not in response.body.lower()


def test_exception_with_empty_message_uses_default():
    """Test that exceptions with empty messages use default messages."""

    @app.get("/test/empty-auth-error")
    async def test_empty_auth_error():
        raise AuthenticationError("")

    response = client.get("/test/empty-auth-error")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication failed"
