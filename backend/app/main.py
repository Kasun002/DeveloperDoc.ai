"""
FastAPI application entry point.

This module initializes the FastAPI application with configuration,
middleware, and API routes.
"""

import logging
from contextlib import asynccontextmanager

from app.api.v1.endpoints import auth, dashboard
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import (
    AuthenticationError,
    EmailAlreadyExistsError,
    IncorrectPasswordError,
    InvalidResetTokenError,
    InvalidTokenError,
    WeakPasswordError,
)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.

    Handles database connectivity verification on startup and cleanup on shutdown.
    """
    # Startup: Verify database connectivity
    logger.info("Starting application...")

    if engine is None:
        logger.error(
            "Database engine not initialized. DATABASE_URL may not be configured."
        )
        raise RuntimeError("Database configuration error: DATABASE_URL not set")

    try:
        # Test database connection
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            logger.info("✓ Database connection successful")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        raise RuntimeError(f"Failed to connect to database: {e}")

    yield

    # Shutdown: Cleanup
    logger.info("Shutting down application...")
    if engine:
        engine.dispose()
        logger.info("Database connections closed")


# Initialize FastAPI application
app = FastAPI(
    title="User Authentication Backend API",
    description="""
## JWT-based User Authentication System

A secure, production-ready authentication backend built with FastAPI and PostgreSQL.

### Features

* **User Registration** - Create new user accounts with email and password
* **User Login** - Authenticate and receive JWT tokens (access + refresh)
* **Password Management** - Change password and reset forgotten passwords
* **Token Refresh** - Obtain new access tokens without re-authentication
* **Security** - Bcrypt password hashing, JWT tokens, comprehensive validation

### Authentication

Protected endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer <your_access_token>
```

Access tokens expire after 30 minutes. Use the refresh token to obtain a new access token.

### Security Considerations

* Passwords are hashed with bcrypt before storage
* JWT tokens are signed with HS256/RS256
* Password reset tokens expire after 1 hour
* All sensitive operations require authentication
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan,
)

# Add security scheme for Bearer token authentication
from fastapi.openapi.utils import get_openapi


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        contact=app.contact,
        license_info=app.license_info,
    )

    # Add security scheme for Bearer token
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT access token in the format: Bearer <token>",
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {"name": settings.app_name, "version": "1.0.0", "status": "running"}


@app.get(
    "/health",
    tags=["health"],
    summary="Health Check",
    description="Check the health status of the API and database connectivity",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {"status": "healthy", "database": "connected"}
                }
            },
        },
        503: {
            "description": "Service is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "database": "disconnected",
                        "error": "Database connection failed",
                    }
                }
            },
        },
    },
)
async def health_check():
    """
    Health check endpoint.

    Verifies that the API is running and can connect to the database.
    Returns 200 if healthy, 503 if database is unreachable.
    """
    # Check database connectivity
    if engine is None:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": "Database engine not initialized",
            },
        )

    try:
        # Attempt to execute a simple query
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": "Database connection failed",
            },
        )


# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])


# Global exception handlers
@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    """
    Handle authentication errors with 401 Unauthorized.

    Returns a sanitized error message without exposing sensitive details.
    """
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc) if str(exc) else "Authentication failed"},
    )


@app.exception_handler(InvalidTokenError)
async def invalid_token_error_handler(request: Request, exc: InvalidTokenError):
    """
    Handle invalid token errors with 401 Unauthorized.

    Returns a sanitized error message without exposing token details.
    """
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc) if str(exc) else "Invalid or expired token"},
    )


@app.exception_handler(WeakPasswordError)
async def weak_password_error_handler(request: Request, exc: WeakPasswordError):
    """
    Handle weak password errors with 422 Unprocessable Entity.

    Returns validation error details to help users create stronger passwords.
    """
    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {
                    "loc": ["body", "password"],
                    "msg": (
                        str(exc)
                        if str(exc)
                        else "Password does not meet strength requirements"
                    ),
                    "type": "value_error",
                }
            ]
        },
    )


@app.exception_handler(EmailAlreadyExistsError)
async def email_exists_error_handler(request: Request, exc: EmailAlreadyExistsError):
    """
    Handle duplicate email errors with 409 Conflict.

    Returns a clear message without exposing user existence details unnecessarily.
    """
    return JSONResponse(status_code=409, content={"detail": "Email already registered"})


@app.exception_handler(InvalidResetTokenError)
async def invalid_reset_token_error_handler(
    request: Request, exc: InvalidResetTokenError
):
    """
    Handle invalid reset token errors with 400 Bad Request.

    Returns a sanitized error message without exposing token details.
    """
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc) if str(exc) else "Invalid or expired reset token"},
    )


@app.exception_handler(IncorrectPasswordError)
async def incorrect_password_error_handler(
    request: Request, exc: IncorrectPasswordError
):
    """
    Handle incorrect password errors with 400 Bad Request.

    Returns a clear message for password change failures.
    """
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc) if str(exc) else "Current password is incorrect"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected server errors with 500 Internal Server Error.

    Sanitizes error messages to avoid leaking sensitive information such as
    database connection strings, internal paths, or stack traces.
    """
    # Log the full error for debugging (in production, use proper logging)
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Return sanitized error response
    return JSONResponse(
        status_code=500, content={"detail": "An internal server error occurred"}
    )
