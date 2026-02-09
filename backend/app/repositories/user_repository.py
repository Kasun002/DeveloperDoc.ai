"""
User repository for database operations.

This module provides the UserRepository class for managing user data
in the database. It follows the repository pattern to separate data
access logic from business logic.
"""

from typing import Optional

from app.models.user import User
from sqlalchemy.orm import Session


class UserRepository:
    """
    Repository for User model database operations.

    Handles all database queries and mutations for the User model,
    providing a clean interface for the service layer.
    """

    def __init__(self, db: Session):
        """
        Initialize the repository with a database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_user(self, email: str, password_hash: str) -> User:
        """
        Create a new user in the database.

        Args:
            email: User's email address (must be unique)
            password_hash: Bcrypt hashed password

        Returns:
            User: The created user object

        Raises:
            IntegrityError: If email already exists
        """
        user = User(email=email, password_hash=password_hash, is_active=True)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by email address.

        Args:
            email: Email address to search for

        Returns:
            User | None: User object if found, None otherwise
        """
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Retrieve a user by ID.

        Args:
            user_id: User's primary key ID

        Returns:
            User | None: User object if found, None otherwise
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def update_password(self, user_id: int, password_hash: str) -> bool:
        """
        Update a user's password hash.

        Args:
            user_id: User's primary key ID
            password_hash: New bcrypt hashed password

        Returns:
            bool: True if update succeeded, False if user not found
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.password_hash = password_hash
        self.db.commit()
        return True

    def user_exists(self, email: str) -> bool:
        """
        Check if a user with the given email exists.

        Args:
            email: Email address to check

        Returns:
            bool: True if user exists, False otherwise
        """
        return self.db.query(User).filter(User.email == email).first() is not None
