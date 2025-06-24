# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **n8n-tools-api** - a FastAPI-based microservice designed for n8n workflow automation. It provides three main API services:
1. **PDF Operations**: Split, merge, extract metadata, validate PDFs
2. **AI-Powered OCR**: Uses Mistral AI's OCR model for text/image extraction
3. **RAG Operations**: Vector database operations with custom Qdrant HTTP client

## Common Development Commands

### Running the Application
```bash
# Development mode with hot reload
./scripts/docker.sh dev
# OR
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Production mode
./scripts/docker.sh prod

# Direct Python (requires environment setup)
uvicorn app.main:app --reload
```

### Testing
```bash
# Run all tests with coverage
python run_tests.py all

# Quick tests during development
python run_tests.py quick

# Specific test suites
python run_tests.py unit
python run_tests.py integration

# Run tests in Docker
./scripts/docker.sh test
```

### Code Quality
```bash
# Format code
python run_tests.py format
# OR
black .

# Run all linting checks
python run_tests.py lint
# OR individually:
flake8 app tests
mypy app --ignore-missing-imports
bandit -r app/
```

### Building and Deployment
```bash
# Build Docker image
./scripts/docker.sh build

# Deploy to production
./scripts/deployment/deploy.sh

# Check health
./scripts/deployment/deploy.sh health
```

## Code Architecture

### Directory Structure
- `app/api/routes/` - API endpoint definitions (ocr.py, pdf.py, rag.py)
- `app/services/` - Business logic (mistral_service.py, pdf_service.py, qdrant_http_service.py)
- `app/models/` - Pydantic models for request/response validation
- `app/core/` - Core functionality (config, auth, errors, logging)
- `app/utils/` - Utilities (s3_client.py, ocr_utils.py)

### Key Design Patterns
1. **Service Layer Pattern**: All business logic in services/, routes only handle HTTP
2. **Dependency Injection**: FastAPI's dependency system for auth, services
3. **Async/Await**: All API operations are async for performance
4. **Error Handling**: Centralized error handling with custom exceptions in core/errors.py
5. **Configuration**: Environment-based config in core/config.py using Pydantic Settings

### API Authentication
- OCR and RAG endpoints require API key authentication
- PDF endpoints are public (no auth required)
- Auth implemented via dependency injection in `app/core/auth.py`

### Testing Strategy
- Unit tests mock external services (Mistral, S3, Qdrant)
- Integration tests use real services when available
- Test fixtures in `tests/conftest.py`
- Performance tests with Locust for load testing

## Important Technical Details

### External Service Integration
1. **Mistral AI**: Uses aiohttp for async requests, implements official OCR API format
2. **S3/MinIO**: boto3 client with connection pooling, handles image uploads from OCR
3. **Qdrant**: Custom HTTP client due to connectivity issues with official SDK

### File Processing Limits
- Maximum file size: 50MB (configurable via MAX_FILE_SIZE env var)
- PDF processing: Memory-efficient streaming for large files
- OCR: Processes images in batches to avoid memory issues

### Error Handling Philosophy
- Always return meaningful error messages to help n8n workflow debugging
- Log detailed errors internally but sanitize for external responses
- Use HTTP status codes correctly (400 for client errors, 500 for server errors)

### Recent Important Changes
- Migrated from PyMuPDF to pypdf for PDF operations (licensing compatibility)
- Implemented official Mistral OCR API format compliance
- Added S3 integration for OCR extracted images
- Fixed critical KeyError in OCR S3 metrics when no images detected

## Environment Variables

Critical environment variables:
- `MISTRAL_API_KEY` - Required for OCR endpoints
- `MINIO_*` - S3 storage configuration (optional, for OCR image storage)
- `QDRANT_*` - Vector database settings (required for RAG endpoints)
- `API_KEY` - Authentication key for protected endpoints
- `DEBUG` - Enable debug mode (default: false)
- `LOG_LEVEL` - Logging verbosity (default: INFO)

## When Making Changes

1. **Adding New Endpoints**: Follow existing patterns in app/api/routes/
2. **Modifying Services**: Ensure proper error handling and async patterns
3. **Testing**: Always add tests for new functionality
4. **Documentation**: Update OpenAPI descriptions in route decorators
5. **Error Messages**: Make them helpful for n8n workflow debugging

## Monitoring and Debugging

- Health check: GET /health
- API Documentation: /docs (Swagger UI), /redoc (ReDoc)
- n8n Integration Guide: /n8n
- Logs: Structured JSON logging when not in debug mode
- Metrics: Prometheus-compatible metrics (when monitoring stack deployed)