"""
Database configuration and session management.

This module sets up the SQLAlchemy engine, session factory, and declarative base
for ORM models. It uses the database URL from application settings with proper
connection pooling for PostgreSQL.
"""

from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# Create SQLAlchemy engine with connection pooling
# For PostgreSQL, connection pooling is enabled by default
# Note: If DATABASE_URL is not set, engine creation will be deferred
if settings.database_url:
    # Determine if we're using PostgreSQL or SQLite
    is_postgres = settings.database_url.startswith("postgresql")

    # Configure engine with appropriate settings
    engine_kwargs = {
        "pool_pre_ping": True,  # Verify connections before using them (prevents stale connections)
        "echo": settings.app_env == "development",  # Log SQL in development
    }

    # Add PostgreSQL-specific connection pooling configuration
    if is_postgres:
        engine_kwargs.update(
            {
                "poolclass": QueuePool,  # Use QueuePool for connection pooling
                "pool_size": 5,  # Minimum number of connections to maintain
                "max_overflow": 10,  # Maximum number of connections above pool_size
                "pool_timeout": 30,  # Seconds to wait before giving up on getting a connection
                "pool_recycle": 3600,  # Recycle connections after 1 hour (prevents stale connections)
            }
        )
    else:
        # SQLite-specific configuration
        engine_kwargs.update(
            {
                "connect_args": {
                    "check_same_thread": False
                }  # Allow SQLite to be used across threads
            }
        )

    engine = create_engine(settings.database_url, **engine_kwargs)

    # Create session factory
    # autocommit=False: Transactions must be explicitly committed
    # autoflush=False: Changes aren't automatically flushed to DB
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    # Placeholder for when DATABASE_URL is not configured
    engine = None
    SessionLocal = None

# Create declarative base for ORM models
Base = declarative_base()


def get_db_info():
    """
    Get database connection information for debugging.

    Returns:
        dict: Database connection details (safe for logging)
    """
    if not engine:
        return {"status": "not_configured"}

    return {
        "url": (
            settings.database_url.split("@")[-1]
            if "@" in settings.database_url
            else "local"
        ),
        "pool_size": engine.pool.size() if hasattr(engine.pool, "size") else "N/A",
        "checked_out": (
            engine.pool.checkedout() if hasattr(engine.pool, "checkedout") else "N/A"
        ),
        "overflow": (
            engine.pool.overflow() if hasattr(engine.pool, "overflow") else "N/A"
        ),
        "is_postgres": (
            settings.database_url.startswith("postgresql")
            if settings.database_url
            else False
        ),
    }
