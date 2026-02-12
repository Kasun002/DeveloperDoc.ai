#!/bin/bash

################################################################################
# DeveloperDoc.ai - Complete System Startup Script
# 
# This script handles the complete startup of the AI Agent System including:
# - Docker services (PostgreSQL, Redis)
# - Documentation scraping and ingestion
# - Backend FastAPI application
# - Frontend React application
#
# Usage:
#   ./start_all.sh              # Full startup with all frameworks
#   ./start_all.sh --quick      # Quick start with essential frameworks only
#   ./start_all.sh --skip-docs  # Skip documentation ingestion
#   ./start_all.sh --backend-only  # Start backend only (no frontend)
#   ./start_all.sh --clean      # Clean start (remove existing data)
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DOCS_DIR="$BACKEND_DIR/docs/scraped"

# Parse command line arguments
QUICK_MODE=false
SKIP_DOCS=false
BACKEND_ONLY=false
CLEAN_MODE=false

for arg in "$@"; do
    case $arg in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --skip-docs)
            SKIP_DOCS=true
            shift
            ;;
        --backend-only)
            BACKEND_ONLY=true
            shift
            ;;
        --clean)
            CLEAN_MODE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --quick         Quick start with essential frameworks only (NestJS, React, FastAPI)"
            echo "  --skip-docs     Skip documentation scraping and ingestion"
            echo "  --backend-only  Start backend only (no frontend)"
            echo "  --clean         Clean start (remove existing data and containers)"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Frameworks to ingest
if [ "$QUICK_MODE" = true ]; then
    FRAMEWORKS="nestjs react fastapi"
    echo -e "${CYAN}🚀 Quick Mode: Using essential frameworks only${NC}"
else
    FRAMEWORKS="nestjs react fastapi django express vue angular spring dotnet"
    echo -e "${CYAN}🚀 Full Mode: Using all frameworks${NC}"
fi

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${CYAN}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        print_success "$1 is installed"
        return 0
    else
        print_error "$1 is not installed"
        return 1
    fi
}

check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port $port is already in use (may be $service already running)"
        return 1
    else
        print_success "Port $port is available"
        return 0
    fi
}

wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    print_step "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start within $((max_attempts * 2)) seconds"
    return 1
}

################################################################################
# Phase 1: Pre-flight Checks
################################################################################

preflight_checks() {
    print_header "Phase 1: Pre-flight Checks"
    
    local checks_passed=true
    
    # Check Docker
    print_step "Checking Docker..."
    if ! check_command docker; then
        print_error "Docker is required. Install from: https://www.docker.com/products/docker-desktop"
        checks_passed=false
    fi
    
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop."
        checks_passed=false
    else
        print_success "Docker is running"
    fi
    
    # Check Python
    print_step "Checking Python..."
    if ! check_command python3; then
        print_error "Python 3.10+ is required"
        checks_passed=false
    else
        python_version=$(python3 --version | cut -d' ' -f2)
        print_success "Python $python_version is installed"
    fi
    
    # Check pip
    if ! check_command pip3; then
        print_error "pip3 is required"
        checks_passed=false
    fi
    
    # Check Node.js (only if not backend-only mode)
    if [ "$BACKEND_ONLY" = false ]; then
        print_step "Checking Node.js..."
        if ! check_command node; then
            print_error "Node.js 18+ is required for frontend"
            checks_passed=false
        else
            node_version=$(node --version)
            print_success "Node.js $node_version is installed"
        fi
        
        if ! check_command npm; then
            print_error "npm is required for frontend"
            checks_passed=false
        fi
    fi
    
    # Check .env file
    print_step "Checking environment configuration..."
    if [ ! -f "$BACKEND_DIR/.env" ] && [ ! -f "$BACKEND_DIR/.env.local" ]; then
        print_error ".env file not found in backend directory"
        print_warning "Creating .env from .env.example..."
        if [ -f "$BACKEND_DIR/.env.example" ]; then
            cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
            print_warning "Please edit backend/.env and configure your settings"
            checks_passed=false
        else
            print_error ".env.example not found"
            checks_passed=false
        fi
    else
        print_success "Environment file found"
        
        # Check for required keys
        env_file="$BACKEND_DIR/.env.local"
        if [ ! -f "$env_file" ]; then
            env_file="$BACKEND_DIR/.env"
        fi
        
        # Check LLM provider configuration
        if grep -q "LLM_PROVIDER=gemini" "$env_file"; then
            print_success "Using Gemini for LLM operations"
            if ! grep -q "GEMINI_API_KEY=" "$env_file" || grep -q "GEMINI_API_KEY=your-gemini-key" "$env_file"; then
                print_warning "GEMINI_API_KEY not set in $env_file"
                print_warning "Please add your Gemini API key to continue"
                checks_passed=false
            fi
        elif grep -q "LLM_PROVIDER=openai" "$env_file"; then
            print_success "Using OpenAI for LLM operations"
            if ! grep -q "OPENAI_API_KEY=" "$env_file" || grep -q "OPENAI_API_KEY=your-openai-key" "$env_file"; then
                print_warning "OPENAI_API_KEY not set in $env_file"
                print_warning "Please add your OpenAI API key to continue"
                checks_passed=false
            fi
        else
            print_warning "LLM_PROVIDER not set (defaulting to OpenAI)"
        fi
        
        # Check embedding configuration
        if grep -q "EMBEDDING_MODEL=all-MiniLM-L6-v2" "$env_file"; then
            print_success "Using local embeddings (no API key needed)"
        else
            print_warning "Embedding model not configured for local embeddings"
            print_warning "Will use local embeddings by default"
        fi
    fi
    
    if [ "$checks_passed" = false ]; then
        print_error "Pre-flight checks failed. Please fix the issues above."
        exit 1
    fi
    
    print_success "All pre-flight checks passed!"
}

################################################################################
# Phase 2: Infrastructure Setup (Docker Services)
################################################################################

start_docker_services() {
    print_header "Phase 2: Starting Docker Services"
    
    cd "$SCRIPT_DIR"
    
    if [ "$CLEAN_MODE" = true ]; then
        print_step "Cleaning existing containers and volumes..."
        docker-compose down -v
        print_success "Cleaned up existing containers"
    fi
    
    print_step "Starting PostgreSQL, PostgreSQL Vector, and Redis..."
    docker-compose up -d postgres postgres-vector redis
    
    print_step "Waiting for services to be healthy..."
    sleep 5
    
    # Check PostgreSQL main
    print_step "Checking PostgreSQL (main database)..."
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker exec ai-agent-postgres pg_isready -U admin -d ai_admin > /dev/null 2>&1; then
            print_success "PostgreSQL main database is ready"
            break
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        print_error "PostgreSQL main database failed to start"
        exit 1
    fi
    
    # Check PostgreSQL vector
    print_step "Checking PostgreSQL Vector (vector database)..."
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker exec ai-agent-postgres-vector pg_isready -U vector_admin -d ai_agent_vectors > /dev/null 2>&1; then
            print_success "PostgreSQL vector database is ready"
            break
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        print_error "PostgreSQL vector database failed to start"
        exit 1
    fi
    
    # Check Redis
    print_step "Checking Redis..."
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker exec ai-agent-redis redis-cli ping > /dev/null 2>&1; then
            print_success "Redis is ready"
            break
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        print_error "Redis failed to start"
        exit 1
    fi
    
    print_success "All Docker services are running!"
}

################################################################################
# Phase 3: Backend Setup
################################################################################

setup_backend() {
    print_header "Phase 3: Backend Setup"
    
    cd "$BACKEND_DIR"
    
    # Install dependencies
    print_step "Installing Python dependencies..."
    if pip3 install -r requirements.txt > /dev/null 2>&1; then
        print_success "Python dependencies installed"
    else
        print_error "Failed to install Python dependencies"
        exit 1
    fi
    
    # Run migrations
    print_step "Running database migrations..."
    if alembic upgrade head; then
        print_success "Database migrations completed"
    else
        print_error "Database migrations failed"
        exit 1
    fi
    
    # Verify and install pgvector extension
    print_step "Verifying pgvector extension..."
    
    # Check if pgvector extension exists
    pgvector_check=$(docker exec ai-agent-postgres-vector psql -U vector_admin -d ai_agent_vectors -t -c "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector';" 2>/dev/null | tr -d ' ' || echo "0")
    
    if [ "$pgvector_check" = "1" ]; then
        # Get version
        pgvector_version=$(docker exec ai-agent-postgres-vector psql -U vector_admin -d ai_agent_vectors -t -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';" 2>/dev/null | tr -d ' ' || echo "unknown")
        print_success "pgvector extension already installed (version $pgvector_version)"
    else
        print_step "Installing pgvector extension..."
        if docker exec ai-agent-postgres-vector psql -U vector_admin -d ai_agent_vectors -c "CREATE EXTENSION IF NOT EXISTS vector;" > /dev/null 2>&1; then
            pgvector_version=$(docker exec ai-agent-postgres-vector psql -U vector_admin -d ai_agent_vectors -t -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';" 2>/dev/null | tr -d ' ' || echo "unknown")
            print_success "pgvector extension installed successfully (version $pgvector_version)"
        else
            print_error "Failed to install pgvector extension"
            print_error "The vector database may not support pgvector"
            exit 1
        fi
    fi
    
    # Verify vector type works
    print_step "Testing vector type functionality..."
    if docker exec ai-agent-postgres-vector psql -U vector_admin -d ai_agent_vectors -c "SELECT '[1,2,3]'::vector;" > /dev/null 2>&1; then
        print_success "Vector type is working correctly"
    else
        print_error "Vector type test failed"
        print_error "pgvector extension may not be properly installed"
        exit 1
    fi
    
    # Check embedding dimension and migrate if needed
    print_step "Checking embedding configuration..."
    current_dim=$(docker exec ai-agent-postgres-vector psql -U vector_admin -d ai_agent_vectors -t -c "SELECT atttypmod FROM pg_attribute WHERE attrelid = 'framework_documentation'::regclass AND attname = 'embedding';" 2>/dev/null | tr -d ' ' || echo "0")
    
    # atttypmod for vector(384) is 388 (384 + 4), for vector(1536) is 1540 (1536 + 4)
    if [ "$current_dim" = "1540" ]; then
        print_warning "Detected OpenAI embeddings (1536-dim). Migrating to local embeddings (384-dim)..."
        print_warning "This will clear existing documentation data (incompatible dimensions)"
        
        # The migration is already in the alembic upgrade head, so it should have run
        # Just verify it worked
        new_dim=$(docker exec ai-agent-postgres-vector psql -U vector_admin -d ai_agent_vectors -t -c "SELECT atttypmod FROM pg_attribute WHERE attrelid = 'framework_documentation'::regclass AND attname = 'embedding';" 2>/dev/null | tr -d ' ' || echo "0")
        
        if [ "$new_dim" = "388" ]; then
            print_success "Successfully migrated to local embeddings (384-dim)"
        else
            print_warning "Migration may not have completed. Current dimension: $new_dim"
        fi
    elif [ "$current_dim" = "388" ]; then
        print_success "Already using local embeddings (384-dim)"
    else
        print_warning "Could not determine embedding dimension (may be first run)"
    fi
    
    print_success "Backend setup completed!"
}

################################################################################
# Phase 4: Documentation Ingestion (DISABLED)
################################################################################

setup_documentation() {
    print_warning "Documentation ingestion disabled - skipping"
    return 0
}

################################################################################
# Phase 5: Start Backend
################################################################################

start_backend() {
    print_header "Phase 5: Starting Backend"
    
    cd "$BACKEND_DIR"
    
    print_step "Starting FastAPI application..."
    
    # Kill existing uvicorn processes
    pkill -f "uvicorn app.main:app" || true
    sleep 2
    
    # Start backend in background
    nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
    BACKEND_PID=$!
    
    echo $BACKEND_PID > backend.pid
    print_success "Backend started (PID: $BACKEND_PID)"
    
    # Wait for backend to be ready
    if wait_for_service "http://localhost:8000/health" "Backend API"; then
        print_success "Backend is ready at http://localhost:8000"
    else
        print_error "Backend failed to start. Check backend/backend.log for details"
        exit 1
    fi
}

################################################################################
# Phase 6: Start Frontend (DISABLED)
################################################################################

start_frontend() {
    print_warning "Frontend startup disabled - backend only mode"
    return 0
}

################################################################################
# Phase 7: Verification & Display Info
################################################################################

verify_and_display() {
    print_header "Phase 7: System Verification"
    
    # Run verification script
    cd "$BACKEND_DIR"
    print_step "Running system verification..."
    
    if python3 scripts/verify_setup.py; then
        print_success "System verification passed!"
    else
        print_warning "Some verification checks failed (see above)"
    fi
    
    # Display access information
    print_header "🎉 System is Ready!"
    
    echo -e "${GREEN}Access URLs:${NC}"
    echo -e "  ${CYAN}Backend API:${NC}        http://localhost:8000"
    echo -e "  ${CYAN}API Documentation:${NC}  http://localhost:8000/docs"
    echo -e "  ${CYAN}Health Check:${NC}       http://localhost:8000/health"
    
    if [ "$BACKEND_ONLY" = false ]; then
        echo -e "  ${CYAN}Frontend App:${NC}       http://localhost:5173"
    fi
    
    echo ""
    echo -e "${GREEN}Database Connections:${NC}"
    echo -e "  ${CYAN}PostgreSQL (main):${NC}   localhost:5432 (admin/admin123)"
    echo -e "  ${CYAN}PostgreSQL (vector):${NC} localhost:5433 (vector_admin/vector123)"
    echo -e "  ${CYAN}Redis:${NC}               localhost:6379"
    
    echo ""
    echo -e "${GREEN}Next Steps:${NC}"
    echo -e "  1. Open http://localhost:5173 in your browser"
    echo -e "  2. Register a new user account"
    echo -e "  3. Try a query: 'Create a NestJS controller for user authentication'"
    
    echo ""
    echo -e "${GREEN}Logs:${NC}"
    echo -e "  ${CYAN}Backend:${NC}  tail -f backend/backend.log"
    echo -e "  ${CYAN}Docker:${NC}   docker-compose logs -f"
    
    echo ""
    echo -e "${YELLOW}To stop all services:${NC}"
    echo -e "  1. Press Ctrl+C to stop frontend"
    echo -e "  2. Run: ./stop_all.sh"
    
    echo ""
}

################################################################################
# Cleanup Handler
################################################################################

cleanup() {
    echo ""
    print_warning "Shutting down..."
    
    # Kill backend if running
    if [ -f "$BACKEND_DIR/backend.pid" ]; then
        backend_pid=$(cat "$BACKEND_DIR/backend.pid")
        if kill -0 "$backend_pid" 2>/dev/null; then
            print_step "Stopping backend (PID: $backend_pid)..."
            kill "$backend_pid"
        fi
        rm -f "$BACKEND_DIR/backend.pid"
    fi
    
    print_success "Shutdown complete. Docker services are still running."
    print_warning "To stop Docker services, run: docker-compose down"
}

trap cleanup EXIT INT TERM

################################################################################
# Main Execution
################################################################################

main() {
    clear
    
    print_header "🚀 DeveloperDoc.ai - Complete System Startup"
    
    echo -e "${CYAN}Configuration:${NC}"
    echo -e "  Mode: Backend Only (Documentation and Frontend disabled)"
    echo -e "  Clean Mode: $([ "$CLEAN_MODE" = true ] && echo "Yes" || echo "No")"
    
    # Execute phases
    preflight_checks
    start_docker_services
    setup_backend
    setup_documentation
    start_backend
    
    # Verification before starting frontend
    verify_and_display
    
    # Frontend disabled - keep backend running
    print_header "Backend Running"
    echo -e "${GREEN}Backend is running at http://localhost:8000${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    
    # Wait indefinitely
    tail -f "$BACKEND_DIR/backend.log"
}

# Run main function
main
