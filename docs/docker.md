# Docker Deployment Guide

## Quick Start

### 1. Build and Run
```bash
# Build the Docker image
./scripts/docker.sh build

# Run in production mode
./scripts/docker.sh run

# Or run in development mode (with hot reload)
./scripts/docker.sh dev
```

### 2. Access the API
- **API Base URL**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Docker Commands

### Build & Run
```bash
# Build image
docker build -t n8n-tools-api:latest .

# Run with docker-compose (recommended)
docker-compose up -d

# Run single container
docker run -d -p 8000:8000 --name n8n-tools-api n8n-tools-api:latest
```

### Environment Configurations

#### Development Mode
```bash
# Hot reload enabled, debug logging
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

#### Production Mode
```bash
# Optimized for production, restricted CORS
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```
