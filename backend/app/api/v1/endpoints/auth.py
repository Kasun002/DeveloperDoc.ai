"""
Authentication API endpoints.

This module defines the authentication endpoints for user registration and login.
"""

from app.core.dependencies import get_current_user, get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmSchema,
    PasswordResetRequestSchema,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """
    Dependency function that provides an AuthService instance.

    Args:
        db: Database session from dependency injection

    Returns:
        AuthService: Initialized authentication service
    """
    return AuthService(db)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password",
    responses={
        201: {
            "description": "User successfully registered",
            "model": UserResponse,
        },
        409: {
            "description": "Email already registered",
            "content": {
                "application/json": {"example": {"detail": "Email already registered"}}
            },
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "password"],
                                "msg": "Password must contain at least one letter",
                                "type": "value_error",
                            }
                        ]
                    }
                }
            },
        },
    },
)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user account.

    Creates a new user with the provided email and password. The password
    is hashed before storage. Returns the created user details without
    exposing the password hash.

    Args:
        request: Registration request containing email and password
        auth_service: Authentication service dependency

    Returns:
        UserResponse: Created user details

    Raises:
        HTTPException 409: If email already exists
        HTTPException 422: If validation fails
    """
    try:
        user = auth_service.register_user(request.email, request.password)
        return UserResponse.model_validate(user)
    except ValueError as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_msg
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user and return access and refresh tokens",
    responses={
        200: {
            "description": "Login successful, tokens returned",
            "model": TokenResponse,
        },
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {"example": {"detail": "Invalid email or password"}}
            },
        },
        422: {
            "description": "Validation error",
        },
    },
)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate user and return JWT tokens.

    Validates user credentials and returns both access token (30-minute expiration)
    and refresh token (7-day expiration) for authenticated API access.

    Args:
        request: Login request containing email and password
        auth_service: Authentication service dependency

    Returns:
        TokenResponse: Access and refresh tokens

    Raises:
        HTTPException 401: If credentials are invalid
        HTTPException 422: If validation fails
    """
    user = auth_service.authenticate_user(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Generate tokens
    access_token = auth_service.create_access_token(user.id)
    refresh_token = auth_service.create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )


@router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change user password",
    description="Change password for authenticated user (requires valid access token)",
    responses={
        200: {
            "description": "Password changed successfully",
            "model": MessageResponse,
        },
        401: {
            "description": "Authentication failed or invalid token",
            "content": {
                "application/json": {"example": {"detail": "Invalid or expired token"}}
            },
        },
        400: {
            "description": "Current password is incorrect",
            "content": {
                "application/json": {
                    "example": {"detail": "Current password is incorrect"}
                }
            },
        },
        422: {
            "description": "Validation error",
        },
    },
    dependencies=[Depends(get_current_user)],
)
async def change_password(
    request: ChangePasswordRequest,
    current_user_id: int = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Change password for authenticated user.

    Requires a valid access token in the Authorization header. Verifies
    the current password before updating to the new password.

    Args:
        request: Password change request with current and new passwords
        current_user_id: User ID from validated access token
        auth_service: Authentication service dependency

    Returns:
        MessageResponse: Success message

    Raises:
        HTTPException 401: If token is invalid or expired
        HTTPException 400: If current password is incorrect
        HTTPException 422: If validation fails
    """
    try:
        success = auth_service.change_password(
            current_user_id, request.current_password, request.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to change password",
            )

        return MessageResponse(message="Password changed successfully")

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/reset-password/request",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
    description="Request a password reset token for the given email",
    responses={
        200: {
            "description": "Password reset instructions sent (always returns 200 for security)",
            "model": MessageResponse,
        },
        422: {
            "description": "Validation error",
        },
    },
)
async def request_password_reset(
    request: PasswordResetRequestSchema,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Request a password reset token.

    Generates a password reset token for the given email address. For security
    reasons, always returns success even if the email doesn't exist (to prevent
    user enumeration attacks).

    In a production system, the token would be sent via email. For this implementation,
    the token is returned in the response for testing purposes.

    Args:
        request: Password reset request with email
        auth_service: Authentication service dependency

    Returns:
        MessageResponse: Success message

    Raises:
        HTTPException 422: If validation fails
    """
    try:
        token = auth_service.request_password_reset(request.email)
        # In production, send token via email instead of returning it
        # For now, return it in the message for testing
        return MessageResponse(
            message=f"Password reset instructions sent to {request.email}. Token: {token}"
        )
    except ValueError:
        # For security, don't reveal if email exists or not
        # Return success message even if user not found
        return MessageResponse(
            message=f"If an account exists with {request.email}, password reset instructions have been sent"
        )


@router.post(
    "/reset-password/confirm",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm password reset",
    description="Reset password using a valid reset token",
    responses={
        200: {
            "description": "Password reset successful",
            "model": MessageResponse,
        },
        400: {
            "description": "Invalid or expired reset token",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid or expired reset token"}
                }
            },
        },
        422: {
            "description": "Validation error",
        },
    },
)
async def confirm_password_reset(
    request: PasswordResetConfirmSchema,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Confirm password reset with token.

    Validates the reset token and updates the user's password. The token
    is marked as used to prevent reuse.

    Args:
        request: Password reset confirmation with token and new password
        auth_service: Authentication service dependency

    Returns:
        MessageResponse: Success message

    Raises:
        HTTPException 400: If token is invalid or expired
        HTTPException 422: If validation fails
    """
    try:
        success = auth_service.confirm_password_reset(
            request.token, request.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to reset password",
            )

        return MessageResponse(message="Password reset successful")

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Generate a new access token using a valid refresh token",
    responses={
        200: {
            "description": "New access token generated",
            "model": TokenResponse,
        },
        401: {
            "description": "Invalid or expired refresh token",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid or expired refresh token"}
                }
            },
        },
    },
)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Refresh access token using refresh token.

    Validates the refresh token and generates a new access token with
    the same user identification. The refresh token remains valid.

    Args:
        request: Refresh token request
        auth_service: Authentication service dependency

    Returns:
        TokenResponse: New access token and the same refresh token

    Raises:
        HTTPException 401: If refresh token is invalid or expired
    """
    try:
        new_access_token = auth_service.refresh_access_token(request.refresh_token)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=request.refresh_token,
            token_type="bearer",
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
