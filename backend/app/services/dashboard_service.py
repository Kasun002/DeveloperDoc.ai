"""
Dashboard service for business logic.

This module implements the dashboard service following SOLID principles:
- SRP: Single responsibility - handles only dashboard business logic
- OCP: Open for extension (new dashboard features), closed for modification
- DIP: Depends on abstractions (User model, not concrete implementations)

The service is designed to be easily testable and extensible.
"""

from typing import Optional

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.dashboard import DashboardData, DashboardResponse, DashboardSummary
from sqlalchemy.orm import Session


class DashboardService:
    """
    Service class for dashboard operations.

    This service handles all dashboard-related business logic, including
    retrieving user dashboard data, calculating statistics, and formatting
    responses.

    Following DIP: Depends on UserRepository abstraction, not concrete database.
    Following SRP: Only responsible for dashboard business logic.
    """

    def __init__(self, db: Session):
        """
        Initialize the dashboard service.

        Args:
            db: Database session for data access
        """
        self.db = db
        self.user_repository = UserRepository(db)

    def get_dashboard_data(self, user_id: int) -> DashboardResponse:
        """
        Retrieve dashboard data for a specific user.

        This method fetches user information and constructs dashboard data
        including summary statistics, additional stats, and recent activity.

        Currently returns placeholder/empty data structure. This is designed
        to be extended with real data in future iterations (OCP).

        Args:
            user_id: ID of the authenticated user

        Returns:
            DashboardResponse: Complete dashboard data for the user

        Raises:
            ValueError: If user not found or inactive
        """
        # Fetch user from repository
        user = self.user_repository.get_user_by_id(user_id)

        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        if not user.is_active:
            raise ValueError(f"User account is inactive")

        # Build dashboard data
        dashboard_data = self._build_dashboard_data(user)

        # Construct response
        return DashboardResponse(
            user_id=user.id,
            email=user.email,
            dashboard_data=dashboard_data,
            message="Dashboard data retrieved successfully",
        )

    def _build_dashboard_data(self, user: User) -> DashboardData:
        """
        Build dashboard data structure for a user.

        This is a private method that constructs the dashboard data.
        Following SRP: Separated from main method for clarity.
        Following OCP: Easy to extend with new data sources.

        Args:
            user: User model instance

        Returns:
            DashboardData: Structured dashboard data
        """
        # Build summary
        summary = DashboardSummary(
            total_logins=0,  # Placeholder - will be implemented with activity tracking
            last_login=None,  # Placeholder - will be implemented with activity tracking
            account_created=user.created_at,
        )

        # Build additional stats (extensible)
        stats = {}

        # Build recent activity (extensible)
        recent_activity = []

        return DashboardData(
            summary=summary, stats=stats, recent_activity=recent_activity
        )

    def validate_user_access(self, user_id: int) -> bool:
        """
        Validate that a user has access to dashboard.

        This method can be extended to include additional access checks
        such as subscription status, permissions, etc.
        Following OCP: Easy to extend with new validation rules.

        Args:
            user_id: ID of the user to validate

        Returns:
            bool: True if user has access, False otherwise
        """
        user = self.user_repository.get_user_by_id(user_id)

        if not user:
            return False

        if not user.is_active:
            return False

        # Additional access checks can be added here
        # Example: check subscription status, permissions, etc.

        return True
