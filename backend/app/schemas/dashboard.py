"""
Dashboard Pydantic schemas for request validation and response serialization.

This module defines all request and response schemas for the dashboard API,
following the Single Responsibility Principle (SRP) - each schema has one clear purpose.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    """
    Summary statistics for the user's dashboard.

    This schema encapsulates basic user statistics and account information.
    Following SRP: Only responsible for summary data structure.
    """

    total_logins: int = Field(
        default=0, description="Total number of successful logins", examples=[42]
    )
    last_login: Optional[datetime] = Field(
        default=None,
        description="Timestamp of the last successful login",
        examples=["2024-01-15T10:30:00Z"],
    )
    account_created: datetime = Field(
        ...,
        description="Timestamp when the account was created",
        examples=["2024-01-01T00:00:00Z"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total_logins": 42,
                    "last_login": "2024-01-15T10:30:00Z",
                    "account_created": "2024-01-01T00:00:00Z",
                }
            ]
        }
    }


class DashboardData(BaseModel):
    """
    Complete dashboard data structure.

    This schema aggregates all dashboard information including summary,
    statistics, and recent activity.
    Following OCP: Open for extension (new fields), closed for modification.
    """

    summary: DashboardSummary = Field(
        ..., description="Summary statistics for the user"
    )
    stats: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional statistics (extensible)",
        examples=[{"key": "value"}],
    )
    recent_activity: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recent user activity (extensible)",
        examples=[[{"action": "login", "timestamp": "2024-01-15T10:30:00Z"}]],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": {
                        "total_logins": 42,
                        "last_login": "2024-01-15T10:30:00Z",
                        "account_created": "2024-01-01T00:00:00Z",
                    },
                    "stats": {},
                    "recent_activity": [],
                }
            ]
        }
    }


class DashboardResponse(BaseModel):
    """
    Response schema for dashboard API endpoint.

    This schema defines the complete response structure returned by the
    dashboard endpoint, including user information and dashboard data.
    Following ISP: Minimal interface with only necessary fields.
    """

    user_id: int = Field(
        ..., description="Unique identifier of the authenticated user", examples=[1]
    )
    email: str = Field(
        ...,
        description="Email address of the authenticated user",
        examples=["user@example.com"],
    )
    dashboard_data: DashboardData = Field(
        ..., description="Dashboard data for the user"
    )
    message: str = Field(
        default="Dashboard data retrieved successfully",
        description="Success message",
        examples=["Dashboard data retrieved successfully"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": 1,
                    "email": "user@example.com",
                    "dashboard_data": {
                        "summary": {
                            "total_logins": 42,
                            "last_login": "2024-01-15T10:30:00Z",
                            "account_created": "2024-01-01T00:00:00Z",
                        },
                        "stats": {},
                        "recent_activity": [],
                    },
                    "message": "Dashboard data retrieved successfully",
                }
            ]
        }
    }
