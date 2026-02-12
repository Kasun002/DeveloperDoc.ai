#!/usr/bin/env python3
"""
Documentation ingestion pipeline for AI Agent System.

This script processes scraped documentation, generates embeddings using
OpenAI's text-embedding-3-small model, and stores them in the PostgreSQL
database with pgvector for semantic search.

Usage:
    python ingest_documentation.py --input docs/scraped --framework nestjs
    python ingest_documentation.py --input docs/scraped --all
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.models.framework_documentation import FrameworkDocumentation
# Use local embedding service to avoid OpenAI quota issues
from app.services.local_embedding_service import LocalEmbeddingService as EmbeddingService


class DocumentationIngestionPipeline:
    """Pipeline for ingesting documentation with embeddings."""
    
    def __init__(self, batch_size: int = 10):
        """
        Initialize the ingestion pipeline.
        
        Args:
            batch_size: Number of documents to process in each batch
        """
        self.batch_size = batch_size
        # Use local embedding service (384 dimensions, no API needed)
        print("Initializing local embedding service (no API key required)...")
        self.embedding_service = EmbeddingService(
            model_name="all-MiniLM-L6-v2",  # Fast, free, local model
            dimension=384  # Smaller dimension, but works great
        )
        
        # Create async engine for vector database
        if not settings.vector_database_url:
            raise ValueError("VECTOR_DATABASE_URL not configured in settings")
        
        # Convert postgresql:// to postgresql+asyncpg://
        db_url = settings.vector_database_url
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not db_url.startswith("postgresql+asyncpg://"):
            db_url = f"postgresql+asyncpg://{db_url}"
        
        self.engine = create_async_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        
        self.async_session_maker = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def load_scraped_docs(self, input_file: Path) -> List[Dict]:
        """Load scraped documentation from JSON file."""
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            docs = json.load(f)
        
        return docs
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        try:
            embeddings = await self.embedding_service.embed_batch(texts)
            return embeddings
        except Exception as e:
            print(f"⚠ Error generating embeddings: {e}")
            # Fallback to individual embedding generation
            embeddings = []
            for text in texts:
                try:
                    embedding = await self.embedding_service.embed_text(text)
                    embeddings.append(embedding)
                except Exception as e:
                    print(f"⚠ Error generating embedding for text: {e}")
                    embeddings.append(None)
            return embeddings
    
    async def check_existing_docs(
        self, 
        session: AsyncSession, 
        framework: str, 
        sources: List[str]
    ) -> set:
        """Check which documents already exist in the database."""
        result = await session.execute(
            text(
                "SELECT source FROM framework_documentation "
                "WHERE framework = :framework AND source = ANY(:sources)"
            ),
            {"framework": framework, "sources": sources}
        )
        existing = {row[0] for row in result.fetchall()}
        return existing
    
    async def ingest_documents(
        self, 
        docs: List[Dict], 
        skip_existing: bool = True
    ) -> int:
        """
        Ingest documents into the database with embeddings.
        
        Args:
            docs: List of document dictionaries
            skip_existing: If True, skip documents that already exist
            
        Returns:
            Number of documents ingested
        """
        if not docs:
            print("⚠ No documents to ingest")
            return 0
        
        framework = docs[0].get("framework", "Unknown")
        print(f"\nProcessing {len(docs)} documents for {framework}...")
        
        async with self.async_session_maker() as session:
            # Check existing documents
            existing_sources = set()
            if skip_existing:
                sources = [doc["source"] for doc in docs]
                existing_sources = await self.check_existing_docs(
                    session, framework, sources
                )
                if existing_sources:
                    print(f"⚠ Skipping {len(existing_sources)} existing documents")
            
            # Filter out existing documents
            docs_to_process = [
                doc for doc in docs 
                if not skip_existing or doc["source"] not in existing_sources
            ]
            
            if not docs_to_process:
                print("✓ All documents already exist in database")
                return 0
            
            print(f"Generating embeddings for {len(docs_to_process)} documents...")
            
            ingested_count = 0
            
            # Process in batches
            for i in range(0, len(docs_to_process), self.batch_size):
                batch = docs_to_process[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                total_batches = (len(docs_to_process) + self.batch_size - 1) // self.batch_size
                
                print(f"  Processing batch {batch_num}/{total_batches}...")
                
                # Extract texts for embedding
                texts = [doc["content"] for doc in batch]
                
                # Generate embeddings
                embeddings = await self.generate_embeddings_batch(texts)
                
                # Create database records
                for doc, embedding in zip(batch, embeddings):
                    if embedding is None:
                        print(f"  ⚠ Skipping document (no embedding): {doc['source']}")
                        continue
                    
                    db_doc = FrameworkDocumentation(
                        content=doc["content"],
                        embedding=embedding,
                        source=doc["source"],
                        framework=doc["framework"],
                        section=doc.get("section"),
                        version=doc.get("version"),
                        doc_metadata=doc.get("metadata", {})
                    )
                    session.add(db_doc)
                    ingested_count += 1
                
                # Commit batch
                try:
                    await session.commit()
                    print(f"  ✓ Batch {batch_num}/{total_batches} committed")
                except Exception as e:
                    await session.rollback()
                    print(f"  ❌ Error committing batch: {e}")
                    raise
            
            print(f"\n✓ Successfully ingested {ingested_count} documents")
            return ingested_count
    
    async def verify_ingestion(self, framework: str) -> Dict:
        """Verify ingestion by querying the database."""
        async with self.async_session_maker() as session:
            # Count documents
            result = await session.execute(
                text(
                    "SELECT COUNT(*) FROM framework_documentation "
                    "WHERE framework = :framework"
                ),
                {"framework": framework}
            )
            count = result.scalar()
            
            # Get sample document
            result = await session.execute(
                text(
                    "SELECT id, framework, section, version, source "
                    "FROM framework_documentation "
                    "WHERE framework = :framework "
                    "LIMIT 1"
                ),
                {"framework": framework}
            )
            sample = result.fetchone()
            
            return {
                "count": count,
                "sample": dict(sample._mapping) if sample else None
            }
    
    async def close(self):
        """Close database connections."""
        await self.engine.dispose()


async def ingest_framework(
    input_dir: Path, 
    framework: str, 
    skip_existing: bool = True,
    batch_size: int = 10
) -> int:
    """Ingest documentation for a specific framework."""
    input_file = input_dir / f"{framework}_docs.json"
    
    if not input_file.exists():
        print(f"❌ Documentation file not found: {input_file}")
        print(f"   Run scraping first: python scrape_documentation.py --framework {framework}")
        return 0
    
    print(f"\n{'='*60}")
    print(f"INGESTING {framework.upper()} DOCUMENTATION")
    print(f"{'='*60}")
    
    pipeline = DocumentationIngestionPipeline(batch_size=batch_size)
    
    try:
        # Load documents
        docs = await pipeline.load_scraped_docs(input_file)
        print(f"✓ Loaded {len(docs)} documents from {input_file}")
        
        # Ingest documents
        ingested_count = await pipeline.ingest_documents(docs, skip_existing=skip_existing)
        
        # Verify ingestion
        if ingested_count > 0:
            print(f"\nVerifying ingestion...")
            verification = await pipeline.verify_ingestion(docs[0]["framework"])
            print(f"✓ Database contains {verification['count']} documents for {framework}")
            
            if verification['sample']:
                print(f"\nSample document:")
                for key, value in verification['sample'].items():
                    if key != 'source':
                        print(f"  {key}: {value}")
        
        return ingested_count
        
    finally:
        await pipeline.close()



async def ingest_all_frameworks(
    input_dir: Path, 
    skip_existing: bool = True,
    batch_size: int = 10
) -> Dict[str, int]:
    """Ingest documentation for all frameworks in the input directory."""
    results = {}
    
    # Find all JSON files in input directory
    json_files = list(input_dir.glob("*_docs.json"))
    
    if not json_files:
        print(f"❌ No documentation files found in {input_dir}")
        print(f"   Run scraping first: python scrape_documentation.py --all")
        return results
    
    print(f"\nFound {len(json_files)} framework documentation files")
    
    for json_file in json_files:
        # Extract framework name from filename
        framework = json_file.stem.replace("_docs", "")
        
        try:
            count = await ingest_framework(
                input_dir, 
                framework, 
                skip_existing=skip_existing,
                batch_size=batch_size
            )
            results[framework] = count
        except Exception as e:
            print(f"❌ Error ingesting {framework}: {e}")
            results[framework] = 0
    
    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest framework documentation with embeddings into database"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="docs/scraped",
        help="Input directory containing scraped documentation JSON files"
    )
    parser.add_argument(
        "--framework",
        type=str,
        help="Framework to ingest (e.g., nestjs, react, fastapi)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ingest all frameworks in input directory"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-ingestion of existing documents"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of documents to process in each batch (default: 10)"
    )
    
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    
    if not input_dir.exists():
        print(f"❌ Input directory not found: {input_dir}")
        print(f"   Run scraping first: python scrape_documentation.py")
        return 1
    
    skip_existing = not args.force
    
    try:
        if args.all:
            print("\n" + "="*60)
            print("INGESTING ALL FRAMEWORK DOCUMENTATION")
            print("="*60)
            results = asyncio.run(
                ingest_all_frameworks(input_dir, skip_existing, args.batch_size)
            )
            
            print("\n" + "="*60)
            print("INGESTION SUMMARY")
            print("="*60)
            total = 0
            for framework, count in results.items():
                print(f"  {framework}: {count} documents")
                total += count
            print(f"\nTotal: {total} documents ingested")
            
        elif args.framework:
            count = asyncio.run(
                ingest_framework(input_dir, args.framework, skip_existing, args.batch_size)
            )
            
        else:
            parser.print_help()
            print("\nExample usage:")
            print("  python ingest_documentation.py --framework nestjs")
            print("  python ingest_documentation.py --all")
            print("  python ingest_documentation.py --all --force  # Re-ingest existing docs")
            return 1
        
        print("\n" + "="*60)
        print("INGESTION COMPLETE")
        print("="*60)
        print("\nNext steps:")
        print("1. Verify data: SELECT COUNT(*), framework FROM framework_documentation GROUP BY framework;")
        print("2. Test search: Use Documentation Search Agent")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
