"""
Integration tests for AuthService.

These tests verify that the AuthService works correctly with the
database and all its dependencies.
"""

import pytest
from app.models.user import User
from app.services.auth_service import AuthService
from sqlalchemy.orm import Session


def test_register_and_authenticate_user(db_session: Session):
    """Test user registration and authentication flow."""
    service = AuthService(db_session)

    # Register a new user
    email = "test@example.com"
    password = "SecurePass123"

    user = service.register_user(email, password)

    assert user is not None
    assert user.email == email
    assert user.password_hash != password  # Password should be hashed
    assert user.is_active is True

    # Authenticate with correct credentials
    authenticated_user = service.authenticate_user(email, password)
    assert authenticated_user is not None
    assert authenticated_user.id == user.id

    # Authenticate with wrong password
    wrong_auth = service.authenticate_user(email, "WrongPassword123")
    assert wrong_auth is None


def test_duplicate_email_registration(db_session: Session):
    """Test that duplicate email registration is rejected."""
    service = AuthService(db_session)

    email = "duplicate@example.com"
    password = "SecurePass123"

    # Register first user
    service.register_user(email, password)

    # Try to register with same email
    with pytest.raises(ValueError, match="Email already registered"):
        service.register_user(email, password)


def test_weak_password_rejected(db_session: Session):
    """Test that weak passwords are rejected."""
    service = AuthService(db_session)

    email = "weak@example.com"

    # Too short
    with pytest.raises(ValueError, match="at least 8 characters"):
        service.register_user(email, "short1")

    # No numbers
    with pytest.raises(ValueError, match="letters and numbers"):
        service.register_user(email, "NoNumbers")

    # No letters
    with pytest.raises(ValueError, match="letters and numbers"):
        service.register_user(email, "12345678")


def test_create_and_verify_tokens(db_session: Session):
    """Test token creation and verification."""
    service = AuthService(db_session)

    # Register a user
    user = service.register_user("token@example.com", "SecurePass123")

    # Create access token
    access_token = service.create_access_token(user.id)
    assert access_token is not None
    assert len(access_token) > 0

    # Create refresh token
    refresh_token = service.create_refresh_token(user.id)
    assert refresh_token is not None
    assert len(refresh_token) > 0

    # Verify access token
    access_payload = service.verify_token(access_token)
    assert access_payload["user_id"] == user.id
    assert access_payload["type"] == "access"
    assert "exp" in access_payload
    assert "iat" in access_payload

    # Verify refresh token
    refresh_payload = service.verify_token(refresh_token)
    assert refresh_payload["user_id"] == user.id
    assert refresh_payload["type"] == "refresh"


def test_change_password(db_session: Session):
    """Test password change functionality."""
    service = AuthService(db_session)

    # Register a user
    email = "change@example.com"
    old_password = "OldPass123"
    new_password = "NewPass456"

    user = service.register_user(email, old_password)

    # Change password with correct current password
    success = service.change_password(user.id, old_password, new_password)
    assert success is True

    # Verify old password no longer works
    auth_old = service.authenticate_user(email, old_password)
    assert auth_old is None

    # Verify new password works
    auth_new = service.authenticate_user(email, new_password)
    assert auth_new is not None
    assert auth_new.id == user.id


def test_change_password_wrong_current(db_session: Session):
    """Test that password change fails with wrong current password."""
    service = AuthService(db_session)

    # Register a user
    user = service.register_user("wrong@example.com", "OldPass123")

    # Try to change password with wrong current password
    with pytest.raises(ValueError, match="Current password is incorrect"):
        service.change_password(user.id, "WrongPass123", "NewPass456")


def test_password_reset_flow(db_session: Session):
    """Test complete password reset flow."""
    service = AuthService(db_session)

    # Register a user
    email = "reset@example.com"
    old_password = "OldPass123"
    new_password = "NewPass456"

    user = service.register_user(email, old_password)

    # Request password reset
    reset_token = service.request_password_reset(email)
    assert reset_token is not None
    assert len(reset_token) > 0

    # Confirm password reset with valid token
    success = service.confirm_password_reset(reset_token, new_password)
    assert success is True

    # Verify old password no longer works
    auth_old = service.authenticate_user(email, old_password)
    assert auth_old is None

    # Verify new password works
    auth_new = service.authenticate_user(email, new_password)
    assert auth_new is not None

    # Try to reuse the same token (should fail)
    with pytest.raises(ValueError, match="Invalid or expired reset token"):
        service.confirm_password_reset(reset_token, "AnotherPass789")


def test_password_reset_invalid_token(db_session: Session):
    """Test that invalid reset tokens are rejected."""
    service = AuthService(db_session)

    # Try to reset with invalid token
    with pytest.raises(ValueError, match="Invalid or expired reset token"):
        service.confirm_password_reset("invalid_token_123", "NewPass456")


def test_refresh_access_token(db_session: Session):
    """Test refreshing access token with refresh token."""
    service = AuthService(db_session)

    # Register a user
    user = service.register_user("refresh@example.com", "SecurePass123")

    # Create refresh token
    refresh_token = service.create_refresh_token(user.id)

    # Use refresh token to get new access token
    new_access_token = service.refresh_access_token(refresh_token)
    assert new_access_token is not None
    assert len(new_access_token) > 0

    # Verify the new access token
    payload = service.verify_token(new_access_token)
    assert payload["user_id"] == user.id
    assert payload["type"] == "access"


def test_refresh_with_access_token_fails(db_session: Session):
    """Test that using access token for refresh fails."""
    service = AuthService(db_session)

    # Register a user
    user = service.register_user("wrongtype@example.com", "SecurePass123")

    # Create access token (not refresh token)
    access_token = service.create_access_token(user.id)

    # Try to use access token for refresh (should fail)
    with pytest.raises(ValueError, match="Invalid token type"):
        service.refresh_access_token(access_token)
