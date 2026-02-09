-- Initialize pgvector extension for AI Agent System
-- This script runs automatically when the PostgreSQL container starts

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extension is installed
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- Log success
DO $$
BEGIN
    RAISE NOTICE 'pgvector extension initialized successfully';
END $$;
