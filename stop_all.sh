#!/bin/bash

################################################################################
# DeveloperDoc.ai - System Shutdown Script
# 
# This script stops all running services including:
# - Backend FastAPI application
# - Frontend React application  
# - Docker services (optional)
#
# Usage:
#   ./stop_all.sh              # Stop backend/frontend, keep Docker running
#   ./stop_all.sh --docker     # Stop everything including Docker services
#   ./stop_all.sh --clean      # Stop and remove all Docker volumes
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Parse arguments
STOP_DOCKER=false
CLEAN_MODE=false

for arg in "$@"; do
    case $arg in
        --docker)
            STOP_DOCKER=true
            shift
            ;;
        --clean)
            STOP_DOCKER=true
            CLEAN_MODE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --docker    Stop Docker services as well"
            echo "  --clean     Stop and remove all Docker volumes (WARNING: deletes data)"
            echo "  --help      Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            exit 1
            ;;
    esac
done

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

################################################################################
# Stop Backend
################################################################################

stop_backend() {
    print_header "Stopping Backend"
    
    cd "$BACKEND_DIR"
    
    # Check for PID file
    if [ -f "backend.pid" ]; then
        backend_pid=$(cat backend.pid)
        if kill -0 "$backend_pid" 2>/dev/null; then
            print_step "Stopping backend (PID: $backend_pid)..."
            kill "$backend_pid"
            sleep 2
            
            # Force kill if still running
            if kill -0 "$backend_pid" 2>/dev/null; then
                print_warning "Force killing backend..."
                kill -9 "$backend_pid"
            fi
            
            print_success "Backend stopped"
        else
            print_warning "Backend process not running (stale PID file)"
        fi
        rm -f backend.pid
    else
        print_warning "No backend PID file found"
    fi
    
    # Kill any remaining uvicorn processes
    print_step "Checking for remaining uvicorn processes..."
    if pkill -f "uvicorn app.main:app"; then
        print_success "Killed remaining uvicorn processes"
    else
        print_success "No remaining uvicorn processes"
    fi
    
    # Clean up log file
    if [ -f "backend.log" ]; then
        print_step "Archiving backend log..."
        mv backend.log "backend.log.$(date +%Y%m%d_%H%M%S)"
        print_success "Log archived"
    fi
}

################################################################################
# Stop Frontend
################################################################################

stop_frontend() {
    print_header "Stopping Frontend"
    
    # Kill any Vite processes
    print_step "Checking for Vite processes..."
    if pkill -f "vite"; then
        print_success "Vite processes stopped"
    else
        print_success "No Vite processes running"
    fi
    
    # Kill any node processes running on port 5173
    print_step "Checking for processes on port 5173..."
    if lsof -ti:5173 | xargs kill -9 2>/dev/null; then
        print_success "Processes on port 5173 stopped"
    else
        print_success "No processes on port 5173"
    fi
}

################################################################################
# Stop Docker Services
################################################################################

stop_docker_services() {
    if [ "$STOP_DOCKER" = false ]; then
        print_warning "Docker services left running (use --docker to stop them)"
        return 0
    fi
    
    print_header "Stopping Docker Services"
    
    cd "$SCRIPT_DIR"
    
    if [ "$CLEAN_MODE" = true ]; then
        print_warning "Clean mode: This will DELETE all data in Docker volumes!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            print_warning "Cancelled. Stopping containers without removing volumes."
            docker-compose down
        else
            print_step "Stopping and removing containers and volumes..."
            docker-compose down -v
            print_success "All containers and volumes removed"
        fi
    else
        print_step "Stopping Docker containers..."
        docker-compose down
        print_success "Docker containers stopped"
    fi
}

################################################################################
# Main Execution
################################################################################

main() {
    print_header "🛑 DeveloperDoc.ai - System Shutdown"
    
    stop_backend
    stop_frontend
    stop_docker_services
    
    print_header "✓ Shutdown Complete"
    
    if [ "$STOP_DOCKER" = false ]; then
        echo -e "${CYAN}Docker services are still running:${NC}"
        echo -e "  - PostgreSQL (main): localhost:5432"
        echo -e "  - PostgreSQL (vector): localhost:5433"
        echo -e "  - Redis: localhost:6379"
        echo ""
        echo -e "${YELLOW}To stop Docker services:${NC}"
        echo -e "  ./stop_all.sh --docker"
        echo ""
        echo -e "${YELLOW}To remove all data:${NC}"
        echo -e "  ./stop_all.sh --clean"
    else
        echo -e "${GREEN}All services stopped${NC}"
        if [ "$CLEAN_MODE" = false ]; then
            echo ""
            echo -e "${CYAN}Data preserved in Docker volumes${NC}"
            echo -e "${YELLOW}To remove all data: ./stop_all.sh --clean${NC}"
        fi
    fi
    
    echo ""
    echo -e "${CYAN}To start again: ./start_all.sh${NC}"
    echo ""
}

main
