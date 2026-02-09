# Local Development Docker Services

This directory contains Docker Compose configuration for local development infrastructure.

## Services

### 1. PostgreSQL (Main Database) - Port 5432
- **Container**: `pg_local`
- **Image**: `postgres:15`
- **Database**: `ai_admin`
- **User**: `admin`
- **Password**: `admin123`
- **Purpose**: User authentication, basic operations, existing features

**Connection String**:
```
postgresql://admin:admin123@localhost:5432/ai_admin
```

### 2. PostgreSQL with pgvector (Vector Database) - Port 5433
- **Container**: `pg_vector_local`
- **Image**: `pgvector/pgvector:pg16`
- **Database**: `ai_agent_vectors`
- **User**: `vector_admin`
- **Password**: `vector123`
- **Purpose**: AI Agent framework documentation embeddings, vector similarity search

**Connection String**:
```
postgresql://vector_admin:vector123@localhost:5433/ai_agent_vectors
```

**Features**:
- pgvector extension for vector similarity search
- HNSW indexing for fast nearest neighbor search
- Optimized for embedding storage and retrieval

### 3. Redis (Cache) - Port 6379
- **Container**: `redis_local`
- **Image**: `redis:7-alpine`
- **Purpose**: AI Agent caching (semantic cache + tool cache)

**Connection String**:
```
redis://localhost:6379/0
```

**Configuration**:
- Max memory: 256MB
- Eviction policy: allkeys-lru (Least Recently Used)
- Persistence: AOF (Append Only File) enabled

### 4. PgAdmin (Database Management) - Port 5050
- **Container**: `pgadmin_local`
- **Image**: `dpage/pgadmin4`
- **Email**: `admin@local.com`
- **Password**: `admin123`
- **Purpose**: Web-based PostgreSQL management interface

**Access**: http://localhost:5050

## Quick Start

### Start All Services

```bash
cd local-dev-docker
docker-compose -f pg-docker.dockercompose.yml up -d
```

### Start Specific Services

```bash
# Start only main PostgreSQL
docker-compose -f pg-docker.dockercompose.yml up -d postgres

# Start only vector database
docker-compose -f pg-docker.dockercompose.yml up -d postgres_vector

# Start only Redis
docker-compose -f pg-docker.dockercompose.yml up -d redis
```

### Check Service Status

```bash
docker-compose -f pg-docker.dockercompose.yml ps
```

### View Logs

```bash
# All services
docker-compose -f pg-docker.dockercompose.yml logs -f

# Specific service
docker-compose -f pg-docker.dockercompose.yml logs -f postgres_vector
docker-compose -f pg-docker.dockercompose.yml logs -f redis
```

### Stop Services

```bash
# Stop all services
docker-compose -f pg-docker.dockercompose.yml down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose -f pg-docker.dockercompose.yml down -v
```

## Verification

### Verify PostgreSQL (Main)

```bash
# Connect to database
docker exec -it pg_local psql -U admin -d ai_admin

# Inside psql:
\dt              # List tables
\q               # Exit
```

### Verify PostgreSQL with pgvector

```bash
# Connect to vector database
docker exec -it pg_vector_local psql -U vector_admin -d ai_agent_vectors

# Inside psql:
# Check pgvector extension
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

# Test vector operations
SELECT '[1,2,3]'::vector;

\q  # Exit
```

### Verify Redis

```bash
# Connect to Redis CLI
docker exec -it redis_local redis-cli

# Inside Redis CLI:
PING                    # Should return PONG
INFO stats              # View statistics
KEYS *                  # List all keys
exit                    # Exit
```

### Verify PgAdmin

1. Open browser: http://localhost:5050
2. Login with:
   - Email: `admin@local.com`
   - Password: `admin123`
3. Add servers:
   - **Main Database**:
     - Host: `postgres` (or `host.docker.internal` on Mac/Windows)
     - Port: `5432`
     - Database: `ai_admin`
     - Username: `admin`
     - Password: `admin123`
   - **Vector Database**:
     - Host: `postgres_vector` (or `host.docker.internal` on Mac/Windows)
     - Port: `5432` (internal port, not 5433)
     - Database: `ai_agent_vectors`
     - Username: `vector_admin`
     - Password: `vector123`

## Database Architecture

### Main Database (pg_local)
```
ai_admin
├── users                        # User accounts
├── password_reset_tokens        # Password reset functionality
└── [other application tables]   # Future application data
```

### Vector Database (pg_vector_local)
```
ai_agent_vectors
├── framework_documentation      # Framework docs with embeddings
│   ├── id (serial)
│   ├── content (text)
│   ├── embedding (vector(1536))
│   ├── metadata (jsonb)
│   ├── source (varchar)
│   ├── framework (varchar)
│   ├── section (varchar)
│   └── version (varchar)
└── [other vector tables]        # Future vector data
```

## Port Mapping

| Service | Internal Port | External Port | Purpose |
|---------|--------------|---------------|---------|
| PostgreSQL (Main) | 5432 | 5432 | Main database |
| PostgreSQL (Vector) | 5432 | 5433 | Vector database |
| Redis | 6379 | 6379 | Cache |
| PgAdmin | 80 | 5050 | Web UI |

## Data Persistence

All data is persisted in Docker volumes:

- `pgdata`: Main PostgreSQL data
- `pgvector_data`: Vector database data
- `redis_data`: Redis cache data (with AOF)
- `pgadmin_data`: PgAdmin configuration

### Backup Data

```bash
# Backup main database
docker exec pg_local pg_dump -U admin ai_admin > backup_main.sql

# Backup vector database
docker exec pg_vector_local pg_dump -U vector_admin ai_agent_vectors > backup_vector.sql

# Backup Redis
docker exec redis_local redis-cli SAVE
docker cp redis_local:/data/dump.rdb ./redis_backup.rdb
```

### Restore Data

```bash
# Restore main database
cat backup_main.sql | docker exec -i pg_local psql -U admin -d ai_admin

# Restore vector database
cat backup_vector.sql | docker exec -i pg_vector_local psql -U vector_admin -d ai_agent_vectors

# Restore Redis
docker cp ./redis_backup.rdb redis_local:/data/dump.rdb
docker-compose -f pg-docker.dockercompose.yml restart redis
```

## Troubleshooting

### Port Already in Use

If you get "port already in use" errors:

```bash
# Check what's using the port
lsof -i :5432
lsof -i :5433
lsof -i :6379

# Kill the process or change the port in docker-compose file
```

### Container Won't Start

```bash
# Check logs
docker-compose -f pg-docker.dockercompose.yml logs postgres_vector

# Remove and recreate
docker-compose -f pg-docker.dockercompose.yml down
docker-compose -f pg-docker.dockercompose.yml up -d
```

### pgvector Extension Not Found

```bash
# Connect to vector database
docker exec -it pg_vector_local psql -U vector_admin -d ai_agent_vectors

# Create extension manually
CREATE EXTENSION IF NOT EXISTS vector;

# Verify
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

### Redis Connection Issues

```bash
# Check if Redis is running
docker ps | grep redis_local

# Restart Redis
docker-compose -f pg-docker.dockercompose.yml restart redis

# Check Redis logs
docker logs redis_local
```

### Clear All Data (Fresh Start)

```bash
# WARNING: This deletes all data!
docker-compose -f pg-docker.dockercompose.yml down -v
docker-compose -f pg-docker.dockercompose.yml up -d
```

## Network Configuration

All services are connected via the `dev_network` bridge network, allowing them to communicate with each other using service names:

- From application: Use `localhost` with external ports
- Between containers: Use service names (`postgres`, `postgres_vector`, `redis`)

## Environment Variables

Update these in `backend/.env`:

```env
# Main database
DATABASE_URL=postgresql://admin:admin123@localhost:5432/ai_admin

# Vector database
VECTOR_DATABASE_URL=postgresql://vector_admin:vector123@localhost:5433/ai_agent_vectors

# Redis
REDIS_URL=redis://localhost:6379/0
```

## Production Considerations

For production deployment:

1. **Use managed services**:
   - AWS RDS for main PostgreSQL
   - AWS RDS with pgvector or Pinecone for vector database
   - AWS ElastiCache for Redis

2. **Update connection strings** in production environment variables

3. **Enable SSL/TLS** for all database connections

4. **Use strong passwords** and rotate regularly

5. **Enable backups** and point-in-time recovery

6. **Monitor resource usage** and scale as needed

## Resources

- **PostgreSQL**: https://www.postgresql.org/docs/
- **pgvector**: https://github.com/pgvector/pgvector
- **Redis**: https://redis.io/docs/
- **PgAdmin**: https://www.pgadmin.org/docs/

## Support

For issues with local development setup:
1. Check service logs: `docker-compose logs -f [service_name]`
2. Verify service health: `docker-compose ps`
3. Check port availability: `lsof -i :[port]`
4. Review this README for common solutions
