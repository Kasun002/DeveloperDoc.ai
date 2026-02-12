#!/bin/bash
# Migration script to switch from OpenAI embeddings to local embeddings
# This script will:
# 1. Run the Alembic migration to change embedding dimension from 1536 to 384
# 2. Re-ingest documentation using local embeddings (no API key needed)

set -e  # Exit on error

echo "=========================================="
echo "MIGRATING TO LOCAL EMBEDDINGS (384-dim)"
echo "=========================================="
echo ""
echo "This will:"
echo "  1. Change embedding dimension from 1536 to 384"
echo "  2. Clear existing documentation (incompatible dimensions)"
echo "  3. Re-ingest documentation using local embeddings"
echo ""
echo "⚠️  WARNING: All existing documentation will be cleared!"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled."
    exit 1
fi

echo ""
echo "Step 1: Running Alembic migration..."
echo "------------------------------------"
cd "$(dirname "$0")"
alembic upgrade head

if [ $? -ne 0 ]; then
    echo "❌ Migration failed!"
    exit 1
fi

echo ""
echo "✓ Migration complete!"
echo ""
echo "Step 2: Re-ingesting documentation with local embeddings..."
echo "-----------------------------------------------------------"
echo ""

# Check if scraped docs exist
if [ ! -d "../docs/scraped" ]; then
    echo "⚠️  No scraped documentation found in docs/scraped/"
    echo ""
    echo "Please run documentation scraping first:"
    echo "  cd backend && python scripts/scrape_documentation.py --all"
    exit 1
fi

# Re-ingest all documentation
python scripts/ingest_documentation.py --all --force

if [ $? -ne 0 ]; then
    echo "❌ Documentation ingestion failed!"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ MIGRATION COMPLETE!"
echo "=========================================="
echo ""
echo "Your system is now using local embeddings (no API quota limits)."
echo ""
echo "Next steps:"
echo "  1. Start the backend: uvicorn app.main:app --reload"
echo "  2. Test vector search with the Documentation Search Agent"
echo ""
