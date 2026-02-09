"""create_framework_documentation_table

Revision ID: bae3a0c66742
Revises: afcd0aaaf25d
Create Date: 2026-02-09 16:38:26.558018

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'bae3a0c66742'
down_revision: Union[str, Sequence[str], None] = 'afcd0aaaf25d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Ensure pgvector extension is enabled
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create framework_documentation table
    op.create_table(
        "framework_documentation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "embedding",
            Vector(1536),
            nullable=False,
            comment="text-embedding-3-small dimension"
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("source", sa.String(500), nullable=False, comment="URL or file path"),
        sa.Column("framework", sa.String(100), nullable=False, comment="NestJS, React, FastAPI, etc."),
        sa.Column("section", sa.String(200), nullable=True, comment="Documentation section"),
        sa.Column("version", sa.String(50), nullable=True, comment="Framework version"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id")
    )
    
    # Create HNSW index for fast similarity search on embedding column
    # Using raw SQL for pgvector-specific index
    op.execute("""
        CREATE INDEX idx_framework_documentation_embedding 
        ON framework_documentation 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    
    # Create GIN index for metadata queries
    op.create_index(
        "idx_framework_documentation_metadata",
        "framework_documentation",
        ["metadata"],
        postgresql_using="gin"
    )
    
    # Create index on framework for filtering
    op.create_index(
        "idx_framework_documentation_framework",
        "framework_documentation",
        ["framework"]
    )
    
    # Create index on source for deduplication
    op.create_index(
        "idx_framework_documentation_source",
        "framework_documentation",
        ["source"]
    )
    
    # Create composite index for framework + version queries
    op.create_index(
        "idx_framework_documentation_framework_version",
        "framework_documentation",
        ["framework", "version"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index("idx_framework_documentation_framework_version", table_name="framework_documentation")
    op.drop_index("idx_framework_documentation_source", table_name="framework_documentation")
    op.drop_index("idx_framework_documentation_framework", table_name="framework_documentation")
    op.drop_index("idx_framework_documentation_metadata", table_name="framework_documentation")
    op.execute("DROP INDEX IF EXISTS idx_framework_documentation_embedding")
    
    # Drop table
    op.drop_table("framework_documentation")
