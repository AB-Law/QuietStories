#!/usr/bin/env bash

# QuietStories Logging Stack Management Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.logging.yml"
LOG_RETENTION_DAYS=${LOG_RETENTION_DAYS:-7}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Function to update log retention configuration
update_retention() {
    local days=$1
    local hours=$((days * 24))

    log "Updating log retention to $days days ($hours hours)"

    # Update Loki configuration
    sed -i.bak "s/retention_period: [0-9]*h/retention_period: ${hours}h/g" "$PROJECT_ROOT/logging/loki-config.yml"

    log "Updated Loki retention configuration"
}

# Function to start the logging stack
start() {
    log "Starting QuietStories Logging Stack..."

    # Create logs directory if it doesn't exist
    mkdir -p "$PROJECT_ROOT/logs"

    # Start the services
    docker-compose -f "$COMPOSE_FILE" up -d

    # Wait for services to be healthy
    log "Waiting for services to start..."
    sleep 10

    # Check service status
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        log "Logging stack started successfully!"
        info "Grafana: http://localhost:3001 (admin/admin123)"
        info "Loki API: http://localhost:3100"
        info "Log retention: $LOG_RETENTION_DAYS days"
    else
        error "Failed to start logging stack"
        docker-compose -f "$COMPOSE_FILE" logs
        exit 1
    fi
}

# Function to stop the logging stack
stop() {
    log "Stopping QuietStories Logging Stack..."
    docker-compose -f "$COMPOSE_FILE" down
    log "Logging stack stopped"
}

# Function to restart the logging stack
restart() {
    log "Restarting QuietStories Logging Stack..."
    stop
    start
}

# Function to show logs
logs() {
    local service=${1:-}
    if [ -n "$service" ]; then
        docker-compose -f "$COMPOSE_FILE" logs -f "$service"
    else
        docker-compose -f "$COMPOSE_FILE" logs -f
    fi
}

# Function to show status
status() {
    info "QuietStories Logging Stack Status:"
    docker-compose -f "$COMPOSE_FILE" ps

    info "\nService URLs:"
    echo "  Grafana:   http://localhost:3001 (admin/admin123)"
    echo "  Loki API:  http://localhost:3100"

    info "\nLog files location:"
    echo "  Local logs: $PROJECT_ROOT/logs/"

    info "\nRetention settings:"
    echo "  Days: $LOG_RETENTION_DAYS"
    echo "  Hours: $((LOG_RETENTION_DAYS * 24))"
}

# Function to clean up old logs
cleanup() {
    log "Cleaning up old log files..."

    # Clean up local log files older than retention period
    find "$PROJECT_ROOT/logs" -name "*.log" -type f -mtime +$LOG_RETENTION_DAYS -delete 2>/dev/null || true

    log "Cleanup completed"
}

# Function to show help
help() {
    cat << EOF
QuietStories Logging Stack Management

Usage: $0 <command> [options]

Commands:
    start                Start the logging stack
    stop                 Stop the logging stack
    restart              Restart the logging stack
    status               Show status of all services
    logs [service]       Show logs (optionally for specific service)
    cleanup              Clean up old log files
    retention <days>     Update log retention period (1-30 days)
    help                 Show this help message

Examples:
    $0 start                    # Start the logging stack
    $0 logs loki               # Show Loki logs
    $0 retention 3             # Set retention to 3 days
    $0 status                  # Show service status

Environment Variables:
    LOG_RETENTION_DAYS         Log retention period (default: 7)

EOF
}

# Main command handling
case "${1:-help}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs "$2"
        ;;
    cleanup)
        cleanup
        ;;
    retention)
        if [ -z "$2" ]; then
            error "Please specify retention period in days (1-30)"
            exit 1
        fi
        if [ "$2" -lt 1 ] || [ "$2" -gt 30 ]; then
            error "Retention period must be between 1 and 30 days"
            exit 1
        fi
        update_retention "$2"
        warn "Restart the logging stack to apply retention changes"
        ;;
    help|--help|-h)
        help
        ;;
    *)
        error "Unknown command: $1"
        help
        exit 1
        ;;
esac
