"""
Tests for health check endpoint.

Validates that the health check endpoint correctly reports database connectivity status.
"""

import pytest
from app.core.database import Base
from app.core.dependencies import get_db
from app.main import app

# Import models so they're registered with Base.metadata
from app.models import user  # noqa: F401
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_health.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


def test_health_check_returns_200_when_healthy():
    """
    Test that health check endpoint returns 200 with healthy status
    when database is connected.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)

    try:
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
    finally:
        # Cleanup
        Base.metadata.drop_all(bind=engine)


def test_health_check_includes_correct_fields():
    """
    Test that health check response includes required fields.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)

    try:
        response = client.get("/health")

        data = response.json()
        assert "status" in data
        assert "database" in data
    finally:
        # Cleanup
        Base.metadata.drop_all(bind=engine)
