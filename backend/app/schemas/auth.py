"""
Authentication Pydantic schemas for request validation and response serialization.

This module defines all request and response schemas for the authentication API,
including field validators for email format and password strength.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Request schema for user registration.

    Validates email format and password strength requirements.
    """

    email: EmailStr = Field(
        ..., description="User's email address", examples=["user@example.com"]
    )
    password: str = Field(
        ...,
        min_length=8,
        description="User's password (minimum 8 characters, must contain letters and numbers)",
        examples=["SecurePass123"],
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets strength requirements.

        Password must:
        - Be at least 8 characters long (enforced by Field min_length)
        - Contain at least one letter
        - Contain at least one number

        Args:
            v: Password string to validate

        Returns:
            The validated password

        Raises:
            ValueError: If password doesn't meet requirements
        """
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"email": "newuser@example.com", "password": "SecurePassword123"}
            ]
        }
    }


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr = Field(
        ..., description="User's email address", examples=["user@example.com"]
    )
    password: str = Field(
        ..., description="User's password", examples=["SecurePass123"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{"email": "user@example.com", "password": "MyPassword123"}]
        }
    }


class ChangePasswordRequest(BaseModel):
    """Request schema for changing password (requires authentication)."""

    current_password: str = Field(
        ..., description="User's current password", examples=["OldPassword123"]
    )
    new_password: str = Field(
        ...,
        min_length=8,
        description="New password (minimum 8 characters, must contain letters and numbers)",
        examples=["NewPassword456"],
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate new password meets strength requirements.

        Password must:
        - Be at least 8 characters long (enforced by Field min_length)
        - Contain at least one letter
        - Contain at least one number

        Args:
            v: Password string to validate

        Returns:
            The validated password

        Raises:
            ValueError: If password doesn't meet requirements
        """
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("New password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("New password must contain at least one number")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "current_password": "OldPassword123",
                    "new_password": "NewSecurePassword456",
                }
            ]
        }
    }


class PasswordResetRequestSchema(BaseModel):
    """Request schema for initiating password reset."""

    email: EmailStr = Field(
        ...,
        description="Email address of the account to reset",
        examples=["user@example.com"],
    )

    model_config = {"json_schema_extra": {"examples": [{"email": "user@example.com"}]}}


class PasswordResetConfirmSchema(BaseModel):
    """Request schema for confirming password reset with token."""

    token: str = Field(
        ...,
        description="Password reset token received via email",
        examples=["abc123def456ghi789"],
    )
    new_password: str = Field(
        ...,
        min_length=8,
        description="New password (minimum 8 characters, must contain letters and numbers)",
        examples=["NewPassword789"],
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate new password meets strength requirements.

        Password must:
        - Be at least 8 characters long (enforced by Field min_length)
        - Contain at least one letter
        - Contain at least one number

        Args:
            v: Password string to validate

        Returns:
            The validated password

        Raises:
            ValueError: If password doesn't meet requirements
        """
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("New password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("New password must contain at least one number")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"token": "abc123def456ghi789", "new_password": "BrandNewPassword123"}
            ]
        }
    }


class RefreshTokenRequest(BaseModel):
    """Request schema for refreshing access token."""

    refresh_token: str = Field(
        ...,
        description="Valid refresh token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE3MDk4NTYwMDB9.signature"
                }
            ]
        }
    }


# Response Schemas


class UserResponse(BaseModel):
    """Response schema for user data.

    Note: password_hash is never included in responses for security.
    """

    id: int = Field(..., description="User's unique identifier", examples=[1])
    email: str = Field(
        ..., description="User's email address", examples=["user@example.com"]
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when user account was created",
        examples=["2024-01-15T10:30:00Z"],
    )
    is_active: bool = Field(
        ..., description="Whether the user account is active", examples=[True]
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "email": "user@example.com",
                    "created_at": "2024-01-15T10:30:00Z",
                    "is_active": True,
                }
            ]
        },
    }


class TokenResponse(BaseModel):
    """Response schema for authentication tokens."""

    access_token: str = Field(
        ...,
        description="JWT access token (30-minute expiration)",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token (7-day expiration)",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
        examples=["bearer"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE3MDk4NTYwMDB9.signature",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE3MTAzNjgwMDB9.signature",
                    "token_type": "bearer",
                }
            ]
        }
    }


class MessageResponse(BaseModel):
    """Generic response schema for success/error messages."""

    message: str = Field(
        ...,
        description="Human-readable message",
        examples=["Operation completed successfully"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"message": "Password changed successfully"},
                {"message": "Password reset email sent"},
            ]
        }
    }
