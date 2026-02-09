"""
Password reset token repository for database operations.

This module provides the PasswordResetTokenRepository class for managing
password reset tokens in the database. It follows the repository pattern
to separate data access logic from business logic.
"""

from datetime import datetime
from typing import Optional

from app.models.user import PasswordResetToken
from sqlalchemy.orm import Session


class PasswordResetTokenRepository:
    """
    Repository for PasswordResetToken model database operations.

    Handles all database queries and mutations for the PasswordResetToken model,
    providing a clean interface for the service layer.
    """

    def __init__(self, db: Session):
        """
        Initialize the repository with a database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_reset_token(
        self, user_id: int, token: str, expires_at: datetime
    ) -> PasswordResetToken:
        """
        Create a new password reset token in the database.

        Args:
            user_id: ID of the user requesting password reset
            token: Unique token string for password reset
            expires_at: Timestamp when the token expires

        Returns:
            PasswordResetToken: The created token object

        Raises:
            IntegrityError: If token already exists (should be unique)
        """
        reset_token = PasswordResetToken(
            user_id=user_id, token=token, expires_at=expires_at, used=False
        )
        self.db.add(reset_token)
        self.db.commit()
        self.db.refresh(reset_token)
        return reset_token

    def get_valid_token(self, token: str) -> Optional[PasswordResetToken]:
        """
        Retrieve a valid (non-expired, unused) password reset token.

        This method checks both expiration and used status to ensure
        the token is still valid for password reset.

        Args:
            token: Token string to search for

        Returns:
            PasswordResetToken | None: Token object if valid, None otherwise
        """
        now = datetime.utcnow()
        return (
            self.db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.token == token,
                PasswordResetToken.used == False,
                PasswordResetToken.expires_at > now,
            )
            .first()
        )

    def mark_token_used(self, token_id: int) -> bool:
        """
        Mark a password reset token as used to prevent reuse.

        Args:
            token_id: Primary key ID of the token

        Returns:
            bool: True if update succeeded, False if token not found
        """
        token = (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.id == token_id)
            .first()
        )

        if not token:
            return False

        token.used = True
        self.db.commit()
        return True

    def delete_expired_tokens(self) -> int:
        """
        Delete all expired password reset tokens for cleanup.

        This method should be called periodically to clean up old tokens
        and maintain database hygiene.

        Returns:
            int: Number of tokens deleted
        """
        now = datetime.utcnow()
        deleted_count = (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.expires_at <= now)
            .delete()
        )
        self.db.commit()
        return deleted_count
