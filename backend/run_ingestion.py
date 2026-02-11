#!/usr/bin/env python3
"""
Documentation Ingestion Runner
Runs the documentation ingestion service to populate the vector database.
"""

import asyncio
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def main():
    try:
        from app.services.documentation_ingestion_service import DocumentationIngestionService
        
        print("Starting documentation ingestion...")
        
        # Get frameworks from environment or use defaults
        frameworks_str = os.getenv('FRAMEWORKS', '')
        frameworks = [f.strip() for f in frameworks_str.split(',') if f.strip()]
        
        if not frameworks:
            frameworks = [
                'nestjs', 'react', 'fastapi', 'spring-boot', 
                'dotnet-core', 'vuejs', 'angular', 'django', 'expressjs'
            ]
        
        force = os.getenv('FORCE', 'false').lower() == 'true'
        
        print(f"Ingesting documentation for: {', '.join(frameworks)}")
        print(f"Force re-ingestion: {force}")
        
        service = DocumentationIngestionService()
        
        for framework in frameworks:
            print(f"\n--- Processing {framework} ---")
            try:
                await service.ingest_framework_documentation(framework, force=force)
                print(f"✓ Successfully ingested {framework} documentation")
            except Exception as e:
                print(f"✗ Failed to ingest {framework}: {str(e)}")
        
        print("\n✓ Documentation ingestion completed")
        
    except ImportError as e:
        print(f"✗ Failed to import ingestion service: {str(e)}")
        print("The ingestion service may not be implemented yet.")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Ingestion failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
