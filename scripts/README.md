# AI Agent System - Scripts

This directory contains utility scripts for managing the AI Agent System.

## Available Scripts

### 1. migrate.sh - Database Migration Script

Runs Alembic database migrations to set up or update the database schema.

**Usage:**
```bash
# From project root
./scripts/migrate.sh

# Or from within Docker container
docker-compose exec fastapi-app ./scripts/migrate.sh
```

**What it does:**
- Checks for required environment variables
- Runs Alembic migrations (`alembic upgrade head`)
- Shows current migration status
- Displays migration history

**Requirements:**
- Alembic installed (`pip install alembic`)
- DATABASE_URL environment variable set
- PostgreSQL database running

---

### 2. ingest_docs.sh - Documentation Ingestion Script

Downloads and ingests framework documentation into the vector database.

**Usage:**
```bash
# Ingest all supported frameworks
./scripts/ingest_docs.sh

# Ingest specific frameworks
./scripts/ingest_docs.sh --frameworks nestjs,react,fastapi

# Force re-ingestion (overwrite existing docs)
./scripts/ingest_docs.sh --force

# Combine options
./scripts/ingest_docs.sh --frameworks nestjs,react --force

# Show help
./scripts/ingest_docs.sh --help
```

**Supported Frameworks:**
- nestjs
- react
- fastapi
- spring-boot
- dotnet-core
- vuejs
- angular
- django
- expressjs

**What it does:**
- Downloads official documentation for specified frameworks
- Parses documentation into chunks
- Generates embeddings using OpenAI's text-embedding-3-small
- Stores embeddings in the vector database (pgvector)
- Adds metadata (framework, version, section, source URL)

**Requirements:**
- Python 3.10+
- VECTOR_DATABASE_URL environment variable set
- OPENAI_API_KEY environment variable set
- PostgreSQL with pgvector extension running
- Documentation ingestion service implemented

---

## Running Scripts in Docker

All scripts can be run inside Docker containers:

```bash
# Run migrations
docker-compose exec fastapi-app ./scripts/migrate.sh

# Run documentation ingestion
docker-compose exec fastapi-app ./scripts/ingest_docs.sh

# Run with specific frameworks
docker-compose exec fastapi-app ./scripts/ingest_docs.sh --frameworks nestjs,react
```

---

## Troubleshooting

### Migration Script Issues

**Error: "Alembic is not installed"**
- Install Alembic: `pip install alembic`
- Or rebuild Docker images: `docker-compose build --no-cache`

**Error: "DATABASE_URL is not set"**
- Check your `.env` or `.env.local` file in the `backend/` directory
- Ensure DATABASE_URL is properly formatted: `postgresql://user:password@host:port/database`

**Error: "Can't locate revision identified by..."**
- Your database might be out of sync with migrations
- Try: `alembic stamp head` to mark current state
- Or drop and recreate the database (development only!)

### Ingestion Script Issues

**Error: "OPENAI_API_KEY is not set"**
- Add your OpenAI API key to `.env` or `.env.local`
- Get an API key from: https://platform.openai.com/api-keys

**Error: "VECTOR_DATABASE_URL is not set"**
- Check your `.env` or `.env.local` file
- Ensure VECTOR_DATABASE_URL points to PostgreSQL with pgvector

**Error: "Failed to import ingestion service"**
- The ingestion service may not be implemented yet
- Check if `app/services/documentation_ingestion_service.py` exists
- The script will create a basic runner if the service is missing

**Slow ingestion:**
- Documentation ingestion can take 10-30 minutes depending on frameworks
- Use `--frameworks` to ingest only specific frameworks
- OpenAI API rate limits may slow down embedding generation

---

## Development Tips

### Creating New Migration

```bash
cd backend
alembic revision -m "description of changes"
# Edit the generated migration file
alembic upgrade head
```

### Checking Migration Status

```bash
cd backend
alembic current
alembic history
```

### Rolling Back Migration

```bash
cd backend
alembic downgrade -1  # Go back one migration
alembic downgrade <revision_id>  # Go to specific revision
```

### Testing Ingestion Locally

```bash
# Set environment variables
export VECTOR_DATABASE_URL="postgresql://vector_admin:vector123@localhost:5433/ai_agent_vectors"
export OPENAI_API_KEY="your-api-key"

# Run ingestion for one framework
./scripts/ingest_docs.sh --frameworks nestjs
```

---

## Script Maintenance

When adding new scripts:
1. Add a shebang line: `#!/bin/bash`
2. Use `set -e` to exit on errors
3. Add colored output for better UX
4. Include `--help` option
5. Make executable: `chmod +x scripts/your_script.sh`
6. Update this README with usage instructions
