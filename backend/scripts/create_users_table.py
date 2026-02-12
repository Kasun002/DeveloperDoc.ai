"""
Script to create users and password_reset_tokens tables in the main database.
This is needed because the main database doesn't have pgvector extension.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from app.core.config import settings
from app.models.user import User, PasswordResetToken
from app.core.database import Base

def create_users_tables():
    """Create users and password_reset_tokens tables in the main database."""
    print(f"Creating users tables in main database: {settings.database_url.split('@')[-1]}")
    
    # Create engine for main database
    engine = create_engine(settings.database_url)
    
    # Create only the users and password_reset_tokens tables
    User.__table__.create(engine, checkfirst=True)
    PasswordResetToken.__table__.create(engine, checkfirst=True)
    
    print("✅ Users tables created successfully!")
    
    # Verify tables exist
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables in main database: {tables}")

if __name__ == "__main__":
    create_users_tables()
