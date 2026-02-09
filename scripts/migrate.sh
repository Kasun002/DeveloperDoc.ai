#!/bin/bash

# Database Migration Script
# This script runs Alembic migrations for the AI Agent System

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
print_message "$BLUE" "AI Agent System - Database Migration"
print_message "$BLUE" "=========================================="
echo ""

# Check if running in Docker or local
if [ -f "/.dockerenv" ]; then
    # Running inside Docker container
    print_message "$BLUE" "Running migrations inside Docker container..."
    cd /app
    alembic upgrade head
else
    # Running on host machine
    print_message "$BLUE" "Running migrations on host machine..."
    
    # Check if backend directory exists
    if [ ! -d "backend" ]; then
        print_message "$RED" "✗ backend directory not found. Please run this script from the project root."
        exit 1
    fi
    
    cd backend
    
    # Check if alembic is installed
    if ! command -v alembic &> /dev/null; then
        print_message "$RED" "✗ Alembic is not installed. Please install it with: pip install alembic"
        exit 1
    fi
    
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
    
    # Check if DATABASE_URL is set
    if [ -z "$DATABASE_URL" ]; then
        print_message "$RED" "✗ DATABASE_URL is not set in .env file"
        exit 1
    fi
    
    print_message "$GREEN" "✓ Environment loaded"
    
    # Run migrations
    print_message "$BLUE" "Running Alembic migrations..."
    alembic upgrade head
fi

print_message "$GREEN" "✓ Database migrations completed successfully"
echo ""

# Show current migration status
print_message "$BLUE" "Current migration status:"
alembic current

echo ""
print_message "$BLUE" "Migration history:"
alembic history --verbose | head -n 20

echo ""
print_message "$GREEN" "✓ Migration script completed"
