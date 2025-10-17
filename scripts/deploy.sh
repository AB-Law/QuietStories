#!/usr/bin/env bash

# QuietStories Deployment Script
# Easy one-command deployment for production using Docker Compose

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

usage() {
    cat << EOF
QuietStories Deployment Script

Usage: $0 [OPTIONS]

Options:
    --tag TAG          Docker image tag to use (default: latest)
                       Options: latest, dev, v1.0.0, etc.
    --pull             Pull latest images before starting
    --no-pull          Skip pulling images (use local cache)
    --stop             Stop services without removing containers
    --down             Stop and remove containers
    --restart          Restart services
    --logs             Show logs after starting
    --follow           Follow logs after starting
    --help             Show this help

Examples:
    $0                     # Deploy with latest stable version
    $0 --tag dev           # Deploy with dev version
    $0 --tag v1.0.0        # Deploy specific version
    $0 --pull --logs       # Pull latest and show logs
    $0 --restart           # Restart services
    $0 --down              # Stop and remove containers

Environment Variables:
    QS_TAG                 Docker image tag (default: latest)
    QS_API_URL             API URL for frontend (default: http://localhost:8000)

EOF
}

# Default values
TAG="latest"
PULL=true
ACTION="up"
SHOW_LOGS=false
FOLLOW_LOGS=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --tag)
            TAG="$2"
            shift 2
            ;;
        --pull)
            PULL=true
            shift
            ;;
        --no-pull)
            PULL=false
            shift
            ;;
        --stop)
            ACTION="stop"
            shift
            ;;
        --down)
            ACTION="down"
            shift
            ;;
        --restart)
            ACTION="restart"
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
        --follow)
            FOLLOW_LOGS=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Override tag with environment variable if set
if [ -n "$QS_TAG" ]; then
    TAG="$QS_TAG"
fi

cd "$PROJECT_ROOT"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    error "docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    error "Docker is not running. Please start Docker first."
    exit 1
fi

log "QuietStories Deployment"
info "Configuration:"
info "  Tag: $TAG"
info "  Action: $ACTION"
info "  Pull images: $PULL"

# Create necessary directories
mkdir -p "$PROJECT_ROOT/data" "$PROJECT_ROOT/logs"

# Handle different actions
case $ACTION in
    up)
        # Pull images if requested
        if [ "$PULL" = true ]; then
            log "Pulling Docker images..."
            # Update docker-compose.prod.yml with the tag
            export QS_IMAGE_TAG=$TAG
            docker-compose -f docker-compose.prod.yml pull
        fi

        # Start services
        log "Starting QuietStories services..."
        docker-compose -f docker-compose.prod.yml up -d

        log "Services started successfully!"
        info ""
        info "QuietStories is now running:"
        info "  Frontend:  http://localhost"
        info "  API:       http://localhost:8000"
        info "  API Docs:  http://localhost:8000/docs"
        info "  ChromaDB:  http://localhost:8001"
        info ""
        info "To view logs:"
        info "  docker-compose -f docker-compose.prod.yml logs -f"
        info ""
        info "To stop:"
        info "  $0 --down"

        # Show logs if requested
        if [ "$SHOW_LOGS" = true ]; then
            log "Showing logs..."
            docker-compose -f docker-compose.prod.yml logs
        fi

        # Follow logs if requested
        if [ "$FOLLOW_LOGS" = true ]; then
            log "Following logs (Ctrl+C to exit)..."
            docker-compose -f docker-compose.prod.yml logs -f
        fi
        ;;

    stop)
        log "Stopping QuietStories services..."
        docker-compose -f docker-compose.prod.yml stop
        log "Services stopped."
        ;;

    down)
        warn "Stopping and removing QuietStories containers..."
        docker-compose -f docker-compose.prod.yml down
        log "Services stopped and removed."
        info "Data and logs are preserved in ./data and ./logs directories."
        ;;

    restart)
        log "Restarting QuietStories services..."
        docker-compose -f docker-compose.prod.yml restart
        log "Services restarted successfully!"
        ;;
esac

# Health check
if [ "$ACTION" = "up" ] || [ "$ACTION" = "restart" ]; then
    info ""
    log "Checking service health..."
    sleep 5

    # Check API health
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        log "✓ API is healthy"
    else
        warn "✗ API health check failed (it may still be starting up)"
        info "  Check logs with: docker-compose -f docker-compose.prod.yml logs api"
    fi

    # Check frontend
    if curl -sf http://localhost/ > /dev/null 2>&1; then
        log "✓ Frontend is accessible"
    else
        warn "✗ Frontend health check failed (it may still be starting up)"
        info "  Check logs with: docker-compose -f docker-compose.prod.yml logs web"
    fi
fi

info ""
log "Deployment complete!"
