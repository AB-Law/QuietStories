#!/usr/bin/env bash

# QuietStories FastAPI with Centralized Logging

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Configuration
LOG_LEVEL=${LOG_LEVEL:-"INFO"}
ENABLE_CONSOLE_LOGS=${ENABLE_CONSOLE_LOGS:-"false"}  # Default to file-only for production
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"8000"}
WORKERS=${WORKERS:-"1"}

# Export environment variables for the application
export LOG_LEVEL
export ENABLE_CONSOLE_LOGS

usage() {
    cat << EOF
QuietStories FastAPI with Centralized Logging

Usage: $0 [OPTIONS]

Options:
    --dev              Development mode (enable console logs, reload)
    --prod             Production mode (file-only logs, optimized)
    --console          Enable console logging (default: file-only)
    --log-level LEVEL  Set log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
    --port PORT        Set port (default: 8000)
    --workers NUM      Number of workers for production (default: 1)
    --help             Show this help

Examples:
    $0 --dev                    # Development with console logs and reload
    $0 --prod --workers 4       # Production with 4 workers
    $0 --console --log-level DEBUG  # Debug mode with console output

Environment Variables:
    LOG_LEVEL              Log level (DEBUG, INFO, WARNING, ERROR)
    ENABLE_CONSOLE_LOGS    Enable console output (true/false)
    HOST                   Bind address (default: 0.0.0.0)
    PORT                   Port number (default: 8000)
    WORKERS               Number of workers (default: 1)

EOF
}

# Parse command line arguments
DEV_MODE=false
PROD_MODE=false
RELOAD=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            DEV_MODE=true
            ENABLE_CONSOLE_LOGS="true"
            RELOAD="--reload"
            shift
            ;;
        --prod)
            PROD_MODE=true
            ENABLE_CONSOLE_LOGS="false"
            shift
            ;;
        --console)
            ENABLE_CONSOLE_LOGS="true"
            shift
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Update exports
export LOG_LEVEL
export ENABLE_CONSOLE_LOGS

# Validate log level
case $LOG_LEVEL in
    DEBUG|INFO|WARNING|ERROR|CRITICAL)
        ;;
    *)
        warn "Invalid log level: $LOG_LEVEL. Using INFO."
        LOG_LEVEL="INFO"
        export LOG_LEVEL
        ;;
esac

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

log "Starting QuietStories FastAPI..."
info "Configuration:"
info "  Mode: $([ "$DEV_MODE" = "true" ] && echo "Development" || ([ "$PROD_MODE" = "true" ] && echo "Production" || echo "Standard"))"
info "  Log Level: $LOG_LEVEL"
info "  Console Logs: $ENABLE_CONSOLE_LOGS"
info "  Host: $HOST"
info "  Port: $PORT"
info "  Workers: $WORKERS"
info "  Logs Directory: $PROJECT_ROOT/logs/"

# Check if logging stack is running
if ! curl -s http://localhost:3100/ready > /dev/null 2>&1; then
    warn "Logging stack (Loki) not detected at localhost:3100"
    warn "Start it with: ./scripts/logging.sh start"
    warn "Dashboard: http://localhost:3001 (admin/admin123)"
fi

# Change to project directory
cd "$PROJECT_ROOT"

# Start the application
if [ "$PROD_MODE" = "true" ] && [ "$WORKERS" -gt 1 ]; then
    log "Starting production server with $WORKERS workers..."
    exec uvicorn backend.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --access-log \
        --log-level "$(echo $LOG_LEVEL | tr '[:upper:]' '[:lower:]')"
else
    log "Starting development/single-worker server..."
    exec uvicorn backend.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --access-log \
        --log-level "$(echo $LOG_LEVEL | tr '[:upper:]' '[:lower:]')" \
        $RELOAD
fi
