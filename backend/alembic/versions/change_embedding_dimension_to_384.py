"""change_embedding_dimension_to_384

Revision ID: c8f9d2e1a3b4
Revises: 7048d18b575d
Create Date: 2026-02-12 10:00:00.000000

This migration changes the embedding vector dimension from 1536 (OpenAI text-embedding-3-small)
to 384 (sentence-transformers all-MiniLM-L6-v2) to support local embeddings without API quotas.

WARNING: This migration will:
1. Drop the existing HNSW index
2. Alter the embedding column dimension
3. Recreate the HNSW index
4. TRUNCATE all existing data (embeddings are incompatible between dimensions)

If you have existing data you want to keep, you must re-ingest it after this migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8f9d2e1a3b4'
down_revision: Union[str, Sequence[str], None] = '7048d18b575d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema to use 384-dimension embeddings.
    
    This migration:
    1. Drops the HNSW index (required before altering vector column)
    2. Truncates existing data (1536-dim embeddings incompatible with 384-dim)
    3. Alters the embedding column to 384 dimensions
    4. Recreates the HNSW index for the new dimension
    """
    # Drop the existing HNSW index (required before altering vector column)
    print("Dropping existing HNSW index...")
    op.execute("DROP INDEX IF EXISTS idx_framework_documentation_embedding")
    
    # Truncate existing data since 1536-dim embeddings are incompatible with 384-dim
    print("Truncating existing data (embeddings are incompatible)...")
    op.execute("TRUNCATE TABLE framework_documentation")
    
    # Alter the embedding column to 384 dimensions
    print("Altering embedding column to 384 dimensions...")
    op.execute("""
        ALTER TABLE framework_documentation 
        ALTER COLUMN embedding TYPE vector(384)
    """)
    
    # Update the comment
    op.execute("""
        COMMENT ON COLUMN framework_documentation.embedding IS 
        'all-MiniLM-L6-v2 dimension (local embeddings)'
    """)
    
    # Recreate HNSW index for 384-dimension vectors
    print("Creating new HNSW index for 384-dimension vectors...")
    op.execute("""
        CREATE INDEX idx_framework_documentation_embedding 
        ON framework_documentation 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    
    print("✓ Migration complete. Please re-ingest documentation with:")
    print("  cd backend && python scripts/ingest_documentation.py --all")


def downgrade() -> None:
    """
    Downgrade schema back to 1536-dimension embeddings.
    
    WARNING: This will truncate all data and require re-ingestion with OpenAI embeddings.
    """
    # Drop the 384-dim HNSW index
    print("Dropping 384-dim HNSW index...")
    op.execute("DROP INDEX IF EXISTS idx_framework_documentation_embedding")
    
    # Truncate existing data
    print("Truncating existing data...")
    op.execute("TRUNCATE TABLE framework_documentation")
    
    # Alter back to 1536 dimensions
    print("Altering embedding column back to 1536 dimensions...")
    op.execute("""
        ALTER TABLE framework_documentation 
        ALTER COLUMN embedding TYPE vector(1536)
    """)
    
    # Update the comment
    op.execute("""
        COMMENT ON COLUMN framework_documentation.embedding IS 
        'text-embedding-3-small dimension'
    """)
    
    # Recreate HNSW index for 1536-dimension vectors
    print("Creating HNSW index for 1536-dimension vectors...")
    op.execute("""
        CREATE INDEX idx_framework_documentation_embedding 
        ON framework_documentation 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    
    print("✓ Downgrade complete. Please re-ingest documentation with OpenAI embeddings.")
