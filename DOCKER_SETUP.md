# AI Agent System - Docker Setup Guide

This guide explains how to set up and run the AI Agent System using Docker Compose for local development.

## Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- OpenAI API Key
- At least 4GB of available RAM
- At least 10GB of available disk space

## Quick Start

1. **Clone the repository and navigate to the project root**

2. **Set up environment variables**
   ```bash
   # Copy the example environment file
   cp backend/.env.example backend/.env
   
   # Edit backend/.env and add your OpenAI API key
   # Required: OPENAI_API_KEY=your-api-key-here
   ```

3. **Start all services**
   ```bash
   ./run_local.sh
   ```

4. **Access the application**
   - FastAPI App: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - MCP Tool Service: http://localhost:8001

## Services Overview

The docker-compose setup includes the following services:

### Core Services

| Service | Port | Description |
|---------|------|-------------|
| **postgres** | 5432 | PostgreSQL database for authentication and basic operations |
| **postgres-vector** | 5433 | PostgreSQL with pgvector extension for vector embeddings |
| **redis** | 6379 | Redis for semantic cache and tool cache |
| **fastapi-app** | 8000 | Main FastAPI application (AI Agent System) |
| **mcp-tool** | 8001 | MCP Tool service for documentation search |

### Development Services (Optional)

| Service | Port | Description |
|---------|------|-------------|
| **pgadmin** | 5050 | PostgreSQL management UI |
| **redis-commander** | 8081 | Redis management UI |

## Usage

### Starting Services

**Basic mode (core services only):**
```bash
./run_local.sh
```

**Development mode (with management tools):**
```bash
./run_local.sh --dev
```

**Rebuild images before starting:**
```bash
./run_local.sh --rebuild
```

**Combine options:**
```bash
./run_local.sh --dev --rebuild
```

### Stopping Services

```bash
docker-compose down
```

**Stop and remove volumes (WARNING: deletes all data):**
```bash
docker-compose down -v
```

### Viewing Logs

**All services:**
```bash
docker-compose logs -f
```

**Specific service:**
```bash
docker-compose logs -f fastapi-app
docker-compose logs -f postgres-vector
docker-compose logs -f redis
```

### Restarting Services

**All services:**
```bash
docker-compose restart
```

**Specific service:**
```bash
docker-compose restart fastapi-app
```

## Database Setup

### Running Migrations

After starting the services for the first time, run database migrations:

```bash
./scripts/migrate.sh
```

Or from within Docker:
```bash
docker-compose exec fastapi-app alembic upgrade head
```

### Accessing Databases

**PostgreSQL (main database):**
```bash
# Using psql
docker-compose exec postgres psql -U admin -d ai_admin

# Connection string
postgresql://admin:admin123@localhost:5432/ai_admin
```

**PostgreSQL (vector database):**
```bash
# Using psql
docker-compose exec postgres-vector psql -U vector_admin -d ai_agent_vectors

# Connection string
postgresql://vector_admin:vector123@localhost:5433/ai_agent_vectors
```

**Redis:**
```bash
# Using redis-cli
docker-compose exec redis redis-cli

# Connection string
redis://localhost:6379/0
```

### Using pgAdmin (Development Mode)

1. Start services in dev mode: `./run_local.sh --dev`
2. Open http://localhost:5050
3. Login with:
   - Email: `admin@example.com`
   - Password: `admin`
4. Add servers:
   - **Main Database:**
     - Host: `postgres`
     - Port: `5432`
     - Database: `ai_admin`
     - Username: `admin`
     - Password: `admin123`
   - **Vector Database:**
     - Host: `postgres-vector`
     - Port: `5432`
     - Database: `ai_agent_vectors`
     - Username: `vector_admin`
     - Password: `vector123`

### Using Redis Commander (Development Mode)

1. Start services in dev mode: `./run_local.sh --dev`
2. Open http://localhost:8081
3. Redis connection is pre-configured

## Documentation Ingestion

After setting up the databases, ingest framework documentation:

```bash
# Ingest all supported frameworks
./scripts/ingest_docs.sh

# Ingest specific frameworks
./scripts/ingest_docs.sh --frameworks nestjs,react,fastapi

# Force re-ingestion
./scripts/ingest_docs.sh --force
```

This process:
- Downloads official documentation for specified frameworks
- Generates embeddings using OpenAI
- Stores embeddings in the vector database
- Can take 10-30 minutes depending on the number of frameworks

## Environment Variables

Key environment variables (set in `backend/.env`):

### Required
- `OPENAI_API_KEY` - Your OpenAI API key
- `DATABASE_URL` - Main PostgreSQL connection string
- `VECTOR_DATABASE_URL` - Vector database connection string
- `JWT_SECRET_KEY` - Secret key for JWT tokens (generate with `openssl rand -hex 32`)

### Optional (with defaults)
- `REDIS_URL` - Redis connection string
- `SEMANTIC_CACHE_THRESHOLD` - Similarity threshold for semantic cache (default: 0.95)
- `SEMANTIC_CACHE_TTL` - Cache TTL in seconds (default: 3600)
- `TOOL_CACHE_TTL` - Tool cache TTL in seconds (default: 300)
- `MAX_WORKFLOW_ITERATIONS` - Max LangGraph iterations (default: 3)
- `VECTOR_SEARCH_TOP_K` - Number of search results (default: 10)
- `VECTOR_SEARCH_MIN_SCORE` - Minimum relevance score (default: 0.7)

See `backend/.env.example` for all available options.

## Troubleshooting

### Services Won't Start

**Check Docker is running:**
```bash
docker info
```

**Check for port conflicts:**
```bash
# Check if ports are already in use
lsof -i :5432  # PostgreSQL
lsof -i :5433  # PostgreSQL Vector
lsof -i :6379  # Redis
lsof -i :8000  # FastAPI
lsof -i :8001  # MCP Tool
```

**View service logs:**
```bash
docker-compose logs
```

### Database Connection Errors

**Error: "could not connect to server"**
- Wait a few seconds for databases to initialize
- Check if containers are running: `docker-compose ps`
- Check logs: `docker-compose logs postgres postgres-vector`

**Error: "database does not exist"**
- Run migrations: `./scripts/migrate.sh`
- Or manually: `docker-compose exec fastapi-app alembic upgrade head`

### OpenAI API Errors

**Error: "OPENAI_API_KEY is not set"**
- Add your API key to `backend/.env`
- Restart services: `docker-compose restart`

**Error: "Rate limit exceeded"**
- OpenAI has rate limits on API calls
- Wait a few minutes and try again
- Consider upgrading your OpenAI plan

### Performance Issues

**Slow startup:**
- First startup downloads images and builds containers (5-10 minutes)
- Subsequent startups are much faster (30-60 seconds)

**High memory usage:**
- The system requires ~4GB RAM for all services
- Close unnecessary applications
- Increase Docker Desktop memory limit (Preferences → Resources)

**Slow documentation ingestion:**
- Ingestion can take 10-30 minutes
- Use `--frameworks` to ingest only needed frameworks
- OpenAI API rate limits may slow down the process

## Development Workflow

### Making Code Changes

The FastAPI app uses hot-reload, so code changes are reflected immediately:

1. Edit files in `backend/app/`
2. Save the file
3. The FastAPI app automatically reloads
4. Check logs: `docker-compose logs -f fastapi-app`

### Adding Database Migrations

1. Make changes to models in `backend/app/models/`
2. Create migration:
   ```bash
   docker-compose exec fastapi-app alembic revision --autogenerate -m "description"
   ```
3. Review the generated migration in `backend/alembic/versions/`
4. Apply migration:
   ```bash
   docker-compose exec fastapi-app alembic upgrade head
   ```

### Running Tests

```bash
# Run all tests
docker-compose exec fastapi-app pytest

# Run specific test file
docker-compose exec fastapi-app pytest tests/test_agents.py

# Run with coverage
docker-compose exec fastapi-app pytest --cov=app tests/
```

### Accessing Python Shell

```bash
# Python shell with app context
docker-compose exec fastapi-app python

# IPython (if installed)
docker-compose exec fastapi-app ipython
```

## Production Considerations

This docker-compose setup is for **local development only**. For production:

1. **Use managed services:**
   - Managed PostgreSQL (AWS RDS, Google Cloud SQL, etc.)
   - Managed Redis (AWS ElastiCache, Redis Cloud, etc.)
   - Container orchestration (Kubernetes, ECS, etc.)

2. **Security:**
   - Change all default passwords
   - Use strong JWT secret keys
   - Enable SSL/TLS for all connections
   - Use secrets management (AWS Secrets Manager, HashiCorp Vault, etc.)

3. **Scaling:**
   - Run multiple FastAPI instances behind a load balancer
   - Use connection pooling for databases
   - Configure Redis for high availability

4. **Monitoring:**
   - Set up proper logging aggregation
   - Use OpenTelemetry with a real backend (Jaeger, Datadog, etc.)
   - Monitor resource usage and set up alerts

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## Support

For issues or questions:
1. Check the logs: `docker-compose logs`
2. Review this documentation
3. Check the main README.md
4. Open an issue on GitHub
