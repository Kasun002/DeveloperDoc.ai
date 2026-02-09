"""
Dashboard API endpoints.

This module defines the dashboard endpoints following SOLID principles:
- SRP: Only handles HTTP request/response for dashboard
- OCP: Open for extension (new endpoints), closed for modification
- DIP: Depends on DashboardService abstraction

All endpoints require JWT authentication.
"""

from app.core.dependencies import get_current_user, get_db
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter()


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    """
    Dependency function that provides a DashboardService instance.

    Following DIP: Dependency injection for loose coupling.
    This allows easy mocking in tests and flexibility in implementation.

    Args:
        db: Database session from dependency injection

    Returns:
        DashboardService: Initialized dashboard service
    """
    return DashboardService(db)


@router.get(
    "",
    response_model=DashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user dashboard",
    description="Retrieve dashboard data for the authenticated user. Requires valid JWT access token.",
    responses={
        200: {
            "description": "Dashboard data retrieved successfully",
            "model": DashboardResponse,
        },
        401: {
            "description": "Authentication failed - invalid or missing token",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_token": {
                            "summary": "Missing token",
                            "value": {"detail": "Not authenticated"},
                        },
                        "invalid_token": {
                            "summary": "Invalid token",
                            "value": {"detail": "Invalid or expired token"},
                        },
                        "expired_token": {
                            "summary": "Expired token",
                            "value": {"detail": "Token has expired"},
                        },
                    }
                }
            },
        },
        404: {
            "description": "User not found",
            "content": {"application/json": {"example": {"detail": "User not found"}}},
        },
        403: {
            "description": "User account inactive",
            "content": {
                "application/json": {"example": {"detail": "User account is inactive"}}
            },
        },
    },
)
async def get_dashboard(
    current_user_id: int = Depends(get_current_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get dashboard data for authenticated user.

    This endpoint retrieves dashboard information for the currently authenticated
    user. The user is identified by the JWT access token provided in the
    Authorization header.

    Security Flow:
    1. Extract JWT token from Authorization header (Bearer <token>)
    2. Validate token signature and expiration
    3. Extract user_id from token payload
    4. Verify user exists and is active
    5. Retrieve dashboard data
    6. Return formatted response

    Following SRP: Only handles HTTP concerns, delegates business logic to service.
    Following DIP: Depends on abstractions (get_current_user, DashboardService).

    Args:
        current_user_id: User ID extracted from validated JWT token
        dashboard_service: Dashboard service instance for business logic

    Returns:
        DashboardResponse: Dashboard data including user info and statistics

    Raises:
        HTTPException 401: If authentication fails
        HTTPException 403: If user account is inactive
        HTTPException 404: If user not found
        HTTPException 500: If server error occurs
    """
    try:
        # Delegate business logic to service layer
        dashboard_data = dashboard_service.get_dashboard_data(current_user_id)
        return dashboard_data

    except ValueError as e:
        error_msg = str(e).lower()

        # Handle specific error cases
        if "not found" in error_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        elif "inactive" in error_msg:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        else:
            # Generic bad request for other ValueError cases
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        # Log the error for debugging (in production, use proper logging)
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error retrieving dashboard data: {e}", exc_info=True)

        # Return generic error to avoid leaking sensitive information
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving dashboard data",
        )
