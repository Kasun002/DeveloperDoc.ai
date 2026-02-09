"""
Security utilities for password hashing and JWT token management.

This module provides functions for:
- Password hashing using bcrypt with configurable rounds
- Password verification with constant-time comparison
- Password strength validation
- JWT token creation and validation
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import bcrypt
from app.core.config import settings
from jose import JWTError, jwt

# ============================================================================
# Password Hashing Functions
# ============================================================================


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with configurable rounds.

    Bcrypt automatically generates a unique salt for each password,
    ensuring that the same password hashed twice produces different hashes.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password as a string (bcrypt hash includes salt)

    Security considerations:
    - Uses bcrypt with configurable rounds (default 12) for computational cost
    - Automatic unique salt generation per password
    - Resistant to rainbow table attacks
    """
    # Convert password to bytes
    password_bytes = password.encode("utf-8")

    # Generate salt with configured rounds
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)

    # Hash the password
    hashed = bcrypt.hashpw(password_bytes, salt)

    # Return as string for database storage
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Uses bcrypt's built-in constant-time comparison to prevent timing attacks.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise

    Security considerations:
    - Uses constant-time comparison to prevent timing attacks
    - Bcrypt automatically extracts salt from hashed password
    """
    try:
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")

        # bcrypt.checkpw performs constant-time comparison
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        # Return False for any errors (invalid hash format, etc.)
        return False


def validate_password_strength(password: str) -> bool:
    """
    Validate password meets minimum strength requirements.

    Requirements:
    - At least 8 characters long
    - Contains at least one letter (uppercase or lowercase)
    - Contains at least one number

    Args:
        password: Password to validate

    Returns:
        True if password meets requirements, False otherwise
    """
    # Check minimum length
    if len(password) < 8:
        return False

    # Check for at least one letter (uppercase or lowercase)
    if not re.search(r"[a-zA-Z]", password):
        return False

    # Check for at least one number
    if not re.search(r"\d", password):
        return False

    return True


# ============================================================================
# JWT Token Functions
# ============================================================================


def create_jwt_token(data: dict, expires_delta: timedelta) -> str:
    """
    Create a signed JWT token with expiration.

    The token includes:
    - user_id: User identification from the data dict
    - exp: Expiration timestamp
    - iat: Issued-at timestamp
    - Any additional claims from the data dict

    Args:
        data: Dictionary containing claims to encode (must include user_id)
        expires_delta: Time until token expiration

    Returns:
        Signed JWT token as a string

    Security considerations:
    - Uses HS256 or RS256 algorithm (configured in settings)
    - Secret key stored in environment variables
    - Includes expiration to limit token lifetime
    - Includes issued-at for token age verification
    """
    # Create a copy to avoid modifying the original
    to_encode = data.copy()

    # Calculate expiration time
    expire = datetime.utcnow() + expires_delta

    # Add standard JWT claims
    to_encode.update(
        {"exp": expire, "iat": datetime.utcnow()}  # Expiration time  # Issued at time
    )

    # Encode and sign the token
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.

    Validates:
    - Token signature
    - Token expiration
    - Token structure

    Args:
        token: JWT token string to decode

    Returns:
        Dictionary containing the token payload

    Raises:
        JWTError: If token is invalid, expired, or tampered

    Security considerations:
    - Verifies signature to detect tampering
    - Checks expiration to prevent use of old tokens
    - Uses constant-time comparison for signature verification
    """
    try:
        # Decode and verify the token
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        # Re-raise JWT errors for caller to handle
        raise e
