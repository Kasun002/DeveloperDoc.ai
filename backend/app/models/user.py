"""
User and PasswordResetToken models for authentication system.

This module defines the SQLAlchemy ORM models for users and password reset tokens.
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship


class User(Base):
    """
    User model representing a registered user in the system.

    Attributes:
        id: Primary key, auto-incrementing integer
        email: Unique email address for the user
        password_hash: Bcrypt hashed password (never store plain text)
        is_active: Whether the user account is active
        created_at: Timestamp when the user was created
        updated_at: Timestamp when the user was last updated
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    reset_tokens = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, is_active={self.is_active})>"


class PasswordResetToken(Base):
    """
    PasswordResetToken model for managing password reset requests.

    Attributes:
        id: Primary key, auto-incrementing integer
        user_id: Foreign key to the users table
        token: Unique token string for password reset
        expires_at: Timestamp when the token expires
        created_at: Timestamp when the token was created
        used: Whether the token has been used
    """

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="reset_tokens")

    def __repr__(self):
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, used={self.used})>"


# Create indexes for performance
Index("idx_users_email", User.email, unique=True)
Index("idx_password_reset_tokens_token", PasswordResetToken.token, unique=True)
