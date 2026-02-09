"""
Authentication service for user registration, login, and token management.

This module provides the AuthService class that implements business logic
for user authentication, including registration, login, token generation,
and password management.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings
from app.core.security import (
    create_jwt_token,
    decode_jwt_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.models.user import User
from app.repositories.password_reset_repository import PasswordResetTokenRepository
from app.repositories.user_repository import UserRepository
from jose import JWTError
from sqlalchemy.orm import Session


class AuthService:
    """
    Service class for authentication operations.

    Handles business logic for user registration, authentication,
    token generation, and password management. Uses repository pattern
    for data access.
    """

    def __init__(self, db: Session):
        """
        Initialize the authentication service.

        Args:
            db: SQLAlchemy database session for dependency injection
        """
        self.db = db
        self.user_repository = UserRepository(db)
        self.password_reset_repository = PasswordResetTokenRepository(db)

    def register_user(self, email: str, password: str) -> User:
        """
        Register a new user with email and password.

        This method:
        1. Validates password strength
        2. Checks if email already exists
        3. Hashes the password
        4. Creates the user in the database

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            User: The created user object

        Raises:
            ValueError: If password is weak or email already exists
        """
        # Validate password strength
        if not validate_password_strength(password):
            raise ValueError(
                "Password must be at least 8 characters long and contain "
                "both letters and numbers"
            )

        # Check if user already exists
        if self.user_repository.user_exists(email):
            raise ValueError("Email already registered")

        # Hash the password
        password_hash = hash_password(password)

        # Create the user
        user = self.user_repository.create_user(email, password_hash)

        return user

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password.

        Verifies the user's credentials and returns the user object
        if authentication succeeds.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            User | None: User object if authentication succeeds, None otherwise
        """
        # Get user by email
        user = self.user_repository.get_user_by_email(email)

        if not user:
            return None

        # Verify password
        if not verify_password(password, user.password_hash):
            return None

        # Check if user is active
        if not user.is_active:
            return None

        return user

    def create_access_token(self, user_id: int) -> str:
        """
        Generate a 30-minute access token for a user.

        The access token is a JWT containing the user_id and standard
        claims (exp, iat). It's used for authenticating API requests.

        Args:
            user_id: User's primary key ID

        Returns:
            str: Signed JWT access token
        """
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        token_data = {"user_id": user_id, "type": "access"}
        return create_jwt_token(token_data, expires_delta)

    def create_refresh_token(self, user_id: int) -> str:
        """
        Generate a 7-day refresh token for a user.

        The refresh token is a JWT containing the user_id and standard
        claims (exp, iat). It's used to obtain new access tokens without
        re-authentication.

        Args:
            user_id: User's primary key ID

        Returns:
            str: Signed JWT refresh token
        """
        expires_delta = timedelta(days=settings.refresh_token_expire_days)
        token_data = {"user_id": user_id, "type": "refresh"}
        return create_jwt_token(token_data, expires_delta)

    def verify_token(self, token: str) -> dict:
        """
        Decode and validate a JWT token.

        Verifies the token signature, expiration, and structure.

        Args:
            token: JWT token string

        Returns:
            dict: Token payload containing user_id and other claims

        Raises:
            JWTError: If token is invalid, expired, or tampered
        """
        try:
            payload = decode_jwt_token(token)
            return payload
        except JWTError as e:
            raise e

    def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> bool:
        """
        Change a user's password after verifying the current password.

        This method:
        1. Retrieves the user
        2. Verifies the current password
        3. Validates the new password strength
        4. Updates the password hash

        Args:
            user_id: User's primary key ID
            current_password: Current plain text password for verification
            new_password: New plain text password

        Returns:
            bool: True if password change succeeded, False otherwise

        Raises:
            ValueError: If current password is incorrect or new password is weak
        """
        # Get the user
        user = self.user_repository.get_user_by_id(user_id)
        if not user:
            return False

        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")

        # Validate new password strength
        if not validate_password_strength(new_password):
            raise ValueError(
                "New password must be at least 8 characters long and contain "
                "both letters and numbers"
            )

        # Hash and update the new password
        new_password_hash = hash_password(new_password)
        return self.user_repository.update_password(user_id, new_password_hash)

    def request_password_reset(self, email: str) -> str:
        """
        Generate a password reset token for a user.

        Creates a unique reset token with 1-hour expiration and stores
        it in the database associated with the user's account.

        Args:
            email: User's email address

        Returns:
            str: Reset token string (to be sent to user via email)

        Raises:
            ValueError: If user with email doesn't exist
        """
        # Get user by email
        user = self.user_repository.get_user_by_email(email)
        if not user:
            raise ValueError("User not found")

        # Generate a secure random token
        token = secrets.token_urlsafe(32)

        # Calculate expiration time (1 hour from now)
        expires_at = datetime.utcnow() + timedelta(
            hours=settings.password_reset_token_expire_hours
        )

        # Store the token in the database
        self.password_reset_repository.create_reset_token(
            user_id=user.id, token=token, expires_at=expires_at
        )

        return token

    def confirm_password_reset(self, token: str, new_password: str) -> bool:
        """
        Reset a user's password using a valid reset token.

        This method:
        1. Validates the reset token (checks expiration and used status)
        2. Validates the new password strength
        3. Updates the user's password
        4. Marks the token as used

        Args:
            token: Password reset token string
            new_password: New plain text password

        Returns:
            bool: True if password reset succeeded, False otherwise

        Raises:
            ValueError: If token is invalid or new password is weak
        """
        # Get valid token
        reset_token = self.password_reset_repository.get_valid_token(token)
        if not reset_token:
            raise ValueError("Invalid or expired reset token")

        # Validate new password strength
        if not validate_password_strength(new_password):
            raise ValueError(
                "New password must be at least 8 characters long and contain "
                "both letters and numbers"
            )

        # Hash and update the new password
        new_password_hash = hash_password(new_password)
        success = self.user_repository.update_password(
            reset_token.user_id, new_password_hash
        )

        if success:
            # Mark the token as used to prevent reuse
            self.password_reset_repository.mark_token_used(reset_token.id)

        return success

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Generate a new access token using a valid refresh token.

        Validates the refresh token and issues a new access token
        with the same user_id.

        Args:
            refresh_token: JWT refresh token string

        Returns:
            str: New access token

        Raises:
            ValueError: If refresh token is invalid or expired
        """
        try:
            # Decode and validate the refresh token
            payload = self.verify_token(refresh_token)

            # Verify it's a refresh token
            if payload.get("type") != "refresh":
                raise ValueError("Invalid token type")

            # Extract user_id
            user_id = payload.get("user_id")
            if not user_id:
                raise ValueError("Invalid token payload")

            # Verify user still exists and is active
            user = self.user_repository.get_user_by_id(user_id)
            if not user or not user.is_active:
                raise ValueError("User not found or inactive")

            # Generate new access token
            return self.create_access_token(user_id)

        except JWTError:
            raise ValueError("Invalid or expired refresh token")
