#!/bin/bash
# =============================================================================
# BekoSIRS Unified Startup Script
# =============================================================================
# This script starts all BekoSIRS services in the correct order with health checks.
#
# Usage: ./start-all.sh [options]
#   --backend-only    Start only the backend server
#   --web-only        Start only the web panel (requires backend running)
#   --mobile-only     Start only the mobile app (requires backend running)
#   --help            Show this help message
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directories
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/BekoSIRS_api"
WEB_DIR="$PROJECT_ROOT/BekoSIRS_Web"
MOBILE_DIR="$PROJECT_ROOT/BekoSIRS_Frontend"

# Log functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Display header
print_header() {
    echo ""
    echo -e "${BLUE}=============================================${NC}"
    echo -e "${BLUE}   BekoSIRS - Unified Startup Script         ${NC}"
    echo -e "${BLUE}=============================================${NC}"
    echo ""
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing=0
    
    if ! command_exists python3; then
        log_error "Python 3 is not installed"
        missing=1
    fi
    
    if ! command_exists npm; then
        log_error "Node.js/npm is not installed"
        missing=1
    fi
    
    if ! command_exists node; then
        log_error "Node.js is not installed"
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        log_error "Please install missing prerequisites and try again."
        exit 1
    fi
    
    log_success "All prerequisites found!"
}

# Check if backend is running
check_backend_health() {
    local max_attempts=30
    local attempt=1
    
    log_info "Checking backend health..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:8000/api/v1/health/" > /dev/null 2>&1 || \
           curl -s "http://localhost:8000/api/v1/" > /dev/null 2>&1; then
            log_success "Backend is healthy!"
            return 0
        fi
        
        echo -n "."
        sleep 1
        ((attempt++))
    done
    
    echo ""
    log_warning "Backend health check timed out, but it may still be starting..."
    return 1
}

# Start Backend
start_backend() {
    log_info "Starting Backend API..."
    
    if [ ! -d "$BACKEND_DIR" ]; then
        log_error "Backend directory not found: $BACKEND_DIR"
        exit 1
    fi
    
    cd "$BACKEND_DIR"
    
    # Check for virtual environment
    if [ -d "venv" ]; then
        source venv/bin/activate
        log_info "Activated virtual environment"
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
        log_info "Activated virtual environment"
    fi
    
    # Run migrations
    log_info "Running database migrations..."
    python manage.py migrate --no-input 2>/dev/null || log_warning "Migration check failed (may already be up to date)"
    
    # Start server in background
    log_info "Starting Django development server on 0.0.0.0:8000..."
    python manage.py runserver 0.0.0.0:8000 &
    BACKEND_PID=$!
    echo $BACKEND_PID > /tmp/bekosirs_backend.pid
    
    # Wait for backend to be ready
    sleep 3
    check_backend_health
    
    log_success "Backend started with PID: $BACKEND_PID"
}

# Start Web Panel
start_web() {
    log_info "Starting Web Panel..."
    
    if [ ! -d "$WEB_DIR" ]; then
        log_error "Web directory not found: $WEB_DIR"
        exit 1
    fi
    
    cd "$WEB_DIR"
    
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        log_info "Installing web dependencies..."
        npm install
    fi
    
    # Start dev server in background
    log_info "Starting Vite development server..."
    npm run dev -- --host &
    WEB_PID=$!
    echo $WEB_PID > /tmp/bekosirs_web.pid
    
    sleep 3
    log_success "Web Panel started with PID: $WEB_PID"
    log_info "Web Panel available at: http://localhost:5173"
}

# Start Mobile App
start_mobile() {
    log_info "Starting Mobile App (Expo)..."
    
    if [ ! -d "$MOBILE_DIR" ]; then
        log_error "Mobile directory not found: $MOBILE_DIR"
        exit 1
    fi
    
    cd "$MOBILE_DIR"
    
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        log_info "Installing mobile dependencies..."
        npm install
    fi
    
    # Start Expo
    log_info "Starting Expo development server..."
    npx expo start &
    MOBILE_PID=$!
    echo $MOBILE_PID > /tmp/bekosirs_mobile.pid
    
    log_success "Mobile App started with PID: $MOBILE_PID"
}

# Stop all services
stop_all() {
    log_info "Stopping all BekoSIRS services..."
    
    if [ -f /tmp/bekosirs_backend.pid ]; then
        kill $(cat /tmp/bekosirs_backend.pid) 2>/dev/null && log_info "Stopped backend"
        rm /tmp/bekosirs_backend.pid
    fi
    
    if [ -f /tmp/bekosirs_web.pid ]; then
        kill $(cat /tmp/bekosirs_web.pid) 2>/dev/null && log_info "Stopped web panel"
        rm /tmp/bekosirs_web.pid
    fi
    
    if [ -f /tmp/bekosirs_mobile.pid ]; then
        kill $(cat /tmp/bekosirs_mobile.pid) 2>/dev/null && log_info "Stopped mobile app"
        rm /tmp/bekosirs_mobile.pid
    fi
    
    log_success "All services stopped."
}

# Show help
show_help() {
    echo "BekoSIRS Unified Startup Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --backend-only    Start only the backend server"
    echo "  --web-only        Start only the web panel (requires backend running)"
    echo "  --mobile-only     Start only the mobile app (requires backend running)"
    echo "  --stop            Stop all running services"
    echo "  --help            Show this help message"
    echo ""
    echo "Default (no options): Start backend and web panel"
}

# Main execution
main() {
    print_header
    
    case "${1:-}" in
        --help)
            show_help
            exit 0
            ;;
        --stop)
            stop_all
            exit 0
            ;;
        --backend-only)
            check_prerequisites
            start_backend
            ;;
        --web-only)
            check_prerequisites
            start_web
            ;;
        --mobile-only)
            check_prerequisites
            start_mobile
            ;;
        *)
            check_prerequisites
            start_backend
            start_web
            ;;
    esac
    
    echo ""
    log_success "=== BekoSIRS Services Started ==="
    echo ""
    echo -e "Backend API:  ${GREEN}http://localhost:8000${NC}"
    echo -e "Web Panel:    ${GREEN}http://localhost:5173${NC}"
    echo ""
    echo "Press Ctrl+C to stop all services"
    
    # Wait for background processes
    wait
}

# Handle Ctrl+C
trap 'echo ""; log_info "Shutting down..."; stop_all; exit 0' INT TERM

# Run main
main "$@"
