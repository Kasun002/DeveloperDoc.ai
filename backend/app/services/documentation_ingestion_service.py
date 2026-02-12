"""
Documentation Ingestion Service

This service provides a high-level interface for ingesting framework documentation
into the vector database. It wraps the DocumentationIngestionPipeline from the
scripts directory.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional

# Add scripts directory to path
scripts_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts')
sys.path.insert(0, scripts_dir)

from ingest_documentation import DocumentationIngestionPipeline


class DocumentationIngestionService:
    """
    Service for ingesting framework documentation with embeddings.
    
    This service provides a simplified interface for the documentation ingestion
    pipeline, making it easy to ingest documentation from application code.
    """
    
    def __init__(self, batch_size: int = 10):
        """
        Initialize the ingestion service.
        
        Args:
            batch_size: Number of documents to process in each batch
        """
        self.batch_size = batch_size
        self.docs_dir = Path(__file__).parent.parent.parent / "docs" / "scraped"
    
    async def ingest_framework_documentation(
        self, 
        framework: str, 
        force: bool = False
    ) -> int:
        """
        Ingest documentation for a specific framework.
        
        Args:
            framework: Framework name (e.g., 'nestjs', 'react', 'fastapi')
            force: If True, re-ingest existing documents
            
        Returns:
            Number of documents ingested
            
        Raises:
            FileNotFoundError: If documentation file doesn't exist
            ValueError: If framework is invalid
        """
        input_file = self.docs_dir / f"{framework}_docs.json"
        
        if not input_file.exists():
            raise FileNotFoundError(
                f"Documentation file not found: {input_file}\n"
                f"Run scraping first: python scripts/scrape_documentation.py --framework {framework}"
            )
        
        pipeline = DocumentationIngestionPipeline(batch_size=self.batch_size)
        
        try:
            # Load documents
            docs = await pipeline.load_scraped_docs(input_file)
            print(f"✓ Loaded {len(docs)} documents from {input_file}")
            
            # Ingest documents
            skip_existing = not force
            ingested_count = await pipeline.ingest_documents(docs, skip_existing=skip_existing)
            
            # Verify ingestion
            if ingested_count > 0:
                print(f"Verifying ingestion...")
                verification = await pipeline.verify_ingestion(docs[0]["framework"])
                print(f"✓ Database contains {verification['count']} documents for {framework}")
            
            return ingested_count
            
        finally:
            await pipeline.close()
    
    async def ingest_all_frameworks(
        self, 
        frameworks: Optional[List[str]] = None,
        force: bool = False
    ) -> Dict[str, int]:
        """
        Ingest documentation for multiple frameworks.
        
        Args:
            frameworks: List of framework names. If None, ingest all available.
            force: If True, re-ingest existing documents
            
        Returns:
            Dictionary mapping framework names to number of documents ingested
        """
        results = {}
        
        # If no frameworks specified, find all JSON files
        if frameworks is None:
            json_files = list(self.docs_dir.glob("*_docs.json"))
            frameworks = [f.stem.replace("_docs", "") for f in json_files]
        
        if not frameworks:
            print(f"⚠ No documentation files found in {self.docs_dir}")
            return results
        
        print(f"\nIngesting documentation for {len(frameworks)} frameworks...")
        
        for framework in frameworks:
            try:
                count = await self.ingest_framework_documentation(framework, force=force)
                results[framework] = count
                print(f"✓ {framework}: {count} documents ingested")
            except Exception as e:
                print(f"✗ {framework}: {str(e)}")
                results[framework] = 0
        
        return results
    
    async def verify_framework_documentation(self, framework: str) -> Dict:
        """
        Verify that documentation exists for a framework.
        
        Args:
            framework: Framework name
            
        Returns:
            Dictionary with count and sample document
        """
        pipeline = DocumentationIngestionPipeline(batch_size=self.batch_size)
        
        try:
            verification = await pipeline.verify_ingestion(framework)
            return verification
        finally:
            await pipeline.close()
    
    async def get_ingestion_status(self) -> Dict[str, int]:
        """
        Get ingestion status for all frameworks.
        
        Returns:
            Dictionary mapping framework names to document counts
        """
        pipeline = DocumentationIngestionPipeline(batch_size=self.batch_size)
        
        try:
            # Get all available frameworks from docs directory
            json_files = list(self.docs_dir.glob("*_docs.json"))
            frameworks = [f.stem.replace("_docs", "") for f in json_files]
            
            status = {}
            for framework in frameworks:
                verification = await pipeline.verify_ingestion(framework)
                status[framework] = verification['count']
            
            return status
            
        finally:
            await pipeline.close()


# Convenience function for backward compatibility
async def ingest_framework(framework: str, force: bool = False) -> int:
    """
    Convenience function to ingest a single framework.
    
    Args:
        framework: Framework name
        force: If True, re-ingest existing documents
        
    Returns:
        Number of documents ingested
    """
    service = DocumentationIngestionService()
    return await service.ingest_framework_documentation(framework, force=force)


async def ingest_all(frameworks: Optional[List[str]] = None, force: bool = False) -> Dict[str, int]:
    """
    Convenience function to ingest multiple frameworks.
    
    Args:
        frameworks: List of framework names. If None, ingest all available.
        force: If True, re-ingest existing documents
        
    Returns:
        Dictionary mapping framework names to number of documents ingested
    """
    service = DocumentationIngestionService()
    return await service.ingest_all_frameworks(frameworks, force=force)
