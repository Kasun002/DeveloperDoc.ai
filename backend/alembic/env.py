"""
Alembic migration environment configuration.

This module configures Alembic for database migrations. It sets up the
database connection, imports all models for autogenerate support, and
defines migration execution modes (offline and online).

Alembic is used for version-controlled database schema changes, allowing
reproducible and trackable database updates across environments.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add the parent directory to sys.path to import app modules
# This allows Alembic to import models and configuration from the app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.database import Base

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the database URL from application settings
# This ensures migrations use the same database as the application
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
# Import all models here so Alembic can detect schema changes
from app.models import *  # noqa: F401, F403

# Target metadata for migrations
# This contains all table definitions from SQLAlchemy models
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Offline mode generates SQL scripts without connecting to the database.
    This is useful for:
    - Generating SQL files for manual review
    - Applying migrations in restricted environments
    - Debugging migration scripts

    In offline mode:
    - No database connection is required
    - SQL statements are written to stdout or a file
    - No actual database changes are made

    Usage:
        alembic upgrade head --sql > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Online mode connects to the database and applies migrations directly.
    This is the standard mode for applying migrations.

    In online mode:
    - Database connection is established
    - Migrations are applied to the database
    - Changes are committed in a transaction

    The function:
    1. Creates a database engine from configuration
    2. Establishes a connection
    3. Configures the migration context
    4. Runs migrations within a transaction

    Usage:
        alembic upgrade head
    """
    # Create database engine from configuration
    # NullPool is used to avoid connection pooling issues during migrations
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Configure migration context with the connection
        context.configure(connection=connection, target_metadata=target_metadata)

        # Run migrations within a transaction
        # If any migration fails, the entire transaction is rolled back
        with context.begin_transaction():
            context.run_migrations()


# Determine which mode to run based on Alembic context
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
