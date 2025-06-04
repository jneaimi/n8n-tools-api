# N8N Tools API

FastAPI-based microservice for PDF manipulation designed for n8n workflow automation. Provides PDF split/merge/metadata operations via HTTP endpoints with auto-generated OpenAPI documentation.

## 🚀 Features

- **PDF Operations**: Split, merge, and extract metadata from PDF files
- **n8n Integration**: Optimized for n8n HTTP node workflows
- **Docker Ready**: Production-ready containerization
- **Auto Documentation**: OpenAPI/Swagger UI at `/docs`
- **Health Monitoring**: Built-in health checks
- **File Validation**: 50MB upload limit with comprehensive validation
- **Temporary Storage**: Automatic cleanup after processing

## 🏗️ Architecture

- **FastAPI**: Modern, fast web framework for building APIs
- **pypdf**: PDF manipulation library
- **Docker**: Containerized deployment
- **Pydantic**: Data validation and settings management
- **uvicorn**: ASGI server for production

## 📦 Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/jneaimi/n8n-tools-api.git
cd n8n-tools-api

# Build and run with Docker
docker build -t n8n-tools-api:latest .
docker-compose up -d

# Test the API
curl http://localhost:8000/health
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `N8N Tools API` | Application name |
| `VERSION` | `0.1.0` | API version |
| `DEBUG` | `false` | Debug mode |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `MAX_FILE_SIZE` | `52428800` | Max file size (50MB) |
| `TEMP_DIR` | `/tmp/n8n-tools-api` | Temporary directory |
| `LOG_LEVEL` | `INFO` | Logging level |

### Docker Environments

```bash
# Development mode (hot reload)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Production mode (optimized)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 📖 API Documentation

Once running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔗 API Endpoints

### Health & Info
- `GET /` - API information
- `GET /health` - Health check

### PDF Operations
- `GET /api/v1/pdf/` - PDF service status
- `POST /api/v1/pdf/validate` - Validate PDF file
- `POST /api/v1/pdf/info` - Get PDF information
- `POST /api/v1/pdf/metadata` - Extract PDF metadata
- `POST /api/v1/pdf/split/pages` - Split PDF into individual pages
- `POST /api/v1/pdf/split/ranges` - Split PDF by page ranges

## 🐳 Docker Commands

```bash
# Management script
./scripts/docker.sh build    # Build image
./scripts/docker.sh run      # Run container
./scripts/docker.sh dev      # Development mode
./scripts/docker.sh prod     # Production mode
./scripts/docker.sh test     # Run tests
./scripts/docker.sh clean    # Cleanup
./scripts/docker.sh logs     # View logs
./scripts/docker.sh shell    # Open shell
```

## 📁 Project Structure

```
n8n-tools-api/
├── app/                     # Application code
│   ├── api/                 # API routes
│   ├── core/                # Core configuration
│   ├── services/            # Business logic
│   └── utils/               # Utilities
├── docs/                    # Documentation
├── scripts/                 # Management scripts
├── tests/                   # Test files
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose
└── requirements.txt        # Python dependencies
```

## 🧪 Testing

```bash
# Run tests locally
pytest tests/ -v

# Run tests in Docker
./scripts/docker.sh test
```

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For support, please open an issue on GitHub or contact the maintainer.
