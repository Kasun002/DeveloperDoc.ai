#!/usr/bin/env python3
"""
Database setup script for PostgreSQL.

This script helps verify the database connection and provides
useful information about the database setup.
"""

import os
import sys

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.database import engine, get_db_info
from sqlalchemy import inspect, text


def check_connection():
    """Check if database connection is working."""
    print("\n" + "=" * 60)
    print("DATABASE CONNECTION CHECK")
    print("=" * 60)

    if not engine:
        print("❌ Database engine not initialized")
        print("   Make sure DATABASE_URL is set in .env or .env.local")
        return False

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✓ Database connection successful")
            print(f"  PostgreSQL version: {version.split(',')[0]}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def show_config():
    """Display current database configuration."""
    print("\n" + "=" * 60)
    print("DATABASE CONFIGURATION")
    print("=" * 60)

    # Mask password in URL for display
    db_url = settings.database_url
    if "@" in db_url:
        parts = db_url.split("@")
        credentials = parts[0].split("://")[1]
        if ":" in credentials:
            user = credentials.split(":")[0]
            masked_url = db_url.replace(credentials, f"{user}:****")
        else:
            masked_url = db_url
    else:
        masked_url = db_url

    print(f"Database URL: {masked_url}")
    print(f"Environment: {settings.app_env}")
    print(f"App Name: {settings.app_name}")

    # Show pool information
    if engine:
        info = get_db_info()
        print(f"\nConnection Pool:")
        print(f"  Pool Size: {info.get('pool_size', 'N/A')}")
        print(f"  Checked Out: {info.get('checked_out', 'N/A')}")
        print(f"  Overflow: {info.get('overflow', 'N/A')}")
        print(f"  Is PostgreSQL: {info.get('is_postgres', False)}")


def list_tables():
    """List all tables in the database."""
    print("\n" + "=" * 60)
    print("DATABASE TABLES")
    print("=" * 60)

    if not engine:
        print("❌ Database engine not initialized")
        return

    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if not tables:
            print("⚠ No tables found. Run migrations with: alembic upgrade head")
            return

        print(f"Found {len(tables)} table(s):")
        for table in tables:
            print(f"  • {table}")

            # Show columns for each table
            columns = inspector.get_columns(table)
            print(f"    Columns: {len(columns)}")
            for col in columns:
                col_type = str(col["type"])
                nullable = "NULL" if col["nullable"] else "NOT NULL"
                print(f"      - {col['name']}: {col_type} {nullable}")
            print()

    except Exception as e:
        print(f"❌ Error listing tables: {e}")


def check_migrations():
    """Check migration status."""
    print("\n" + "=" * 60)
    print("MIGRATION STATUS")
    print("=" * 60)

    if not engine:
        print("❌ Database engine not initialized")
        return

    try:
        with engine.connect() as connection:
            # Check if alembic_version table exists
            result = connection.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = 'alembic_version')"
                )
            )
            exists = result.fetchone()[0]

            if not exists:
                print("⚠ Alembic version table not found")
                print("  Run migrations with: alembic upgrade head")
                return

            # Get current version
            result = connection.execute(text("SELECT version_num FROM alembic_version"))
            version = result.fetchone()

            if version:
                print(f"✓ Current migration version: {version[0]}")
                print("  To update: alembic upgrade head")
            else:
                print("⚠ No migration version found")
                print("  Run migrations with: alembic upgrade head")

    except Exception as e:
        print(f"❌ Error checking migrations: {e}")


def test_crud_operations():
    """Test basic CRUD operations."""
    print("\n" + "=" * 60)
    print("CRUD OPERATIONS TEST")
    print("=" * 60)

    if not engine:
        print("❌ Database engine not initialized")
        return

    try:
        with engine.connect() as connection:
            # Check if users table exists
            result = connection.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = 'users')"
                )
            )
            exists = result.fetchone()[0]

            if not exists:
                print("⚠ Users table not found. Run migrations first.")
                return

            # Count users
            result = connection.execute(text("SELECT COUNT(*) FROM users"))
            count = result.fetchone()[0]
            print(f"✓ Users table accessible")
            print(f"  Current user count: {count}")

            # Check password_reset_tokens table
            result = connection.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = 'password_reset_tokens')"
                )
            )
            exists = result.fetchone()[0]

            if exists:
                result = connection.execute(
                    text("SELECT COUNT(*) FROM password_reset_tokens")
                )
                count = result.fetchone()[0]
                print(f"✓ Password reset tokens table accessible")
                print(f"  Current token count: {count}")

    except Exception as e:
        print(f"❌ Error testing CRUD operations: {e}")


def main():
    """Run all checks."""
    print("\n" + "=" * 60)
    print("POSTGRESQL DATABASE SETUP VERIFICATION")
    print("=" * 60)

    # Check connection
    if not check_connection():
        print("\n❌ Database connection failed. Please check your configuration.")
        print("\nTroubleshooting steps:")
        print("1. Ensure PostgreSQL Docker container is running:")
        print("   docker ps | grep pg_local")
        print("2. Verify .env or .env.local has correct DATABASE_URL:")
        print("   DATABASE_URL=postgresql://admin:admin123@localhost:5432/ai_admin")
        print("3. Test connection manually:")
        print("   docker exec -it pg_local psql -U admin -d ai_admin")
        return 1

    # Show configuration
    show_config()

    # Check migrations
    check_migrations()

    # List tables
    list_tables()

    # Test CRUD
    test_crud_operations()

    print("\n" + "=" * 60)
    print("SETUP VERIFICATION COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. If migrations not run: alembic upgrade head")
    print("2. Start the application: uvicorn app.main:app --reload")
    print("3. Test API: http://localhost:8000/docs")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
