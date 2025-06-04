#!/bin/bash

# Docker Build and Management Script for N8N Tools API
# Usage: ./scripts/docker.sh [build|run|dev|prod|test|clean]

set -e

PROJECT_NAME="n8n-tools-api"
IMAGE_NAME="$PROJECT_NAME:latest"
CONTAINER_NAME="$PROJECT_NAME"

case "$1" in
    "build")
        echo "Building Docker image..."
        docker build -t $IMAGE_NAME .
        echo "✅ Build complete: $IMAGE_NAME"
        ;;
    
    "run")
        echo "Running container in production mode..."
        docker-compose up -d
        echo "✅ Container started: http://localhost:8000"
        echo "📋 Health check: curl http://localhost:8000/health"
        echo "📖 API docs: http://localhost:8000/docs"
        ;;
    
    "dev")
        echo "Running container in development mode..."
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
        ;;
    
    "prod")
        echo "Running container in production mode..."
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
        ;;
    
    "test")
        echo "Running tests in container..."
        docker run --rm -v $(pwd)/tests:/app/tests $IMAGE_NAME pytest tests/ -v
        ;;
    
    "clean")
        echo "Cleaning up containers and images..."
        docker-compose down --volumes --remove-orphans
        docker rmi $IMAGE_NAME 2>/dev/null || true
        echo "✅ Cleanup complete"
        ;;
    
    "logs")
        echo "Showing container logs..."
        docker-compose logs -f
        ;;
    
    "shell")
        echo "Opening shell in running container..."
        docker exec -it $CONTAINER_NAME /bin/bash
        ;;
    
    *)
        echo "Usage: $0 {build|run|dev|prod|test|clean|logs|shell}"
        echo ""
        echo "Commands:"
        echo "  build  - Build the Docker image"
        echo "  run    - Run container with default configuration"
        echo "  dev    - Run in development mode (with hot reload)"
        echo "  prod   - Run in production mode"
        echo "  test   - Run tests in container"
        echo "  clean  - Stop containers and remove images"
        echo "  logs   - Show container logs"
        echo "  shell  - Open shell in running container"
        exit 1
        ;;
esac
