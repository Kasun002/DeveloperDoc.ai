"""
Dependency injection for FastAPI endpoints.

This module provides dependency functions for database sessions and other
shared resources used across API endpoints.
"""

from typing import Generator

from app.core.database import SessionLocal
from app.core.security import decode_jwt_token
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

# HTTP Bearer token security scheme
security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function that provides a database session.

    Yields a SQLAlchemy session and ensures it's closed after use.
    Used for dependency injection in FastAPI endpoints.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """
    Dependency function that extracts and validates access token from Authorization header.

    Extracts the JWT token from the Authorization header, validates its signature
    and expiration, and returns the user_id from the token payload.

    Args:
        credentials: HTTP Bearer credentials from Authorization header

    Returns:
        int: User ID from the token payload

    Raises:
        HTTPException 401: If token is missing, invalid, or expired
    """
    token = credentials.credentials

    try:
        # Decode and validate the token
        payload = decode_jwt_token(token)

        # Extract user_id from payload
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing user_id",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify it's an access token (not a refresh token)
        token_type = payload.get("type")
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: expected access token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user_id

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
