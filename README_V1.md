# DeveloperDoc.ai - Quick Start Guide

> AI-powered code generation with framework documentation search

## Overview

DeveloperDoc.ai is an intelligent code generation system that combines multi-agent AI architecture with semantic documentation search. It helps developers generate framework-compliant code by automatically searching relevant documentation and applying best practices.

**Key Capabilities**:
- Framework-aware code generation (NestJS, React, FastAPI, Django, Express, Vue, Angular, Spring Boot, .NET Core)
- Semantic documentation search with vector similarity
- Multi-agent orchestration with supervisor routing
- Two-tier caching for optimal performance
- Support for OpenAI and Google Gemini AI

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐        │
│  │   Login    │  │  Register  │  │    Chat    │        │
│  └────────────┘  └────────────┘  └────────────┘        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ HTTP/REST API
┌─────────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                       │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │           Semantic Cache (Redis)               │    │
│  │         Check for similar queries              │    │
│  └────────────────────────────────────────────────┘    │
│                          │                              │
│                          ▼                              │
│  ┌────────────────────────────────────────────────┐    │
│  │         LangGraph Workflow Engine              │    │
│  │                                                 │    │
│  │  ┌──────────────────────────────────────┐     │    │
│  │  │      Supervisor Agent (GPT-3.5)      │     │    │
│  │  │   Analyzes prompt & routes request   │     │    │
│  │  └──────────────────────────────────────┘     │    │
│  │                    │                           │    │
│  │         ┌──────────┴──────────┐               │    │
│  │         ▼                     ▼               │    │
│  │  ┌─────────────┐      ┌─────────────┐        │    │
│  │  │   Search    │      │  Code Gen   │        │    │
│  │  │   Agent     │      │   Agent     │        │    │
│  │  │   (MCP)     │      │ (GPT-3.5)   │        │    │
│  │  └─────────────┘      └─────────────┘        │    │
│  └────────────────────────────────────────────────┘    │
│                          │                              │
│                          ▼                              │
│  ┌────────────────────────────────────────────────┐    │
│  │         Vector Database (pgvector)             │    │
│  │    Framework documentation embeddings          │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### How It Works

#### 1. Multi-Agent System

**Supervisor Agent**:
- Analyzes incoming prompts
- Determines routing strategy (SEARCH_ONLY, CODE_ONLY, SEARCH_THEN_CODE)
- Orchestrates workflow between agents

**Documentation Search Agent**:
- Performs semantic search using pgvector
- Applies cross-encoder re-ranking for relevance
- Self-corrects on low confidence results
- Caches results for 5 minutes

**Code Generation Agent**:
- Generates framework-compliant code
- Uses documentation context from search
- Validates syntax automatically
- Retries on errors (max 2 attempts)

#### 2. Workflow Process

```
User Query → Semantic Cache Check
                    │
                    ├─ Cache Hit → Return Cached Response
                    │
                    └─ Cache Miss → Supervisor Agent
                                        │
                                        ├─ Route: SEARCH_ONLY
                                        │     └─→ Search Docs → Return Results
                                        │
                                        ├─ Route: CODE_ONLY
                                        │     └─→ Generate Code → Validate → Return
                                        │
                                        └─ Route: SEARCH_THEN_CODE
                                              └─→ Search Docs → Generate Code → Validate
                                                      │
                                                      ├─ Valid → Cache & Return
                                                      │
                                                      └─ Invalid → Retry or Search Again
```

#### 3. Caching Strategy

**Semantic Cache** (Redis + pgvector):
- Stores responses with embeddings
- Similarity threshold: 0.95
- TTL: 1 hour
- Reduces LLM API calls by ~40%

**Tool Cache** (Redis):
- Caches MCP tool results
- TTL: 5 minutes
- Reduces vector search operations

---

## Backend Architecture

### Technology Stack

- **Framework**: FastAPI (Python 3.10+)
- **AI/ML**: LangGraph, LangChain, OpenAI API, Google Gemini API
- **Databases**: PostgreSQL (main + vector with pgvector), Redis
- **Observability**: OpenTelemetry, structlog

### Project Structure

```
backend/
├── app/
│   ├── agents/                    # AI Agents
│   │   ├── supervisor_agent.py   # Routes requests
│   │   ├── documentation_search_agent.py  # Searches docs
│   │   ├── code_gen_agent.py     # Generates code
│   │   └── syntax_validator.py   # Validates syntax
│   │
│   ├── api/v1/endpoints/          # API Endpoints
│   │   ├── auth.py               # Authentication
│   │   ├── agent.py              # AI Agent queries
│   │   └── dashboard.py          # User dashboard
│   │
│   ├── core/                      # Core functionality
│   │   ├── config.py             # Configuration
│   │   ├── database.py           # Main DB connection
│   │   ├── vector_database.py    # Vector DB manager
│   │   ├── security.py           # JWT & auth
│   │   └── telemetry.py          # OpenTelemetry
│   │
│   ├── services/                  # Business logic
│   │   ├── embedding_service.py  # Generate embeddings
│   │   ├── semantic_cache.py     # Semantic caching
│   │   ├── tool_cache.py         # Tool result caching
│   │   ├── vector_search_service.py  # Vector search
│   │   ├── reranking_service.py  # Re-rank results
│   │   ├── framework_detector.py # Auto-detect framework
│   │   └── gemini_client.py      # Gemini AI client
│   │
│   ├── workflows/                 # LangGraph workflows
│   │   └── agent_workflow.py     # Orchestration logic
│   │
│   └── main.py                    # Application entry
│
├── alembic/                       # Database migrations
├── tests/                         # Test suite
├── requirements.txt               # Python dependencies
└── .env                          # Environment variables
```

### Key Features

**Multi-Agent Orchestration**:
- Supervisor routes to specialized agents
- Iterative refinement with cycles
- Max 3 workflow iterations

**Vector Search**:
- pgvector with HNSW indexing (O(log N) performance)
- 1536-dimensional embeddings (text-embedding-3-small)
- Cross-encoder re-ranking for accuracy

**LLM Provider Flexibility**:
- OpenAI (gpt-3.5-turbo) - Default
- Google Gemini (gemini-1.5-flash) - Alternative
- Switch with single environment variable

**Observability**:
- OpenTelemetry distributed tracing
- Structured JSON logging
- Trace IDs for request tracking

---

## Frontend Architecture

### Technology Stack

- **Framework**: React 19.2.0 with TypeScript
- **Build Tool**: Vite 7.2.4
- **Styling**: Tailwind CSS 4.1.18
- **Routing**: React Router DOM 7.13.0
- **Forms**: React Hook Form 7.71.1
- **Notifications**: React Hot Toast 2.6.0

### Project Structure

```
frontend/
├── src/
│   ├── components/               # UI Components
│   │   ├── ChatInterface.tsx    # Main chat UI
│   │   ├── LoginForm.tsx        # Login form
│   │   ├── RegisterForm.tsx     # Registration form
│   │   └── MarkdownRenderer.tsx # Display AI responses
│   │
│   ├── pages/                   # Page components
│   │   ├── ChatPage.tsx         # Chat page
│   │   ├── LoginPage.tsx        # Login page
│   │   └── RegisterPage.tsx     # Register page
│   │
│   ├── routes/                  # Routing
│   │   ├── AppRouter.tsx        # Main router
│   │   └── ProtectedRoute.tsx   # Auth guard
│   │
│   ├── services/                # API services
│   │   ├── authService.ts       # Auth API calls
│   │   └── agentService.ts      # Agent API calls
│   │
│   ├── utils/                   # Utilities
│   │   ├── toast.ts             # Toast notifications
│   │   └── cookieUtils.ts       # Cookie management
│   │
│   ├── App.jsx                  # Root component
│   └── main.jsx                 # Entry point
│
├── public/                      # Static assets
├── package.json                 # Dependencies
└── vite.config.js              # Vite config
```

### Key Features

**Authentication**:
- JWT-based authentication
- Secure cookie storage
- Protected routes with guards
- Auto-redirect on session expiration

**Chat Interface**:
- ChatGPT-like UI design
- Real-time query submission
- Markdown rendering for responses
- Loading states with spinners

**Toast Notifications**:
- Success (green) - Successful operations
- Error (red) - Failed operations
- Loading (blue) - In-progress operations
- Auto-dismiss with smooth animations

**Responsive Design**:
- Mobile-first approach
- Works on all screen sizes
- Touch-friendly interface

---

## Local Setup

### Prerequisites

- **Docker Desktop** (for databases)
- **Python 3.10+** and pip
- **Node.js 18+** and npm
- **OpenAI API Key** (or Gemini API Key)

### 1. Clone Repository

```bash
git clone <repository-url>
cd developerdoc-ai
```

### 2. Start Infrastructure Services

```bash
# Start PostgreSQL (main + vector) and Redis
docker-compose up -d postgres postgres-vector redis
```

Verify services are running:
```bash
docker-compose ps
```

You should see:
- `postgres` - Main PostgreSQL (port 5432)
- `postgres-vector` - Vector PostgreSQL (port 5433)
- `redis` - Redis cache (port 6379)

### 3. Setup Backend

#### Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

#### Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API key:
```env
# Required
OPENAI_API_KEY=sk-your-openai-api-key-here

# Or use Gemini instead
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key-here

# Database URLs (already configured for local Docker)
DATABASE_URL=postgresql://admin:admin123@localhost:5432/ai_admin
VECTOR_DATABASE_URL=postgresql://vector_admin:vector123@localhost:5433/ai_agent_vectors
REDIS_URL=redis://localhost:6379/0

# JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-256-bit-secret-key-change-in-production
```

#### Run Database Migrations

```bash
alembic upgrade head
```

#### Start Backend Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

### 4. Setup Frontend

#### Install Dependencies

```bash
cd frontend
npm install
```

#### Start Development Server

```bash
npm run dev
```

Frontend will be available at: `http://localhost:5173`

### 5. Verify Setup

#### Check Backend Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

#### Check Frontend

Open browser: `http://localhost:5173`

You should see the login page.

### 6. Test the Application

1. **Register a new user**:
   - Go to `http://localhost:5173/register`
   - Enter email and password
   - Click "Register"
   - You should see a success toast and be redirected to chat

2. **Submit a query**:
   - Enter: "Create a NestJS controller for user authentication"
   - Click "Send"
   - You should see:
     - Blue loading toast
     - Green success toast when complete
     - AI-generated code in markdown format

---

## Quick Commands Reference

### Backend

```bash
# Start backend
cd backend
uvicorn app.main:app --reload

# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Run tests
pytest -v

# Check health
curl http://localhost:8000/health
```

### Frontend

```bash
# Start frontend
cd frontend
npm run dev

# Build for production
npm run build

# Run linter
npm run lint

# Preview production build
npm run preview
```

### Docker Services

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f postgres
docker-compose logs -f redis

# Restart a service
docker-compose restart postgres
```

### Database

```bash
# Connect to main database
docker exec -it postgres psql -U admin -d ai_admin

# Connect to vector database
docker exec -it postgres-vector psql -U vector_admin -d ai_agent_vectors

# Connect to Redis
docker exec -it redis redis-cli
```

---

## Environment Variables

### Backend (.env)

```env
# Application
APP_ENV=development
APP_NAME=DeveloperDocAI

# Databases
DATABASE_URL=postgresql://admin:admin123@localhost:5432/ai_admin
VECTOR_DATABASE_URL=postgresql://vector_admin:vector123@localhost:5433/ai_agent_vectors
REDIS_URL=redis://localhost:6379/0

# LLM Provider (choose one)
LLM_PROVIDER=openai                    # or "gemini"
OPENAI_API_KEY=sk-your-key-here       # if using OpenAI
GEMINI_API_KEY=your-key-here          # if using Gemini

# JWT Configuration
JWT_SECRET_KEY=your-256-bit-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Agent Configuration
SEMANTIC_CACHE_THRESHOLD=0.95
SEMANTIC_CACHE_TTL=3600
TOOL_CACHE_TTL=300
MAX_WORKFLOW_ITERATIONS=3

# Vector Search
VECTOR_SEARCH_TOP_K=10
VECTOR_SEARCH_MIN_SCORE=0.7

# Observability
OTEL_ENABLED=true
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Frontend

No environment variables needed for local development. Backend URL is hardcoded to `http://localhost:8000`.

For production, update API URLs in:
- `frontend/src/services/authService.ts`
- `frontend/src/services/agentService.ts`

---

## Troubleshooting

### Backend Issues

**Can't connect to database**:
```bash
# Check if containers are running
docker-compose ps

# Restart PostgreSQL
docker-compose restart postgres postgres-vector
```

**OpenAI API errors**:
- Verify API key is correct in `.env`
- Check API key has sufficient credits
- Try switching to Gemini: `LLM_PROVIDER=gemini`

**Migration errors**:
```bash
# Check current migration status
alembic current

# Rollback and reapply
alembic downgrade -1
alembic upgrade head
```

### Frontend Issues

**Can't connect to backend**:
- Verify backend is running on `http://localhost:8000`
- Check backend health: `curl http://localhost:8000/health`
- Check browser console for CORS errors

**Toast notifications not showing**:
```bash
# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

**Build errors**:
```bash
# Clear cache and rebuild
rm -rf node_modules dist
npm install
npm run build
```

---

## Switching LLM Providers

### From OpenAI to Gemini

1. Get Gemini API key: https://makersuite.google.com/app/apikey

2. Update `backend/.env`:
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
```

3. Restart backend:
```bash
# Stop with Ctrl+C, then restart
uvicorn app.main:app --reload
```

### From Gemini to OpenAI

Update `backend/.env`:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key
```

Restart backend.

---

## Project Status

**Version**: 1.2.0  
**Status**: Production Ready ✅

**Backend**: Operational
- Multi-agent system
- Vector search
- Semantic caching
- OpenAI & Gemini support

**Frontend**: Operational
- React application
- Authentication
- Chat interface
- Toast notifications

---

## Documentation

**Detailed Documentation**:
- [Full README](README.md) - Complete documentation
- [Backend README](backend/README.md) - Backend details
- [Frontend Toast Docs](frontend/TOAST_SETUP_COMPLETE.md) - Toast notifications

**Specifications**:
- [AI Agent Design](.kiro/specs/ai-agent/design.md)
- [Gemini Integration](.kiro/specs/gemini-ai-integration/)

**External Resources**:
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Docs](https://react.dev/)
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)

---

## Support

For issues or questions:
1. Check the [Full README](README.md)
2. Review troubleshooting section above
3. Check Docker logs: `docker-compose logs -f`
4. Verify environment variables in `.env`

---

**Built with ❤️ by the DeveloperDoc.ai Team**
