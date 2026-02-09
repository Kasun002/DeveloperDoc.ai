#!/bin/bash

# Documentation Ingestion Script
# This script downloads and ingests framework documentation into the vector database

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_message "$BLUE" "=========================================="
print_message "$BLUE" "AI Agent System - Documentation Ingestion"
print_message "$BLUE" "=========================================="
echo ""

# Parse command line arguments
FRAMEWORKS=""
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --frameworks)
            FRAMEWORKS="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help)
            echo "Usage: ./scripts/ingest_docs.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --frameworks NAMES  Comma-separated list of frameworks to ingest"
            echo "                      (e.g., 'nestjs,react,fastapi')"
            echo "                      If not specified, ingests all supported frameworks"
            echo "  --force             Force re-ingestion even if docs already exist"
            echo "  --help              Show this help message"
            echo ""
            echo "Supported frameworks:"
            echo "  - nestjs"
            echo "  - react"
            echo "  - fastapi"
            echo "  - spring-boot"
            echo "  - dotnet-core"
            echo "  - vuejs"
            echo "  - angular"
            echo "  - django"
            echo "  - expressjs"
            exit 0
            ;;
        *)
            print_message "$RED" "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if running in Docker or local
if [ -f "/.dockerenv" ]; then
    # Running inside Docker container
    print_message "$BLUE" "Running ingestion inside Docker container..."
    cd /app
else
    # Running on host machine
    print_message "$BLUE" "Running ingestion on host machine..."
    
    # Check if backend directory exists
    if [ ! -d "backend" ]; then
        print_message "$RED" "✗ backend directory not found. Please run this script from the project root."
        exit 1
    fi
    
    cd backend
    
    # Check if .env file exists
    if [ ! -f ".env" ] && [ ! -f ".env.local" ]; then
        print_message "$RED" "✗ No .env or .env.local file found in backend/"
        print_message "$YELLOW" "Please create one from .env.example"
        exit 1
    fi
    
    # Load environment variables
    if [ -f ".env.local" ]; then
        export $(cat .env.local | grep -v '^#' | xargs)
    elif [ -f ".env" ]; then
        export $(cat .env | grep -v '^#' | xargs)
    fi
    
    # Check if required environment variables are set
    if [ -z "$VECTOR_DATABASE_URL" ]; then
        print_message "$RED" "✗ VECTOR_DATABASE_URL is not set in .env file"
        exit 1
    fi
    
    if [ -z "$OPENAI_API_KEY" ]; then
        print_message "$RED" "✗ OPENAI_API_KEY is not set in .env file"
        exit 1
    fi
    
    print_message "$GREEN" "✓ Environment loaded"
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_message "$RED" "✗ Python 3 is not installed"
    exit 1
fi

print_message "$GREEN" "✓ Python 3 is available"

# Check if ingestion script exists
INGESTION_SCRIPT="app/services/documentation_ingestion_service.py"

if [ ! -f "$INGESTION_SCRIPT" ]; then
    print_message "$YELLOW" "⚠ Ingestion service not found at $INGESTION_SCRIPT"
    print_message "$YELLOW" "Creating a basic ingestion runner..."
    
    # Create a simple ingestion runner
    cat > run_ingestion.py << 'EOF'
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
EOF
    
    chmod +x run_ingestion.py
    INGESTION_SCRIPT="run_ingestion.py"
fi

# Set environment variables for the ingestion script
if [ -n "$FRAMEWORKS" ]; then
    export FRAMEWORKS="$FRAMEWORKS"
fi

if [ "$FORCE" = true ]; then
    export FORCE="true"
fi

# Run the ingestion
print_message "$BLUE" "Starting documentation ingestion..."
echo ""

python3 "$INGESTION_SCRIPT"

echo ""
print_message "$GREEN" "✓ Documentation ingestion completed"
echo ""
print_message "$BLUE" "You can now query the documentation through the AI Agent API"
