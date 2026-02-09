"""
FastAPI application entry point.

This module initializes the FastAPI application with configuration,
middleware, and API routes.
"""

import logging
from contextlib import asynccontextmanager

from app.api.v1.endpoints import auth, dashboard, mcp_tools
from app.core.config import settings
from app.core.database import engine
from app.core.vector_database import vector_db_manager
from app.core.logging_config import configure_logging, get_logger
from app.core.telemetry import configure_telemetry, instrument_fastapi
from app.core.exceptions import (
    AuthenticationError,
    EmailAlreadyExistsError,
    IncorrectPasswordError,
    InvalidResetTokenError,
    InvalidTokenError,
    WeakPasswordError,
    AgentWorkflowError,
    AgentTimeoutError,
    AgentServiceUnavailableError,
    InvalidPromptError,
)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

# Configure structured logging
configure_logging()
logger = get_logger(__name__)

# Configure OpenTelemetry
tracer_provider = configure_telemetry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.

    Handles database connectivity verification on startup and cleanup on shutdown.
    """
    # Startup: Verify database connectivity
    logger.info("application_startup", environment=settings.app_env)

    if engine is None:
        logger.error(
            "database_engine_not_initialized",
            error="DATABASE_URL may not be configured"
        )
        raise RuntimeError("Database configuration error: DATABASE_URL not set")

    try:
        # Test database connection
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            logger.info("database_connection_successful", database="main")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e), database="main")
        raise RuntimeError(f"Failed to connect to database: {e}")
    
    # Initialize vector database connection pool
    try:
        await vector_db_manager.connect()
        health = await vector_db_manager.health_check()
        if health.get("status") == "healthy":
            logger.info(
                "vector_database_connection_successful",
                database="vector",
                pool_size=health.get("pool_size"),
                pgvector_available=health.get("pgvector_available")
            )
        else:
            logger.warning(
                "vector_database_health_check_warning",
                database="vector",
                health_status=health
            )
    except Exception as e:
        logger.warning(
            "vector_database_connection_failed",
            database="vector",
            error=str(e),
            critical=False
        )
    
    # Initialize semantic cache
    try:
        from app.services.semantic_cache import semantic_cache
        await semantic_cache.connect()
        logger.info(
            "semantic_cache_connection_successful",
            service="semantic_cache"
        )
    except Exception as e:
        logger.warning(
            "semantic_cache_connection_failed",
            service="semantic_cache",
            error=str(e),
            critical=False
        )

    yield

    # Shutdown: Cleanup
    logger.info("application_shutdown")
    if engine:
        engine.dispose()
        logger.info("database_connections_closed", database="main")
    
    # Close vector database pool
    await vector_db_manager.disconnect()
    logger.info("database_connections_closed", database="vector")
    
    # Close semantic cache connections
    try:
        from app.services.semantic_cache import semantic_cache
        await semantic_cache.disconnect()
        logger.info("semantic_cache_disconnected", service="semantic_cache")
    except Exception as e:
        logger.warning(
            "semantic_cache_disconnect_error",
            service="semantic_cache",
            error=str(e)
        )


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

# Instrument FastAPI with OpenTelemetry
instrument_fastapi(app)

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
        logger.error("health_check_failed", reason="database_engine_not_initialized")
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

        logger.info("health_check_successful", database="main")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error("health_check_failed", database="main", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": "Database connection failed",
            },
        )


@app.get(
    "/health/vector-db",
    tags=["health"],
    summary="Vector Database Health Check",
    description="Check the health status of the vector database (pgvector) connectivity",
    responses={
        200: {
            "description": "Vector database is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "pool_size": 5,
                        "pool_free": 3,
                        "pgvector_available": True
                    }
                }
            },
        },
        503: {
            "description": "Vector database is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "error": "Connection pool not initialized"
                    }
                }
            },
        },
    },
)
async def vector_db_health_check():
    """
    Vector database health check endpoint.

    Verifies that the vector database is accessible and pgvector extension is available.
    Returns 200 if healthy, 503 if database is unreachable.
    """
    health = await vector_db_manager.health_check()
    
    if health.get("status") == "healthy":
        return health
    else:
        return JSONResponse(
            status_code=503,
            content=health
        )


# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])

app.include_router(mcp_tools.router, prefix="/api/v1/mcp", tags=["mcp-tools"])

# Import agent router
from app.api.v1.endpoints import agent
app.include_router(agent.router, prefix="/api/v1/agent", tags=["ai-agent"])


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


# AI Agent System Exception Handlers

@app.exception_handler(InvalidPromptError)
async def invalid_prompt_error_handler(request: Request, exc: InvalidPromptError):
    """
    Handle invalid prompt errors with 400 Bad Request.
    
    Returns validation error details to help users correct their prompts.
    """
    logger.warning(
        "invalid_prompt_error",
        error=str(exc),
        path=str(request.url),
        method=request.method
    )
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc) if str(exc) else "Invalid prompt"}
    )


@app.exception_handler(AgentWorkflowError)
async def agent_workflow_error_handler(request: Request, exc: AgentWorkflowError):
    """
    Handle agent workflow errors with 500 Internal Server Error.
    
    Logs the error with trace information and returns a sanitized message.
    """
    logger.error(
        "agent_workflow_error",
        error=str(exc),
        error_type=type(exc).__name__,
        path=str(request.url),
        method=request.method,
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Agent workflow execution failed"}
    )


@app.exception_handler(AgentTimeoutError)
async def agent_timeout_error_handler(request: Request, exc: AgentTimeoutError):
    """
    Handle agent timeout errors with 504 Gateway Timeout.
    
    Returns a clear message indicating the operation took too long.
    """
    logger.error(
        "agent_timeout_error",
        error=str(exc),
        path=str(request.url),
        method=request.method
    )
    return JSONResponse(
        status_code=504,
        content={"detail": "Request timeout. The operation took too long to complete."}
    )


@app.exception_handler(AgentServiceUnavailableError)
async def agent_service_unavailable_error_handler(
    request: Request, exc: AgentServiceUnavailableError
):
    """
    Handle agent service unavailable errors with 503 Service Unavailable.
    
    Returns a message indicating the service is temporarily unavailable.
    """
    logger.error(
        "agent_service_unavailable_error",
        error=str(exc),
        path=str(request.url),
        method=request.method
    )
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Service temporarily unavailable. Please try again later.",
            "retry_after": 60  # Suggest retry after 60 seconds
        },
        headers={"Retry-After": "60"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected server errors with 500 Internal Server Error.

    Sanitizes error messages to avoid leaking sensitive information such as
    database connection strings, internal paths, or stack traces.
    """
    # Log the full error for debugging with structured logging
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=str(request.url),
        method=request.method,
        exc_info=True
    )

    # Return sanitized error response
    return JSONResponse(
        status_code=500, content={"detail": "An internal server error occurred"}
    )
