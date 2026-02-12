"""Check the status of both databases."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, inspect
from app.core.config import settings

def check_databases():
    """Check tables in both databases."""
    
    # Check main database
    print("=" * 60)
    print("MAIN DATABASE (users, auth)")
    print("=" * 60)
    print(f"URL: {settings.database_url.split('@')[-1]}")
    
    main_engine = create_engine(settings.database_url)
    main_inspector = inspect(main_engine)
    main_tables = main_inspector.get_table_names()
    print(f"Tables: {main_tables}")
    
    # Check vector database
    print("\n" + "=" * 60)
    print("VECTOR DATABASE (framework docs, semantic cache)")
    print("=" * 60)
    print(f"URL: {settings.vector_database_url.split('@')[-1]}")
    
    vector_engine = create_engine(settings.vector_database_url)
    vector_inspector = inspect(vector_engine)
    vector_tables = vector_inspector.get_table_names()
    print(f"Tables: {vector_tables}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ Main DB has users table: {'users' in main_tables}")
    print(f"✅ Main DB has password_reset_tokens table: {'password_reset_tokens' in main_tables}")
    print(f"✅ Vector DB has framework_documentation table: {'framework_documentation' in vector_tables}")
    print(f"✅ Vector DB has semantic_cache table: {'semantic_cache' in vector_tables}")

if __name__ == "__main__":
    check_databases()
