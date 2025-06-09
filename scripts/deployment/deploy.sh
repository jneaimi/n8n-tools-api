#!/bin/bash

# Production Deployment Script for N8N Tools API
# This script handles the complete production deployment process

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
IMAGE_NAME="n8n-tools-api"
CONTAINER_NAME="n8n-tools-api"
HEALTH_ENDPOINT="http://localhost:8000/health"
MAX_WAIT_TIME=60

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if required files exist
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if [[ ! -f "$PROJECT_ROOT/Dockerfile" ]]; then
        log_error "Dockerfile not found in project root"
        exit 1
    fi
    
    if [[ ! -f "$PROJECT_ROOT/docker-compose.yml" ]]; then
        log_error "docker-compose.yml not found in project root"
        exit 1
    fi
    
    if [[ ! -f "$PROJECT_ROOT/docker-compose.prod.yml" ]]; then
        log_error "docker-compose.prod.yml not found in project root"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Function to backup current deployment
backup_current_deployment() {
    log_info "Creating backup of current deployment..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="$PROJECT_ROOT/backups/$TIMESTAMP"
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup environment file
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        cp "$PROJECT_ROOT/.env" "$BACKUP_DIR/.env.backup"
    fi
    
    # Export current container if it exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_info "Exporting current container..."
        docker commit "$CONTAINER_NAME" "${IMAGE_NAME}:backup-$TIMESTAMP" || log_warning "Could not create container backup"
    fi
    
    log_success "Backup created in $BACKUP_DIR"
}

# Function to build the Docker image
build_image() {
    log_info "Building Docker image..."
    
    cd "$PROJECT_ROOT"
    
    # Build with build args for optimization
    docker build \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        --tag "${IMAGE_NAME}:latest" \
        --tag "${IMAGE_NAME}:$(date +%Y%m%d)" \
        .
    
    log_success "Docker image built successfully"
}

# Function to stop current deployment
stop_current_deployment() {
    log_info "Stopping current deployment..."
    
    cd "$PROJECT_ROOT"
    
    # Stop containers gracefully
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml down --timeout 30 || log_warning "Could not stop containers gracefully"
    
    log_success "Current deployment stopped"
}

# Function to deploy new version
deploy_new_version() {
    log_info "Deploying new version..."
    
    cd "$PROJECT_ROOT"
    
    # Start new deployment
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
    
    log_success "New version deployed"
}

# Function to wait for service to be healthy
wait_for_health() {
    log_info "Waiting for service to become healthy..."
    
    local count=0
    while [[ $count -lt $MAX_WAIT_TIME ]]; do
        if curl -f "$HEALTH_ENDPOINT" >/dev/null 2>&1; then
            log_success "Service is healthy!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((count+=2))
    done
    
    log_error "Service did not become healthy within $MAX_WAIT_TIME seconds"
    return 1
}

# Function to run post-deployment tests
run_post_deployment_tests() {
    log_info "Running post-deployment tests..."
    
    # Test health endpoint
    if ! curl -f "$HEALTH_ENDPOINT" >/dev/null 2>&1; then
        log_error "Health check failed"
        return 1
    fi
    
    # Test API documentation endpoint
    if ! curl -f "http://localhost:8000/docs" >/dev/null 2>&1; then
        log_warning "API documentation endpoint not accessible"
    fi
    
    # Test OpenAPI schema endpoint
    if ! curl -f "http://localhost:8000/openapi.json" >/dev/null 2>&1; then
        log_warning "OpenAPI schema endpoint not accessible"
    fi
    
    log_success "Post-deployment tests completed"
}

# Function to cleanup old images and containers
cleanup() {
    log_info "Cleaning up old Docker images and containers..."
    
    # Remove dangling images
    docker image prune -f || log_warning "Could not prune dangling images"
    
    # Remove old backups (keep last 5)
    if [[ -d "$PROJECT_ROOT/backups" ]]; then
        cd "$PROJECT_ROOT/backups"
        ls -1t | tail -n +6 | xargs -r rm -rf
    fi
    
    log_success "Cleanup completed"
}

# Function to rollback deployment
rollback() {
    log_error "Deployment failed. Initiating rollback..."
    
    cd "$PROJECT_ROOT"
    
    # Find the latest backup image
    BACKUP_IMAGE=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "${IMAGE_NAME}:backup-" | head -n 1)
    
    if [[ -n "$BACKUP_IMAGE" ]]; then
        log_info "Rolling back to $BACKUP_IMAGE"
        
        # Tag backup as latest
        docker tag "$BACKUP_IMAGE" "${IMAGE_NAME}:latest"
        
        # Restart with backup image
        deploy_new_version
        
        if wait_for_health; then
            log_success "Rollback completed successfully"
        else
            log_error "Rollback failed. Manual intervention required."
            exit 1
        fi
    else
        log_error "No backup image found. Manual intervention required."
        exit 1
    fi
}

# Main deployment function
main() {
    log_info "Starting production deployment of N8N Tools API..."
    
    # Set trap for cleanup on exit
    trap 'log_error "Deployment interrupted"' INT TERM
    
    # Run deployment steps
    check_prerequisites
    backup_current_deployment
    build_image
    stop_current_deployment
    deploy_new_version
    
    # Wait for service and test
    if wait_for_health && run_post_deployment_tests; then
        cleanup
        log_success "Deployment completed successfully!"
        
        echo
        log_info "Service endpoints:"
        echo "  Health: $HEALTH_ENDPOINT"
        echo "  API Docs: http://localhost:8000/docs"
        echo "  OpenAPI: http://localhost:8000/openapi.json"
    else
        rollback
    fi
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "rollback")
        rollback
        ;;
    "health")
        if curl -f "$HEALTH_ENDPOINT" >/dev/null 2>&1; then
            log_success "Service is healthy"
            exit 0
        else
            log_error "Service is not healthy"
            exit 1
        fi
        ;;
    "cleanup")
        cleanup
        ;;
    *)
        echo "Usage: $0 [deploy|rollback|health|cleanup]"
        echo "  deploy  - Deploy the application (default)"
        echo "  rollback - Rollback to previous version"
        echo "  health  - Check service health"
        echo "  cleanup - Clean up old images and containers"
        exit 1
        ;;
esac
