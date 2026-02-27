# DeveloperDoc.ai — Developer Documentation

> Complete reference for engineers working on the DeveloperDoc.ai codebase.

---

## Table of Contents

- [DeveloperDoc.ai — Developer Documentation](#developerdocai--developer-documentation)
  - [Table of Contents](#table-of-contents)
  - [1. Project Overview](#1-project-overview)
  - [2. High-Level Architecture](#2-high-level-architecture)
    - [Request Lifecycle](#request-lifecycle)
  - [3. Repository Structure](#3-repository-structure)
  - [4. Backend — Implementation Guide](#4-backend--implementation-guide)
    - [4.1 Technology Stack](#41-technology-stack)
    - [4.2 Directory Breakdown](#42-directory-breakdown)
    - [4.3 Core Application Bootstrap](#43-core-application-bootstrap)
    - [4.4 Configuration System](#44-configuration-system)
    - [4.5 Security \& JWT](#45-security--jwt)
    - [4.6 Database Layer](#46-database-layer)
      - [Main Database (PostgreSQL, port 5432)](#main-database-postgresql-port-5432)
      - [Vector Database (PostgreSQL + pgvector, port 5433)](#vector-database-postgresql--pgvector-port-5433)
    - [4.7 AI Agent System](#47-ai-agent-system)
      - [Supervisor Agent (`app/agents/supervisor_agent.py`)](#supervisor-agent-appagentssupervisor_agentpy)
      - [Documentation Search Agent (`app/agents/documentation_search_agent.py`)](#documentation-search-agent-appagentsdocumentation_search_agentpy)
      - [Code Generation Agent (`app/agents/code_gen_agent.py`)](#code-generation-agent-appagentscode_gen_agentpy)
      - [Syntax Validator (`app/agents/syntax_validator.py`)](#syntax-validator-appagentssyntax_validatorpy)
    - [4.8 LangGraph Workflow](#48-langgraph-workflow)
    - [4.9 Caching Layer](#49-caching-layer)
      - [Semantic Cache (`app/services/semantic_cache.py`)](#semantic-cache-appservicessemantic_cachepy)
      - [Tool Cache (`app/services/tool_cache.py`)](#tool-cache-appservicestool_cachepy)
    - [4.10 API Endpoints](#410-api-endpoints)
      - [Authentication (`/api/v1/auth/`)](#authentication-apiv1auth)
      - [Agent (`/api/v1/agent/`)](#agent-apiv1agent)
      - [Dashboard (`/api/v1/dashboard/`)](#dashboard-apiv1dashboard)
      - [MCP Tools (`/api/v1/mcp/`)](#mcp-tools-apiv1mcp)
      - [System Endpoints](#system-endpoints)
    - [4.11 Services](#411-services)
      - [`embedding_service.py`](#embedding_servicepy)
      - [`local_embedding_service.py`](#local_embedding_servicepy)
      - [`reranking_service.py`](#reranking_servicepy)
      - [`framework_detector.py`](#framework_detectorpy)
      - [`gemini_client.py`](#gemini_clientpy)
    - [4.12 Observability](#412-observability)
  - [5. Frontend — Implementation Guide](#5-frontend--implementation-guide)
    - [5.1 Technology Stack](#51-technology-stack)
    - [5.2 Directory Breakdown](#52-directory-breakdown)
    - [5.3 Routing \& Auth Guards](#53-routing--auth-guards)
    - [5.4 Services Layer](#54-services-layer)
      - [`authService.ts`](#authservicets)
      - [`agentService.ts`](#agentservicets)
    - [5.5 Components](#55-components)
      - [`ChatInterface.tsx`](#chatinterfacetsx)
      - [`LoginForm.tsx` / `RegisterForm.tsx`](#loginformtsx--registerformtsx)
      - [`MarkdownRenderer.tsx`](#markdownrenderertsx)
    - [5.6 State \& Notifications](#56-state--notifications)
  - [6. Infrastructure](#6-infrastructure)
    - [6.1 Docker Services](#61-docker-services)
    - [6.2 Database Schemas](#62-database-schemas)
      - [Main DB (PostgreSQL)](#main-db-postgresql)
      - [Vector DB (PostgreSQL + pgvector)](#vector-db-postgresql--pgvector)
    - [6.3 Migrations (Alembic)](#63-migrations-alembic)
  - [7. Local Development Setup](#7-local-development-setup)
    - [Prerequisites](#prerequisites)
    - [Step 1 — Clone \& configure](#step-1--clone--configure)
    - [Step 2 — Start infrastructure (Docker)](#step-2--start-infrastructure-docker)
    - [Step 3 — Backend setup](#step-3--backend-setup)
    - [Step 4 — Ingest documentation (first-time only)](#step-4--ingest-documentation-first-time-only)
    - [Step 5 — Frontend setup](#step-5--frontend-setup)
    - [Step 6 — Verify everything works](#step-6--verify-everything-works)
    - [One-Command Alternative](#one-command-alternative)
  - [8. Environment Variables Reference](#8-environment-variables-reference)
  - [9. Testing](#9-testing)
    - [9.1 Backend Tests](#91-backend-tests)
    - [9.2 Frontend Tests](#92-frontend-tests)
  - [10. API Reference](#10-api-reference)
    - [Base URL](#base-url)
    - [Authentication](#authentication)
    - [Auth Endpoints](#auth-endpoints)
    - [Agent Endpoint](#agent-endpoint)
    - [Response Formats](#response-formats)
  - [11. Known Issues \& Gotchas](#11-known-issues--gotchas)
    - [Backend](#backend)
    - [Frontend](#frontend)
    - [Infrastructure](#infrastructure)
  - [12. Development Workflow](#12-development-workflow)
    - [Adding a New API Endpoint](#adding-a-new-api-endpoint)
    - [Adding a New Framework](#adding-a-new-framework)
    - [Switching LLM Provider](#switching-llm-provider)
    - [Database Migrations](#database-migrations)
    - [Running the Full Test Suite](#running-the-full-test-suite)
    - [Checking System Health](#checking-system-health)
    - [Logs](#logs)

---

## 1. Project Overview

DeveloperDoc.ai is an AI-powered code generation system. Users submit natural-language prompts (e.g., "Create a NestJS controller for user authentication") and receive framework-compliant code backed by real documentation search.

**Core capabilities:**

| Capability | How |
|---|---|
| Framework-aware code generation | LLM + vector-searched framework docs as context |
| Multi-agent orchestration | Supervisor routes to Search / CodeGen / both |
| Semantic caching | Redis + pgvector deduplicate similar queries |
| 9 supported frameworks | NestJS, React, FastAPI, Django, Express, Vue, Angular, Spring Boot, .NET Core |
| Dual LLM support | OpenAI GPT-3.5 or Google Gemini (runtime switchable) |
| Observability | OpenTelemetry tracing + structlog JSON logging |

---

## 2. High-Level Architecture

```mermaid
graph TB
    %% ── Frontend ──────────────────────────────────────────────────────────
    subgraph Browser["Browser / Frontend"]
        FE["React 19 + Vite · localhost:5173\n─────────────────────────────\nAuth → Chat → Markdown rendering"]
    end

    %% ── Backend ───────────────────────────────────────────────────────────
    subgraph Backend["Backend API · FastAPI · localhost:8000"]

        subgraph Endpoints["Endpoints"]
            E1["Auth endpoints (JWT)"]
            E2["Agent query endpoint"]
            E3["Dashboard endpoints"]
            E4["MCP Tool endpoints"]
        end

        subgraph Cache["Semantic Cache"]
            SC["Redis exact-match\n+\npgvector similarity\n(threshold 0.95)"]
        end

        subgraph Workflow["LangGraph Workflow Engine"]
            SUP["Supervisor"]
            SA["Search Agent\n──────────────\npgvector + re-ranker"]
            CA["CodeGen Agent\n──────────────\nLLM + docs"]
        end

        Endpoints --> Cache
        Cache -->|cache miss| Workflow
        SUP --> SA
        SUP --> CA
    end

    %% ── Data Stores ───────────────────────────────────────────────────────
    PG1[("PostgreSQL · main\nlocalhost:5432\n──────────────\nUsers · Auth tokens")]
    PG2[("PostgreSQL + pgvector\nlocalhost:5433\n──────────────\nFramework docs\nEmbeddings\nSemantic cache table")]
    RD[("Redis\nlocalhost:6379\n──────────────\nExact-match cache\nTool result cache")]

    %% ── Edges ─────────────────────────────────────────────────────────────
    FE <-->|HTTP / REST| Endpoints

    Backend --> PG1
    Backend --> PG2
    Cache   --> RD
    SA      --> PG2

    %% ── Styles ────────────────────────────────────────────────────────────
    classDef frontend  fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a
    classDef endpoint  fill:#dcfce7,stroke:#22c55e,color:#14532d
    classDef cache     fill:#fef9c3,stroke:#eab308,color:#713f12
    classDef workflow  fill:#e0f2fe,stroke:#0284c7,color:#0c4a6e
    classDef postgres  fill:#f3e8ff,stroke:#a855f7,color:#581c87
    classDef redis     fill:#fee2e2,stroke:#ef4444,color:#7f1d1d

    class FE frontend
    class E1,E2,E3,E4 endpoint
    class SC,Cache cache
    class SUP,SA,CA workflow
    class PG1,PG2 postgres
    class RD redis
```

### Request Lifecycle

```mermaid
flowchart TD
    A([User Query]) --> B["POST /api/v1/agent/query"]
    B --> C["Auto-detect framework\nfrom prompt"]
    C --> D{"Check\nSemantic Cache"}

    D -->|Cache HIT ~50 ms| Z([Return response to frontend])
    D -->|Cache MISS| E["LangGraph Workflow"]

    E --> F["Supervisor\ndecides route"]

    F -->|SEARCH_ONLY|        G["Documentation Search"]
    F -->|CODE_ONLY|          H["Code Generation"]
    F -->|SEARCH_THEN_CODE|   G

    G --> G1["Embed query\n→ pgvector similarity search"]
    G1 --> G2["Cross-encoder re-rank\n→ top K docs"]
    G2 -->|SEARCH_THEN_CODE| H

    H --> H1["LLM + doc context\n→ generate code"]
    H1 --> H2{"Syntax\nvalid?"}
    H2 -->|No — retry max 2x| H1
    H2 -->|Yes| I["Store in\nsemantic cache"]

    G2 -->|SEARCH_ONLY| I
    I --> Z

    %% ── Styles ────────────────────────────────────────────────────────────
    classDef io        fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a
    classDef process   fill:#dcfce7,stroke:#22c55e,color:#14532d
    classDef decision  fill:#fef9c3,stroke:#eab308,color:#713f12
    classDef search    fill:#f3e8ff,stroke:#a855f7,color:#581c87
    classDef codegen   fill:#e0f2fe,stroke:#0284c7,color:#0c4a6e
    classDef cache     fill:#fee2e2,stroke:#ef4444,color:#7f1d1d

    class A,Z io
    class B,C,E,F process
    class D,H2 decision
    class G,G1,G2 search
    class H,H1 codegen
    class I cache
```

---

## 3. Repository Structure

```
DeveloperDoc.ai/
├── backend/                    # FastAPI Python backend
│   ├── app/                    # Application source
│   ├── alembic/                # Database migrations
│   ├── tests/                  # pytest test suite (25+ files)
│   ├── scripts/                # Scraping & ingestion scripts
│   ├── requirements.txt
│   ├── alembic.ini
│   └── .env / .env.local       # Environment (gitignored)
├── frontend/                   # React TypeScript frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── utils/
│   │   └── test/               # Vitest test suite
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml          # Production-like compose (all services)
├── docker-compose.dev.yml      # Dev compose (infra only)
├── start_all.sh                # One-command startup script
├── stop_all.sh                 # Shutdown script
└── scripts/                    # Setup helper scripts
```

---

## 4. Backend — Implementation Guide

### 4.1 Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Web framework | FastAPI | latest |
| ASGI server | Uvicorn | latest |
| ORM | SQLAlchemy (async) | latest |
| Migrations | Alembic | latest |
| Main DB | PostgreSQL | 15 |
| Vector DB | PostgreSQL + pgvector | ankane/pgvector |
| Cache | Redis | 7 |
| AI orchestration | LangGraph + LangChain | latest |
| LLM (default) | OpenAI gpt-3.5-turbo | — |
| LLM (alternative) | Google Gemini 1.5 Flash | — |
| Embeddings | text-embedding-3-small (1536-dim) | OpenAI |
| Re-ranking | cross-encoder/ms-marco-MiniLM-L-6-v2 | sentence-transformers |
| Auth | JWT (HS256) + bcrypt | python-jose, passlib |
| Observability | OpenTelemetry + structlog | latest |
| Testing | pytest + pytest-asyncio + httpx | latest |

### 4.2 Directory Breakdown

```
backend/app/
├── main.py                         # App factory, lifespan, routers, exception handlers
├── agents/
│   ├── supervisor_agent.py         # LLM-based prompt router
│   ├── documentation_search_agent.py  # Vector search + re-ranking
│   ├── code_gen_agent.py           # LLM code generation + validation
│   └── syntax_validator.py         # Per-language syntax validation
├── api/v1/endpoints/
│   ├── auth.py                     # Register, login, refresh, password reset
│   ├── agent.py                    # POST /query, GET /health
│   ├── dashboard.py                # User dashboard metrics
│   └── mcp_tools.py                # MCP protocol tool endpoints
├── core/
│   ├── config.py                   # Pydantic BaseSettings
│   ├── security.py                 # Password hashing, JWT encode/decode
│   ├── database.py                 # SQLAlchemy async engine + session
│   ├── vector_database.py          # AsyncPG pool for pgvector DB
│   ├── dependencies.py             # FastAPI DI: get_db, get_current_user
│   ├── exceptions.py               # Custom exception classes
│   ├── telemetry.py                # OpenTelemetry setup
│   └── logging_config.py           # structlog JSON formatter
├── models/
│   ├── user.py                     # User + PasswordResetToken ORM models
│   └── framework_documentation.py  # FrameworkDocumentation ORM model
├── schemas/
│   ├── auth.py                     # Pydantic request/response for auth
│   ├── agent.py                    # QueryRequest, AgentResponse, etc.
│   ├── dashboard.py                # Dashboard response shapes
│   └── mcp.py                      # MCP protocol schemas
├── repositories/
│   ├── user_repository.py          # DB queries for users
│   └── password_reset_repository.py
├── services/
│   ├── auth_service.py             # Registration, login, token refresh
│   ├── embedding_service.py        # OpenAI text-embedding calls
│   ├── local_embedding_service.py  # sentence-transformers fallback
│   ├── semantic_cache.py           # Redis + pgvector cache
│   ├── tool_cache.py               # Short-lived search result cache
│   ├── vector_search_service.py    # pgvector similarity queries
│   ├── reranking_service.py        # Cross-encoder re-ranking
│   ├── framework_detector.py       # Detect framework from prompt text
│   ├── gemini_client.py            # Google Gemini API wrapper
│   ├── mcp_client.py               # MCP service HTTP client
│   ├── documentation_ingestion_service.py  # Load scraped docs → vector DB
│   └── dashboard_service.py        # Usage statistics queries
├── workflows/
│   └── agent_workflow.py           # LangGraph graph definition & runner
└── utils/
    ├── retry.py                    # Tenacity retry decorators
    └── circuit_breaker.py          # Circuit breaker pattern
```

### 4.3 Core Application Bootstrap

**`app/main.py`** is the entry point. Key responsibilities:

```python
# Lifespan context manager — runs on startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Verify main DB connection
    # 2. Verify vector DB connection (asyncpg pool)
    # 3. Initialize semantic cache (create pool)
    # 4. Setup OpenTelemetry
    yield
    # 5. Close pools and cleanup
```

**CORS** is configured to allow all origins in development. For production, restrict `allow_origins`.

**Global exception handlers** map custom exceptions to HTTP status codes:

| Exception | HTTP Status | When |
|---|---|---|
| `AuthenticationError` | 401 | Bad credentials, expired token |
| `WeakPasswordError` | 422 | Password fails strength check |
| `EmailAlreadyExistsError` | 409 | Duplicate registration |
| `AgentWorkflowError` | 500 | Unhandled agent failure |
| `AgentUnavailableError` | 503 | LLM API down |
| `AgentTimeoutError` | 504 | Workflow exceeded time limit |
| `InvalidPromptError` | 400 | Empty or malformed prompt |

### 4.4 Configuration System

**`app/core/config.py`** uses Pydantic `BaseSettings`. Values are loaded from `.env.local` (preferred) or `.env`.

Critical settings and their defaults:

```python
class Settings(BaseSettings):
    # Application
    app_env: str = "development"
    app_name: str = "DeveloperDocAI"

    # Main database (PostgreSQL)
    database_url: str  # required

    # Vector database (PostgreSQL + pgvector)
    vector_database_url: str  # required

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str  # required — generate with: openssl rand -hex 32
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_reset_token_expire_hours: int = 1

    # LLM
    llm_provider: str = "openai"        # "openai" or "gemini"
    openai_api_key: Optional[str]
    gemini_api_key: Optional[str]

    # Embeddings
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # Semantic Cache
    semantic_cache_threshold: float = 0.95
    semantic_cache_ttl: int = 3600      # seconds

    # Tool Cache
    tool_cache_ttl: int = 300           # 5 minutes

    # Vector Search
    vector_search_top_k: int = 10
    vector_search_min_score: float = 0.7

    # Re-ranking
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Workflow
    max_workflow_iterations: int = 3

    # Password
    bcrypt_rounds: int = 12

    # Observability
    otel_enabled: bool = True
    log_level: str = "INFO"
    log_format: str = "json"
```

### 4.5 Security & JWT

**`app/core/security.py`** implements:

**Password hashing:**
- bcrypt with configurable rounds (default 12)
- `hash_password(plain: str) → str`
- `verify_password(plain: str, hashed: str) → bool` — constant-time comparison

**Password strength validation:**
- Minimum 8 characters
- Must contain at least one letter and one number
- Raises `WeakPasswordError` on failure

**JWT tokens:**
- `create_access_token(data: dict, expires_delta) → str` — short-lived (30 min)
- `create_refresh_token(data: dict) → str` — long-lived (7 days)
- `decode_token(token: str) → dict` — validates signature + expiration
- Algorithm: HS256 (symmetric), configurable to RS256

**Token storage in frontend:** stored in HTTP-only cookies via `cookieUtils.ts`.

### 4.6 Database Layer

#### Main Database (PostgreSQL, port 5432)

Used for: users, password reset tokens, auth state.

- **ORM**: SQLAlchemy async engine with `AsyncSession`
- **Connection**: `app/core/database.py` — `async_sessionmaker` factory
- **DI**: `get_db()` dependency injects session per request

Tables:
- `users` — id, email (unique), password_hash, is_active, created_at, updated_at
- `password_reset_tokens` — id, user_id (FK), token (unique), expires_at, used

#### Vector Database (PostgreSQL + pgvector, port 5433)

Used for: framework documentation embeddings, semantic cache.

- **Driver**: `asyncpg` (direct, not SQLAlchemy) for performance
- **Connection**: `app/core/vector_database.py` — `asyncpg.create_pool(min=2, max=10)`
- **Extension**: `pgvector` must be installed (handled by `ankane/pgvector` Docker image)

Tables:
- `framework_documentation` — content, embedding (vector 1536), metadata (JSONB), source, framework, section, version + HNSW index
- `semantic_cache` — prompt (unique), response, embedding (vector 384), cached_at, ttl + HNSW index

**HNSW index parameters** (migration `bae3a0c66742`):
```sql
CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```
This gives O(log N) approximate nearest-neighbor search.

### 4.7 AI Agent System

The system has three specialized agents orchestrated by LangGraph.

#### Supervisor Agent (`app/agents/supervisor_agent.py`)

Analyzes the user's prompt and decides the routing strategy.

**Routing strategies:**
| Strategy | When Used | Example Prompt |
|---|---|---|
| `SEARCH_ONLY` | Pure documentation lookup | "What is dependency injection in NestJS?" |
| `CODE_ONLY` | Simple code tasks without framework specifics | "Write a Python fibonacci function" |
| `SEARCH_THEN_CODE` | Framework-specific code generation | "Create a NestJS REST controller" |

**Implementation:**
- Sends prompt to LLM (GPT-3.5 or Gemini) with a classification system prompt
- Returns `RoutingStrategy` enum
- Includes tenacity retry with exponential backoff (3 attempts)
- Logs routing decision with trace ID

#### Documentation Search Agent (`app/agents/documentation_search_agent.py`)

Retrieves relevant framework documentation using semantic search.

**Pipeline:**
1. Check tool cache (Redis, 5 min TTL) — skip vector search if cached
2. Generate query embedding (OpenAI `text-embedding-3-small`)
3. pgvector cosine similarity search (top_k = 10)
4. Cross-encoder re-ranking (`ms-marco-MiniLM-L-6-v2`) — reorders results by relevance
5. **Self-correction**: if max score < 0.7, rephrase query and retry once
6. Return `DocumentationResult[]` with content, score, source metadata

**Self-correction** is a key reliability feature. It reformulates the query if results are low-confidence, giving a second chance at finding relevant docs.

#### Code Generation Agent (`app/agents/code_gen_agent.py`)

Generates framework-compliant code using the LLM.

**Framework-specific prompting:** The agent maintains custom system prompts for each framework:
- **NestJS**: Focus on decorators (`@Controller`, `@Injectable`), TypeScript, DI patterns
- **React**: Hooks, functional components, JSX, state management
- **FastAPI**: Pydantic models, async route handlers, dependency injection
- **Spring Boot**: Annotations, REST controllers, JPA repositories
- **.NET Core**: Controllers, dependency injection, Entity Framework
- ... and 4 more frameworks

**Generation pipeline:**
1. Build prompt: framework guide + documentation context + user query
2. Call LLM → extract code from markdown code blocks
3. Validate syntax (language-specific)
4. If invalid: retry with error feedback (max 2 retries)
5. Return `CodeGenerationResult` with `syntax_valid` flag

#### Syntax Validator (`app/agents/syntax_validator.py`)

Validates generated code before returning to the user.

| Language | Validation Method |
|---|---|
| Python | `py_compile` + AST parse |
| JavaScript / TypeScript | Regex heuristics (balanced braces, brackets) |
| Java | Regex heuristics (class/method structure) |
| C# | Regex heuristics |

### 4.8 LangGraph Workflow

**`app/workflows/agent_workflow.py`** defines the multi-agent graph.

**Graph structure:**
```
START → supervisor → (conditional) → search → codegen → validate → END
                   ↘               ↗
                    → codegen ─────
```

**State object (`WorkflowState`):**
```python
{
  "prompt": str,
  "routing_strategy": RoutingStrategy,
  "search_results": List[DocumentationResult],
  "generated_code": str,
  "syntax_valid": bool,
  "iteration_count": int,      # prevents infinite cycles
  "agents_invoked": List[str], # for response metadata
  "processing_time_ms": float,
  "token_usage": dict
}
```

**Cycle protection:** `max_workflow_iterations = 3` (configurable). If the code fails validation twice, the workflow returns the best available result.

**Execution:**
```python
result = await workflow.ainvoke({"prompt": user_query})
```

Returns `AgentResponse` Pydantic model with `answer`, `cache_hit`, `metadata`.

### 4.9 Caching Layer

Two-tier caching prevents redundant LLM API calls.

#### Semantic Cache (`app/services/semantic_cache.py`)

Stores full agent responses keyed by prompt similarity.

**Lookup flow:**
1. SHA256 hash of prompt → check Redis exact-match (sub-millisecond)
2. If miss: embed prompt → pgvector cosine similarity search in `semantic_cache` table
3. If similarity ≥ 0.95: cache hit, return stored response
4. If miss: execute workflow, store result with embedding

**Why two layers?** Redis handles exact repeats instantly. pgvector handles semantically similar queries ("Create NestJS controller" ≈ "Write a NestJS controller").

**Cache operations:**
```python
await cache.get(prompt)                   # check cache
await cache.get_with_embedding(prompt, embedding)  # similarity search
await cache.set(prompt, response, embedding)       # store result
await cache.clear()                       # flush all
```

**Connection pool:** asyncpg pool (min=2, max=10) to the vector DB.

#### Tool Cache (`app/services/tool_cache.py`)

Short-lived cache (5 min) for documentation search results. Keyed by the search query string. Stored in Redis DB 0 (separate from semantic cache). Prevents re-running expensive vector searches for the same query within a session.

### 4.10 API Endpoints

#### Authentication (`/api/v1/auth/`)

| Method | Path | Description | Auth Required |
|---|---|---|---|
| POST | `/register` | Create new user | No |
| POST | `/login` | Authenticate, get tokens | No |
| POST | `/refresh` | Get new access token | Refresh token in body |
| POST | `/change-password` | Change password | Yes |
| POST | `/reset-password/request` | Send reset email | No |
| POST | `/reset-password/confirm` | Reset with token | No |

**Register request:**
```json
{ "email": "user@example.com", "password": "Secure123" }
```

**Login response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

#### Agent (`/api/v1/agent/`)

| Method | Path | Description | Auth Required |
|---|---|---|---|
| POST | `/query` | Submit AI query | Yes |
| GET | `/health` | Agent system health | No |

**Query request:**
```json
{ "prompt": "Create a NestJS authentication module with JWT" }
```

**Query response:**
```json
{
  "answer": "## NestJS Authentication Module\n\n```typescript\n...",
  "cache_hit": false,
  "metadata": {
    "routing_strategy": "SEARCH_THEN_CODE",
    "agents_invoked": ["supervisor", "search", "codegen"],
    "processing_time_ms": 4823,
    "frameworks_detected": ["nestjs"],
    "token_usage": { "prompt_tokens": 1200, "completion_tokens": 800 }
  }
}
```

#### Dashboard (`/api/v1/dashboard/`)

Returns usage statistics for the authenticated user.

#### MCP Tools (`/api/v1/mcp/`)

Model Context Protocol tool endpoints for external integrations.

#### System Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Basic health check |
| GET | `/health/vector-db` | Vector DB connectivity |
| GET | `/docs` | Swagger UI (auto-generated) |
| GET | `/redoc` | ReDoc API documentation |

### 4.11 Services

#### `embedding_service.py`

Wraps OpenAI's `text-embedding-3-small` (1536 dims).

```python
embedding = await service.embed_text("NestJS controller")
embeddings = await service.embed_batch(["text1", "text2"])
```

Includes tenacity retry (3 attempts, exponential backoff) for rate limits.

#### `local_embedding_service.py`

Fallback using sentence-transformers (no API key needed, runs locally). Used when OpenAI API is unavailable or for cost reduction. Produces 384-dimensional embeddings (smaller than OpenAI's 1536).

**Important:** The semantic_cache table uses `vector(384)` as of the migration `change_embedding_dimension_to_384.py`, which matches local embeddings.

#### `reranking_service.py`

Uses `cross-encoder/ms-marco-MiniLM-L-6-v2` to re-score (document, query) pairs. Takes top_k vector results and returns them sorted by cross-encoder relevance score. Runs locally (no API call needed).

#### `framework_detector.py`

Inspects the prompt text for framework keywords to set context before the workflow runs. Used to pre-filter documentation search and to select the correct code generation prompt template.

#### `gemini_client.py`

Google Gemini API wrapper. Mirrors the OpenAI client interface so agents can call either provider transparently. Switch via `LLM_PROVIDER=gemini` in `.env`.

### 4.12 Observability

**OpenTelemetry** traces each request end-to-end:
- Span per workflow node (supervisor, search, codegen)
- Span per LLM API call
- Span per cache operation

**structlog** provides structured JSON logs:
```json
{ "level": "info", "event": "cache_hit", "trace_id": "abc123", "similarity": 0.97 }
```

**Health endpoints** for external monitoring:
- `GET /health` → `{ "status": "healthy", "database": "connected" }`
- `GET /health/vector-db` → `{ "status": "healthy", "pool_size": 5 }`

---

## 5. Frontend — Implementation Guide

### 5.1 Technology Stack

| Technology | Version | Purpose |
|---|---|---|
| React | 19.2.0 | UI framework |
| TypeScript | (components) | Type safety |
| Vite | 7.2.4 | Build tool, dev server |
| Tailwind CSS | 4.1.18 | Styling |
| React Router DOM | 7.13.0 | Client-side routing |
| React Hook Form | 7.71.1 | Form management + validation |
| React Hot Toast | 2.6.0 | Toast notifications |
| Vitest | 4.0.18 | Test runner |
| Testing Library | latest | Component testing |
| MSW | 2.x | API mocking in tests |

**Note:** The codebase mixes `.jsx` (App, main) with `.tsx` (everything else). This is intentional — do not convert App.jsx to TypeScript unless the whole migration is planned.

### 5.2 Directory Breakdown

```
frontend/src/
├── App.jsx                  # Root component — mounts AppRouter + Toaster
├── main.jsx                 # ReactDOM.createRoot entry point
├── components/
│   ├── ChatInterface.tsx    # Query input + response display
│   ├── LoginForm.tsx        # Email/password login form
│   ├── RegisterForm.tsx     # Registration form with validation
│   └── MarkdownRenderer.tsx # Renders AI markdown responses
├── pages/
│   ├── ChatPage.tsx         # Main chat page (header + ChatInterface)
│   ├── LoginPage.tsx        # Login page wrapper
│   └── RegisterPage.tsx     # Register page wrapper
├── routes/
│   ├── AppRouter.tsx        # All route definitions
│   └── ProtectedRoute.tsx   # Auth guard wrapper
├── services/
│   ├── authService.ts       # Login, register, token management
│   ├── agentService.ts      # Submit query to backend
│   └── __mocks__/           # Vitest module mocks
│       ├── authService.ts
│       └── agentService.ts
└── utils/
    ├── cookieUtils.ts       # setCookie, getCookie, deleteCookie
    ├── toast.ts             # Typed toast helper wrappers
    └── __mocks__/
        ├── cookieUtils.ts
        └── toast.ts
```

### 5.3 Routing & Auth Guards

**`AppRouter.tsx`** defines all routes:

```
/           → redirect to /login
/login      → LoginPage (public)
/register   → RegisterPage (public)
/chat       → ChatPage (protected)
```

**`ProtectedRoute.tsx`** checks for a valid access token cookie. If none is found, it redirects to `/login` using React Router's `<Navigate>`.

```tsx
// ProtectedRoute logic
const token = getCookie('access_token')
if (!token) return <Navigate to="/login" replace />
return <Outlet />
```

### 5.4 Services Layer

#### `authService.ts`

Handles all authentication API calls against `http://localhost:8000/api`.

```typescript
// Login — returns { access_token, refresh_token } or throws
login(email: string, password: string): Promise<TokenResponse>

// Register — creates user
register(email: string, password: string): Promise<void>

// Token management (uses cookieUtils internally)
storeTokens(accessToken: string, refreshToken: string): void
getAccessToken(): string | null
clearTokens(): void
```

Tokens are stored in cookies with 30-minute expiry for access token, 7-day for refresh.

#### `agentService.ts`

Submits queries to the agent endpoint.

```typescript
submitQuery(prompt: string): Promise<AgentResponse>
```

Automatically reads the access token from cookies and includes it in the `Authorization: Bearer <token>` header. Returns the full `AgentResponse` object from the backend.

**Session expiry handling:** If the backend returns 401, `agentService` dispatches a `SESSION_EXPIRED` event. `ChatInterface.tsx` listens for this event, clears tokens, and redirects to `/login`.

### 5.5 Components

#### `ChatInterface.tsx`

Main interaction UI. Responsibilities:
- Text area for prompt input
- Submit button with loading state
- Displays AI response using `MarkdownRenderer`
- Handles `SESSION_EXPIRED` custom event → auto-logout
- Shows error messages from failed queries

State managed locally with `useState` (no global state library needed for this scope).

#### `LoginForm.tsx` / `RegisterForm.tsx`

Built with **React Hook Form**. Validation rules:
- Email: required, valid format
- Password: required, min 8 characters (RegisterForm enforces this client-side; backend also validates)

On success, calls `onSuccess` prop callback (page navigates to `/chat`).
On failure, displays error toast via `toast.error()`.

#### `MarkdownRenderer.tsx`

Renders the AI's markdown response. Handles:
- Headings (h1–h4)
- Code blocks with language labels
- Inline code
- Ordered and unordered lists
- Paragraphs

**Important:** Code blocks use `<pre><code>` with CSS formatting. There is currently no syntax highlighting library — adding one (e.g., `highlight.js` or `prism`) would improve readability.

### 5.6 State & Notifications

**No global state manager** (no Redux, Zustand, etc.) is used. The app is simple enough that local component state + prop drilling is sufficient.

**Toast notifications** (`react-hot-toast`) are configured in `App.jsx`:
```jsx
<Toaster position="top-right" toastOptions={{ duration: 4000 }} />
```

Toast helpers in `utils/toast.ts`:
```typescript
showSuccess(message: string): void   // green
showError(message: string): void     // red
showLoading(message: string): string // blue, returns ID for dismissal
dismissToast(id: string): void
```

---

## 6. Infrastructure

### 6.1 Docker Services

**`docker-compose.yml`** defines the full stack for production-like environments:

| Service | Container | Image | Port | Purpose |
|---|---|---|---|---|
| postgres | ai-agent-postgres | postgres:15-alpine | 5432 | Main DB |
| postgres-vector | ai-agent-postgres-vector | ankane/pgvector | 5433 | Vector DB |
| redis | ai-agent-redis | redis:7-alpine | 6379 | Cache |
| fastapi-app | ai-agent-fastapi | custom build | 8000 | Backend API |
| mcp-tool | ai-agent-mcp-tool | custom build | 8001 | MCP Tool Service |

**`docker-compose.dev.yml`** runs only infrastructure (postgres, postgres-vector, redis) so the backend and frontend can be run locally for hot-reload development.

All services are on the `ai-agent-network` bridge network. The FastAPI container waits for `postgres`, `postgres-vector`, and `redis` to be healthy before starting.

### 6.2 Database Schemas

#### Main DB (PostgreSQL)

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Password reset tokens
CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    used BOOLEAN DEFAULT FALSE
);
```

#### Vector DB (PostgreSQL + pgvector)

```sql
-- Framework documentation with embeddings
CREATE TABLE framework_documentation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(1536),             -- OpenAI text-embedding-3-small
    metadata JSONB,                      -- source, tags, etc.
    source VARCHAR,                      -- URL of original doc
    framework VARCHAR,                   -- nestjs, react, fastapi, etc.
    section VARCHAR,                     -- doc section title
    version VARCHAR,                     -- framework version
    created_at TIMESTAMP DEFAULT now()
);

-- HNSW index for fast similarity search
CREATE INDEX ON framework_documentation
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- GIN index on metadata for JSONB queries
CREATE INDEX ON framework_documentation USING gin(metadata);

-- Semantic cache
CREATE TABLE semantic_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt TEXT UNIQUE NOT NULL,
    response TEXT NOT NULL,
    embedding vector(384),              -- local embedding (384-dim)
    cached_at TIMESTAMP DEFAULT now(),
    ttl INTEGER DEFAULT 3600
);

CREATE INDEX ON semantic_cache
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

### 6.3 Migrations (Alembic)

Migrations are in `backend/alembic/versions/`. Run order:

| Migration | File | Creates |
|---|---|---|
| 1 | `afcd0aaaf25d_create_users_and_password_reset_tokens_` | users, password_reset_tokens |
| 2 | `bae3a0c66742_create_framework_documentation_table` | framework_documentation with HNSW |
| 3 | `7048d18b575d_create_semantic_cache_table` | semantic_cache |
| 4 | `change_embedding_dimension_to_384` | Alters embedding dim on semantic_cache to 384 |

**Important:** Migration 4 changes the semantic_cache embedding dimension from 1536 to 384 to match local embeddings. If you switch embedding providers, run a data migration or clear the cache.

**Common migration commands:**
```bash
# Apply all migrations
alembic upgrade head

# Check current migration
alembic current

# Rollback one step
alembic downgrade -1

# Generate new migration from model changes
alembic revision --autogenerate -m "description"
```

**The alembic.ini** points to the main database (`DATABASE_URL`). Vector DB schema changes must be applied manually or via a separate alembic config pointing to `VECTOR_DATABASE_URL`.

---

## 7. Local Development Setup

### Prerequisites

| Tool | Minimum Version | Check |
|---|---|---|
| Docker Desktop | Any recent | `docker --version` |
| Python | 3.10+ | `python3 --version` |
| pip | latest | `pip --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |

### Step 1 — Clone & configure

```bash
git clone <repo-url>
cd DeveloperDoc.ai
```

Create the backend environment file:
```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` with your values (see [Environment Variables](#8-environment-variables-reference)).

### Step 2 — Start infrastructure (Docker)

```bash
# Infra only (recommended for dev)
docker-compose -f docker-compose.dev.yml up -d

# Verify all services are healthy
docker-compose ps
```

Expected output — all three services `healthy`:
```
NAME                    STATUS
ai-agent-postgres       Up (healthy)
ai-agent-postgres-vector  Up (healthy)
ai-agent-redis          Up (healthy)
```

### Step 3 — Backend setup

```bash
cd backend
pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Start the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend available at `http://localhost:8000`.
Swagger UI at `http://localhost:8000/docs`.

### Step 4 — Ingest documentation (first-time only)

This populates the vector database with framework documentation.

```bash
cd backend

# Scrape docs (quick: NestJS, React, FastAPI only — ~5 min)
python scripts/scrape_documentation.py --quick

# Full scrape (all 9 frameworks — ~15 min)
python scripts/scrape_documentation.py

# Generate embeddings and store in vector DB
python scripts/ingest_documentation.py

# Verify ingestion
python scripts/verify_setup.py
```

### Step 5 — Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend available at `http://localhost:5173`.

### Step 6 — Verify everything works

```bash
# Backend health
curl http://localhost:8000/health

# Expected:
{ "status": "healthy", "database": "connected" }
```

Open `http://localhost:5173` → register → submit a query.

### One-Command Alternative

The `start_all.sh` script automates steps 2–5:

```bash
./start_all.sh --quick          # infra + backend + frontend (quick doc mode)
./start_all.sh                  # full mode (all 9 frameworks)
./start_all.sh --skip-docs      # skip documentation ingestion
./start_all.sh --backend-only   # no frontend
./stop_all.sh                   # stop all processes
./stop_all.sh --docker          # stop processes + Docker services
```

---

## 8. Environment Variables Reference

Create `backend/.env` (or `backend/.env.local` for local overrides):

```env
# ── Application ──────────────────────────────────
APP_ENV=development
APP_NAME=DeveloperDocAI
APP_HOST=0.0.0.0
APP_PORT=8000

# ── Databases ────────────────────────────────────
DATABASE_URL=postgresql://admin:admin123@localhost:5432/ai_admin
VECTOR_DATABASE_URL=postgresql://vector_admin:vector123@localhost:5433/ai_agent_vectors

# ── Redis ────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# ── LLM Provider (choose one) ────────────────────
LLM_PROVIDER=openai                          # "openai" or "gemini"
OPENAI_API_KEY=sk-...                        # required if LLM_PROVIDER=openai
GEMINI_API_KEY=...                           # required if LLM_PROVIDER=gemini

# ── JWT ──────────────────────────────────────────
# Generate: openssl rand -hex 32
JWT_SECRET_KEY=your-256-bit-secret-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
PASSWORD_RESET_TOKEN_EXPIRE_HOURS=1

# ── Password Security ────────────────────────────
BCRYPT_ROUNDS=12

# ── Embeddings ───────────────────────────────────
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# ── Re-ranking ───────────────────────────────────
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# ── Semantic Cache ───────────────────────────────
SEMANTIC_CACHE_THRESHOLD=0.95
SEMANTIC_CACHE_TTL=3600                      # seconds (1 hour)

# ── Tool Cache ───────────────────────────────────
TOOL_CACHE_TTL=300                           # seconds (5 minutes)

# ── Vector Search ────────────────────────────────
VECTOR_SEARCH_TOP_K=10
VECTOR_SEARCH_MIN_SCORE=0.7

# ── Workflow ─────────────────────────────────────
MAX_WORKFLOW_ITERATIONS=3

# ── MCP Service ──────────────────────────────────
MCP_SERVICE_URL=http://localhost:8001
MCP_TOOL_RETRY_ATTEMPTS=3
MCP_TOOL_RETRY_BACKOFF_MULTIPLIER=1
MCP_TOOL_RETRY_MIN_WAIT=1
MCP_TOOL_RETRY_MAX_WAIT=10

# ── Observability ────────────────────────────────
OTEL_ENABLED=true
OTEL_SERVICE_NAME=ai-agent-system
OTEL_EXPORTER_TYPE=console                   # "console" or "jaeger" or "otlp"
LOG_LEVEL=INFO                               # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json                              # "json" or "text"
```

**Frontend:** No `.env` needed for local dev. The API base URL is hardcoded in services:
- `frontend/src/services/authService.ts` — `http://localhost:8000/api`
- `frontend/src/services/agentService.ts` — `http://localhost:8000/api`

For production, extract these to `VITE_API_BASE_URL` environment variables.

---

## 9. Testing

### 9.1 Backend Tests

Test suite location: `backend/tests/`
Runner: `pytest` with `pytest-asyncio`

**Run tests:**
```bash
cd backend

# All tests
pytest -v

# Specific file
pytest tests/test_agent_endpoint.py -v

# With coverage
pytest --cov=app --cov-report=html

# Specific marker
pytest -m "unit" -v
pytest -m "integration" -v
```

**Test files overview:**

| File | Tests |
|---|---|
| `test_agent_endpoint.py` | Agent query validation, cache hits/misses |
| `test_agent_workflow.py` | Workflow routing, node execution, cycles |
| `test_supervisor_agent.py` | Routing strategy decisions |
| `test_code_gen_agent.py` | Code generation with framework context |
| `test_code_gen_integration.py` | Full code gen pipeline |
| `test_caching_layer.py` | Semantic cache get/set/similarity |
| `test_semantic_cache.py` | Cache TTL, threshold behavior |
| `test_auth_service_integration.py` | Register, login, token refresh |
| `test_jwt_properties.py` | JWT expiration, claims |
| `test_vector_database.py` | asyncpg pool connectivity |
| `test_embedding_service.py` | OpenAI embedding calls (mocked) |
| `test_reranking_service.py` | Cross-encoder ranking |
| `test_exception_handlers.py` | HTTP status code mapping |
| `test_health_check.py` | `/health` endpoint |
| `test_observability.py` | OpenTelemetry span creation |
| `test_e2e_agent_workflows.py` | End-to-end workflow (mocked LLM) |
| `test_e2e_flows.py` | Full registration → query flows |
| `test_performance.py` | Response time benchmarks |
| `test_api_endpoints.py` | Auth API contract tests |
| `test_dashboard_api.py` | Dashboard endpoint |
| `test_mcp_client.py` | MCP HTTP client |
| `test_syntax_validator.py` | Per-language validation |
| `test_retry_utils.py` | Tenacity retry decorator |
| `test_vector_search_service.py` | pgvector similarity queries |
| `test_workflow_integration.py` | LangGraph graph integration |

**`conftest.py`** provides:
- In-memory SQLite database (isolated per test)
- Environment variable injection (no real API keys needed)
- Async event loop configuration

### 9.2 Frontend Tests

Test suite location: `frontend/src/test/`
Runner: Vitest v4.0.18

**Run tests:**
```bash
cd frontend

npm test              # watch mode
npm run test:run      # CI (single run)
npm run test:coverage # with coverage
```

**Test configuration** in `vite.config.js`:
```js
test: {
  environment: 'jsdom',
  setupFiles: ['./src/test/setup.ts'],
  globals: true
}
```

**`src/test/setup.ts`** initializes:
- `@testing-library/jest-dom` matchers
- MSW server (for integration tests)

**Test structure:**
```
src/test/
├── setup.ts
├── utils/
│   ├── cookieUtils.test.ts       # setCookie, getCookie, deleteCookie
│   └── toast.test.ts             # all toast helpers
├── services/
│   ├── authService.test.ts       # login, register, token ops (mocked fetch)
│   └── agentService.test.ts      # submitQuery (mocked fetch + authService)
├── components/
│   ├── LoginForm.test.tsx         # validation, success, failure
│   ├── RegisterForm.test.tsx      # validation, success, failure
│   ├── MarkdownRenderer.test.tsx  # markdown rendering
│   └── ChatInterface.test.tsx     # submit, response, SESSION_EXPIRED
├── pages/
│   ├── LoginPage.test.tsx         # structure, /register link, navigate
│   ├── RegisterPage.test.tsx      # structure, /login link, navigate
│   └── ChatPage.test.tsx          # logo, logout, clearTokens + navigate
└── integration/
    ├── mocks/
    │   ├── handlers.ts            # MSW request handlers
    │   └── server.ts              # MSW node server
    ├── auth.integration.test.tsx  # full login/register flows
    ├── routing.integration.test.tsx  # ProtectedRoute behavior
    └── chat.integration.test.tsx  # full chat flow with MSW
```

**Total: 121 unit tests, all passing.**

**Key testing patterns:**

```typescript
// Service tests — vi.mock + global.fetch mock
vi.mock('../../../utils/cookieUtils')
global.fetch = vi.fn()

// Component tests — mock service modules
vi.mock('../../../services/authService')

// Page tests — mock useNavigate
vi.mock('react-router-dom', async (importOriginal) => ({
  ...await importOriginal(),
  useNavigate: () => mockNavigate
}))

// Components with router — wrap in MemoryRouter
render(<MemoryRouter><LoginForm /></MemoryRouter>)
```

---

## 10. API Reference

### Base URL

`http://localhost:8000/api/v1`

### Authentication

All protected endpoints require:
```
Authorization: Bearer <access_token>
```

### Auth Endpoints

**Register**
```
POST /auth/register
Content-Type: application/json

{ "email": "user@example.com", "password": "Secure123" }

201 Created
{ "message": "User created successfully" }

409 Conflict — email already exists
422 Unprocessable — weak password
```

**Login**
```
POST /auth/login
Content-Type: application/json

{ "email": "user@example.com", "password": "Secure123" }

200 OK
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}

401 Unauthorized — bad credentials
```

**Refresh Token**
```
POST /auth/refresh
Content-Type: application/json

{ "refresh_token": "eyJ..." }

200 OK
{ "access_token": "eyJ...", "token_type": "bearer" }
```

### Agent Endpoint

**Submit Query**
```
POST /agent/query
Authorization: Bearer <token>
Content-Type: application/json

{ "prompt": "Create a NestJS authentication module with JWT" }

200 OK
{
  "answer": "## NestJS Authentication Module\n\n```typescript\n...",
  "cache_hit": false,
  "metadata": {
    "routing_strategy": "SEARCH_THEN_CODE",
    "agents_invoked": ["supervisor", "search", "codegen"],
    "processing_time_ms": 4823,
    "frameworks_detected": ["nestjs"],
    "token_usage": { "prompt_tokens": 1200, "completion_tokens": 800 }
  }
}

400 Bad Request — empty or invalid prompt
401 Unauthorized — missing/expired token
503 Service Unavailable — LLM API down
504 Gateway Timeout — workflow timed out
```

**Agent Health**
```
GET /agent/health

200 OK
{ "status": "healthy", "cache": "connected", "workflow": "ready" }
```

### Response Formats

All error responses follow:
```json
{
  "detail": "Human-readable error message"
}
```

---

## 11. Known Issues & Gotchas

### Backend

**1. Embedding dimension mismatch**
Migration `change_embedding_dimension_to_384` reduced the semantic_cache embedding dimension from 1536 to 384 (for local embeddings). If you use OpenAI embeddings (1536-dim) and the semantic_cache table has `vector(384)`, cache writes will fail silently. The cache is designed to degrade gracefully, so queries will still work — they just won't be cached.

**Fix:** Ensure your `EMBEDDING_MODEL` and the actual dimension in the database match. If using OpenAI (1536-dim), roll back migration 4 or create a new migration to alter the column back to `vector(1536)`.

**2. alembic.ini target database**
`alembic.ini` connects to `DATABASE_URL` (main DB). The vector DB schema (`framework_documentation`, `semantic_cache`) is managed separately. If you need to run a migration affecting the vector DB, you must either:
- Temporarily update alembic.ini to point to `VECTOR_DATABASE_URL`, or
- Run the migration SQL directly

**3. First-time startup is slow**
Documentation scraping and embedding generation can take 5–35 minutes depending on which frameworks and your internet speed. This only needs to run once. Subsequent starts are fast.

**4. OpenAI rate limits**
If you hit OpenAI rate limits during batch embedding (ingestion), the embedding service will retry automatically (3 attempts, exponential backoff). If it still fails, run `ingest_documentation.py` again — it handles partial ingestion.

**5. MCP service dependency**
The `docker-compose.yml` runs an MCP tool service on port 8001. In local development, this may not be running. The `MCP_SERVICE_URL` can be left unconfigured if you're not using MCP features — the backend handles the connection failure gracefully.

**6. Vector search scores below threshold**
If `vector_search_min_score=0.7` is too restrictive for your use case, lower it. If too permissive, increase it. The re-ranker will re-order results regardless of the initial score filter.

### Frontend

**7. API base URL is hardcoded**
Both `authService.ts` and `agentService.ts` have `http://localhost:8000/api` hardcoded. For production, extract to a `VITE_API_BASE_URL` environment variable:
```typescript
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
```

**8. No syntax highlighting in responses**
`MarkdownRenderer.tsx` renders code blocks as plain `<pre><code>` elements. There is no syntax highlighting library integrated. Consider adding `highlight.js` or `prism-react-renderer`.

**9. No token refresh in frontend**
The frontend stores a refresh token but does not automatically use it when the access token expires. When a 401 is received, the user is logged out entirely. Implementing auto-refresh would improve UX:
- Intercept 401 responses in `authService.ts`
- Call `/auth/refresh` with the refresh token
- Retry the original request with the new access token

**10. Mixed JSX/TSX**
`App.jsx` and `main.jsx` are plain JavaScript. All other files are TypeScript. This is a known inconsistency. If you add new files, use `.tsx` to stay consistent with the majority.

### Infrastructure

**11. Docker compose file selection**
- `docker-compose.yml` — runs everything including FastAPI app (production-like)
- `docker-compose.dev.yml` — infra only (postgres, redis)

Always use `docker-compose.dev.yml` for local development so you can run the backend with hot-reload.

**12. Port conflicts**
Default ports: 5432, 5433, 6379, 8000, 8001, 5173. If any of these are in use, you'll get startup errors. Check with:
```bash
lsof -i :5432   # or use the port in question
```

---

## 12. Development Workflow

### Adding a New API Endpoint

1. Create or update Pydantic schemas in `app/schemas/`
2. Add business logic to the appropriate service in `app/services/`
3. Add the endpoint to the relevant `app/api/v1/endpoints/` file
4. Add tests to `tests/test_<feature>.py`
5. Run `pytest -v` to confirm

### Adding a New Framework

1. Add framework to `app/services/framework_detector.py` keyword list
2. Add framework-specific system prompt to `app/agents/code_gen_agent.py`
3. Add documentation scraping config to `backend/scripts/scrape_documentation.py`
4. Re-run ingestion: `python scripts/ingest_documentation.py`

### Switching LLM Provider

Update `backend/.env`:
```env
# OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# OR Gemini
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
```
Restart the backend. No code changes needed.

### Database Migrations

```bash
# After changing SQLAlchemy models in app/models/
alembic revision --autogenerate -m "add column x to users"
alembic upgrade head

# Check what's been applied
alembic current

# Rollback
alembic downgrade -1
```

### Running the Full Test Suite

```bash
# Backend
cd backend
pytest -v --cov=app --cov-report=term-missing

# Frontend
cd frontend
npm run test:run
```

### Checking System Health

```bash
# All Docker services
docker-compose ps

# Backend API
curl http://localhost:8000/health
curl http://localhost:8000/health/vector-db

# Redis
docker exec ai-agent-redis redis-cli ping

# Document count in vector DB
docker exec ai-agent-postgres-vector psql -U vector_admin -d ai_agent_vectors \
  -c "SELECT framework, COUNT(*) FROM framework_documentation GROUP BY framework;"

# Semantic cache entries
docker exec ai-agent-postgres-vector psql -U vector_admin -d ai_agent_vectors \
  -c "SELECT COUNT(*) FROM semantic_cache;"
```

### Logs

```bash
# Backend log (when run with start_all.sh)
tail -f backend/backend.log

# Docker logs
docker-compose logs -f fastapi-app
docker-compose logs -f postgres

# Backend structured logs (JSON format)
# Set LOG_FORMAT=text in .env for human-readable output during development
```

---

*Last updated: 2026-02-26*
