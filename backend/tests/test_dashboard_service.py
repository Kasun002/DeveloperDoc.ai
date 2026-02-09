"""
Unit tests for DashboardService.

These tests verify the dashboard service business logic following SOLID principles.
Tests are isolated and use mocking where appropriate.
"""

from datetime import datetime

import pytest
from app.models.user import User
from app.services.dashboard_service import DashboardService
from sqlalchemy.orm import Session


def test_get_dashboard_data_success(db_session: Session):
    """Test successful dashboard data retrieval."""
    service = DashboardService(db_session)

    # Create a test user
    from app.services.auth_service import AuthService

    auth_service = AuthService(db_session)
    user = auth_service.register_user("dashboard@example.com", "TestPass123")

    # Get dashboard data
    dashboard_data = service.get_dashboard_data(user.id)

    # Verify response structure
    assert dashboard_data.user_id == user.id
    assert dashboard_data.email == "dashboard@example.com"
    assert dashboard_data.message == "Dashboard data retrieved successfully"

    # Verify dashboard data structure
    assert dashboard_data.dashboard_data is not None
    assert dashboard_data.dashboard_data.summary is not None
    assert dashboard_data.dashboard_data.summary.total_logins == 0
    assert dashboard_data.dashboard_data.summary.last_login is None
    assert dashboard_data.dashboard_data.summary.account_created is not None
    assert dashboard_data.dashboard_data.stats == {}
    assert dashboard_data.dashboard_data.recent_activity == []


def test_get_dashboard_data_user_not_found(db_session: Session):
    """Test dashboard data retrieval with non-existent user."""
    service = DashboardService(db_session)

    # Try to get dashboard for non-existent user
    with pytest.raises(ValueError, match="User with ID 99999 not found"):
        service.get_dashboard_data(99999)


def test_get_dashboard_data_inactive_user(db_session: Session):
    """Test dashboard data retrieval with inactive user."""
    service = DashboardService(db_session)

    # Create a test user
    from app.services.auth_service import AuthService

    auth_service = AuthService(db_session)
    user = auth_service.register_user("inactive@example.com", "TestPass123")

    # Deactivate user
    user.is_active = False
    db_session.commit()

    # Try to get dashboard for inactive user
    with pytest.raises(ValueError, match="User account is inactive"):
        service.get_dashboard_data(user.id)


def test_validate_user_access_success(db_session: Session):
    """Test user access validation for active user."""
    service = DashboardService(db_session)

    # Create a test user
    from app.services.auth_service import AuthService

    auth_service = AuthService(db_session)
    user = auth_service.register_user("access@example.com", "TestPass123")

    # Validate access
    has_access = service.validate_user_access(user.id)
    assert has_access is True


def test_validate_user_access_user_not_found(db_session: Session):
    """Test user access validation for non-existent user."""
    service = DashboardService(db_session)

    # Validate access for non-existent user
    has_access = service.validate_user_access(99999)
    assert has_access is False


def test_validate_user_access_inactive_user(db_session: Session):
    """Test user access validation for inactive user."""
    service = DashboardService(db_session)

    # Create a test user
    from app.services.auth_service import AuthService

    auth_service = AuthService(db_session)
    user = auth_service.register_user("noaccess@example.com", "TestPass123")

    # Deactivate user
    user.is_active = False
    db_session.commit()

    # Validate access
    has_access = service.validate_user_access(user.id)
    assert has_access is False


def test_dashboard_data_structure(db_session: Session):
    """Test that dashboard data has correct structure and types."""
    service = DashboardService(db_session)

    # Create a test user
    from app.services.auth_service import AuthService

    auth_service = AuthService(db_session)
    user = auth_service.register_user("structure@example.com", "TestPass123")

    # Get dashboard data
    dashboard_data = service.get_dashboard_data(user.id)

    # Verify types
    assert isinstance(dashboard_data.user_id, int)
    assert isinstance(dashboard_data.email, str)
    assert isinstance(dashboard_data.message, str)
    assert isinstance(dashboard_data.dashboard_data.summary.total_logins, int)
    assert isinstance(dashboard_data.dashboard_data.stats, dict)
    assert isinstance(dashboard_data.dashboard_data.recent_activity, list)

    # Verify account_created is a datetime
    assert isinstance(dashboard_data.dashboard_data.summary.account_created, datetime)
