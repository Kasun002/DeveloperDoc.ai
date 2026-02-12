"""
Framework Documentation model for AI Agent System.

This module defines the SQLAlchemy ORM model for framework documentation
with pgvector embeddings for semantic search.
"""

from datetime import datetime

from app.core.database import Base
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB


class FrameworkDocumentation(Base):
    """
    Framework Documentation model for storing documentation with embeddings.

    This model stores framework documentation chunks with their vector embeddings
    for semantic search using pgvector. Supports multiple frameworks including
    NestJS, React, FastAPI, Spring Boot, .NET Core, Vue.js, Angular, Django,
    Express.js, and others.

    Attributes:
        id: Primary key, auto-incrementing integer
        content: The documentation text content
        embedding: Vector embedding (1536 dimensions for text-embedding-3-small)
        doc_metadata: JSONB field for flexible metadata storage (mapped to 'metadata' column)
        source: URL or file path of the documentation source
        framework: Framework name (e.g., "NestJS", "React", "FastAPI")
        section: Documentation section (e.g., "Controllers", "Hooks")
        version: Framework version (e.g., "10.x", "18.2")
        created_at: Timestamp when the record was created
        updated_at: Timestamp when the record was last updated
    """

    __tablename__ = "framework_documentation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=False, comment="all-MiniLM-L6-v2 dimension (local embeddings)")
    doc_metadata = Column(JSONB, nullable=False, server_default="{}", name="metadata")
    source = Column(String(500), nullable=False, comment="URL or file path")
    framework = Column(String(100), nullable=False, comment="NestJS, React, FastAPI, etc.")
    section = Column(String(200), nullable=True, comment="Documentation section")
    version = Column(String(50), nullable=True, comment="Framework version")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return (
            f"<FrameworkDocumentation(id={self.id}, framework={self.framework}, "
            f"section={self.section}, version={self.version})>"
        )


# Create indexes for performance
# Note: HNSW index on embedding is created in the migration using raw SQL
# as it requires pgvector-specific syntax
Index("idx_framework_documentation_metadata", FrameworkDocumentation.doc_metadata, postgresql_using="gin")
Index("idx_framework_documentation_framework", FrameworkDocumentation.framework)
Index("idx_framework_documentation_source", FrameworkDocumentation.source)
Index("idx_framework_documentation_framework_version", FrameworkDocumentation.framework, FrameworkDocumentation.version)
