#!/bin/bash
# Development server startup script for Unix systems (macOS/Linux)
# Starts both backend and frontend, handles graceful shutdown

set -eo pipefail

cd "$(dirname "$0")" || exit 1

# Color codes
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Store PIDs for cleanup
BACKEND_PID=""
FRONTEND_PID=""

log() {
    local prefix=$1
    local message=$2
    local color=$3
    echo -e "${color}${BOLD}[${prefix}]${NC} ${message}"
}

cleanup() {
    local exit_code=${1:-$?}
    trap - SIGINT SIGTERM EXIT
    log "SYSTEM" "Shutting down servers..." "$YELLOW"
    
    if [ ! -z "$BACKEND_PID" ]; then
        kill -TERM "$BACKEND_PID" 2>/dev/null || true
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill -TERM "$FRONTEND_PID" 2>/dev/null || true
    fi
    
    # Wait a moment for graceful shutdown
    sleep 1
    
    # Force kill if still running
    if [ ! -z "$BACKEND_PID" ]; then
        kill -9 "$BACKEND_PID" 2>/dev/null || true
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill -9 "$FRONTEND_PID" 2>/dev/null || true
    fi
    
    log "SYSTEM" "All servers stopped" "$YELLOW"
    exit "$exit_code"
}

# Set up signal handlers
trap 'cleanup $?' SIGINT SIGTERM EXIT

# Print header
echo -e "\n${CYAN}${BOLD}╔═══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║   ADK Context Engineering - Dev Server   ║${NC}"
echo -e "${CYAN}${BOLD}╚═══════════════════════════════════════════╝${NC}\n"

log "SYSTEM" "Platform: $(uname -s) ($(uname -m))" "$CYAN"
log "SYSTEM" "Starting development servers..." "$CYAN"

# Check if venv exists
if [ ! -f venv/bin/activate ]; then
    log "ERROR" "Virtual environment not found!" "$RED"
    log "ERROR" "Please run: python -m venv venv" "$RED"
    log "ERROR" "Then: source venv/bin/activate && pip install -r requirements.txt" "$RED"
    exit 1
fi

# Start backend
log "BACKEND" "Starting FastAPI server..." "$BLUE"
(
    source venv/bin/activate
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 2>&1 | while IFS= read -r line; do
        log "BACKEND" "$line" "$BLUE"
    done
) &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Start frontend
log "FRONTEND" "Starting Vite dev server..." "$GREEN"
(
    cd frontend
    pnpm dev 2>&1 | while IFS= read -r line; do
        log "FRONTEND" "$line" "$GREEN"
    done
) &
FRONTEND_PID=$!

# Wait a moment for both to initialize
sleep 2

# Print status
echo -e "\n${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log "SYSTEM" "✨ Development servers are running!" "$CYAN"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log "BACKEND" "http://localhost:8000 (API)" "$BLUE"
log "BACKEND" "http://localhost:8000/docs (API Docs)" "$BLUE"
log "FRONTEND" "http://localhost:5173 (UI)" "$GREEN"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log "SYSTEM" "Press Ctrl+C to stop all servers" "$YELLOW"
echo ""

# Wait for either process to exit
wait

