"""create_semantic_cache_table

Revision ID: 7048d18b575d
Revises: bae3a0c66742
Create Date: 2026-02-09 17:30:16.294284

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7048d18b575d'
down_revision: Union[str, Sequence[str], None] = 'bae3a0c66742'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create semantic_cache table for similarity-based cache lookups
    op.execute("""
        CREATE TABLE IF NOT EXISTS semantic_cache (
            id SERIAL PRIMARY KEY,
            prompt TEXT NOT NULL UNIQUE,
            response TEXT NOT NULL,
            embedding vector(1536) NOT NULL,
            cached_at TIMESTAMP NOT NULL DEFAULT NOW(),
            ttl INTEGER NOT NULL DEFAULT 3600,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Create HNSW index for fast similarity search
    op.execute("""
        CREATE INDEX IF NOT EXISTS semantic_cache_embedding_idx 
        ON semantic_cache 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    
    # Create index on cached_at for TTL cleanup
    op.execute("""
        CREATE INDEX IF NOT EXISTS semantic_cache_cached_at_idx 
        ON semantic_cache (cached_at)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS semantic_cache CASCADE")
