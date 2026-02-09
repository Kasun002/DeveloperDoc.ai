#!/bin/bash

# AI Agent System - Local Development Startup Script
# This script starts all services required for local development

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
print_message "$BLUE" "AI Agent System - Local Development Setup"
print_message "$BLUE" "=========================================="
echo ""

# Check if .env file exists
if [ ! -f "backend/.env" ] && [ ! -f "backend/.env.local" ]; then
    print_message "$YELLOW" "⚠ No .env or .env.local file found in backend/"
    print_message "$YELLOW" "Creating .env from .env.example..."
    
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        print_message "$GREEN" "✓ Created backend/.env from .env.example"
        print_message "$YELLOW" "⚠ Please edit backend/.env and add your OPENAI_API_KEY and other secrets"
        print_message "$YELLOW" "Then run this script again."
        exit 1
    else
        print_message "$RED" "✗ backend/.env.example not found!"
        exit 1
    fi
fi

# Check if OPENAI_API_KEY is set
if [ -f "backend/.env" ]; then
    source backend/.env
elif [ -f "backend/.env.local" ]; then
    source backend/.env.local
fi

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your-openai-key" ]; then
    print_message "$RED" "✗ OPENAI_API_KEY is not set in your .env file"
    print_message "$YELLOW" "Please add your OpenAI API key to backend/.env or backend/.env.local"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_message "$RED" "✗ Docker is not running. Please start Docker and try again."
    exit 1
fi

print_message "$GREEN" "✓ Docker is running"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_message "$RED" "✗ docker-compose is not installed. Please install it and try again."
    exit 1
fi

print_message "$GREEN" "✓ docker-compose is available"
echo ""

# Parse command line arguments
DEV_MODE=false
REBUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            DEV_MODE=true
            shift
            ;;
        --rebuild)
            REBUILD=true
            shift
            ;;
        --help)
            echo "Usage: ./run_local.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dev       Start with development tools (pgAdmin, Redis Commander)"
            echo "  --rebuild   Rebuild Docker images before starting"
            echo "  --help      Show this help message"
            exit 0
            ;;
        *)
            print_message "$RED" "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Stop any running containers
print_message "$BLUE" "Stopping any running containers..."
docker-compose down

# Rebuild if requested
if [ "$REBUILD" = true ]; then
    print_message "$BLUE" "Rebuilding Docker images..."
    docker-compose build --no-cache
fi

# Start services
if [ "$DEV_MODE" = true ]; then
    print_message "$BLUE" "Starting services in development mode..."
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
else
    print_message "$BLUE" "Starting services..."
    docker-compose up -d
fi

# Wait for services to be healthy
print_message "$BLUE" "Waiting for services to be healthy..."
sleep 5

# Check service health
print_message "$BLUE" "Checking service health..."
echo ""

# Check PostgreSQL
if docker-compose ps postgres | grep -q "Up"; then
    print_message "$GREEN" "✓ PostgreSQL (main) is running on port 5432"
else
    print_message "$RED" "✗ PostgreSQL (main) failed to start"
fi

# Check PostgreSQL Vector
if docker-compose ps postgres-vector | grep -q "Up"; then
    print_message "$GREEN" "✓ PostgreSQL (vector) is running on port 5433"
else
    print_message "$RED" "✗ PostgreSQL (vector) failed to start"
fi

# Check Redis
if docker-compose ps redis | grep -q "Up"; then
    print_message "$GREEN" "✓ Redis is running on port 6379"
else
    print_message "$RED" "✗ Redis failed to start"
fi

# Check FastAPI
if docker-compose ps fastapi-app | grep -q "Up"; then
    print_message "$GREEN" "✓ FastAPI app is running on port 8000"
else
    print_message "$RED" "✗ FastAPI app failed to start"
fi

# Check MCP Tool
if docker-compose ps mcp-tool | grep -q "Up"; then
    print_message "$GREEN" "✓ MCP Tool service is running on port 8001"
else
    print_message "$RED" "✗ MCP Tool service failed to start"
fi

echo ""
print_message "$BLUE" "=========================================="
print_message "$GREEN" "Services are starting up!"
print_message "$BLUE" "=========================================="
echo ""
print_message "$BLUE" "Service URLs:"
print_message "$BLUE" "  - FastAPI App:     http://localhost:8000"
print_message "$BLUE" "  - API Docs:        http://localhost:8000/docs"
print_message "$BLUE" "  - MCP Tool:        http://localhost:8001"
print_message "$BLUE" "  - PostgreSQL:      localhost:5432"
print_message "$BLUE" "  - PostgreSQL Vec:  localhost:5433"
print_message "$BLUE" "  - Redis:           localhost:6379"

if [ "$DEV_MODE" = true ]; then
    echo ""
    print_message "$BLUE" "Development Tools:"
    print_message "$BLUE" "  - pgAdmin:         http://localhost:5050"
    print_message "$BLUE" "    (email: admin@example.com, password: admin)"
    print_message "$BLUE" "  - Redis Commander: http://localhost:8081"
fi

echo ""
print_message "$BLUE" "Useful commands:"
print_message "$BLUE" "  - View logs:       docker-compose logs -f"
print_message "$BLUE" "  - Stop services:   docker-compose down"
print_message "$BLUE" "  - Restart:         docker-compose restart"
print_message "$BLUE" "  - Run migrations:  ./scripts/migrate.sh"
print_message "$BLUE" "  - Ingest docs:     ./scripts/ingest_docs.sh"
echo ""
print_message "$GREEN" "✓ Setup complete! Your AI Agent System is ready."
