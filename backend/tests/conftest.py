"""
Pytest configuration and fixtures for tests.

This module provides shared fixtures and configuration for all tests in the
authentication backend. It sets up test environment variables and provides
database session fixtures with proper isolation.
"""

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add the app directory to the Python path
# This allows tests to import from the app module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up test environment variables.

    This fixture runs once per test session and automatically sets up
    required environment variables for testing. It ensures tests have
    valid configuration without requiring a .env file.

    Environment variables set:
    - JWT_SECRET_KEY: Test secret for JWT token signing
    - DATABASE_URL: Test database connection string
    """
    # Set test JWT secret if not already set
    # Using a fixed secret for reproducible tests
    if not os.environ.get("JWT_SECRET_KEY"):
        os.environ["JWT_SECRET_KEY"] = "test_secret_key_for_jwt_testing_12345678"

    # Set test database URL if not already set
    # Using SQLite for fast test execution
    if not os.environ.get("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "sqlite:///./test.db"


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test.

    This fixture provides an isolated database session for each test function.
    It uses an in-memory SQLite database for fast execution and ensures
    complete isolation between tests by creating and dropping tables for
    each test.

    Benefits:
    - Fast execution (in-memory database)
    - Complete isolation (fresh database per test)
    - No cleanup required (database destroyed after test)
    - No test pollution (each test starts with clean state)

    Yields:
        Session: SQLAlchemy database session for the test
    """
    from app.core.database import Base

    # Import models to ensure they're registered with Base.metadata
    from app.models.user import PasswordResetToken, User  # noqa: F401

    # Create an in-memory SQLite database
    # StaticPool ensures the same connection is reused (required for :memory:)
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables defined in the Base metadata
    Base.metadata.create_all(bind=engine)

    # Create a session factory and instantiate a session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        # Yield the session to the test
        yield session
    finally:
        # Cleanup: close the session and drop all tables
        session.close()
        Base.metadata.drop_all(bind=engine)
