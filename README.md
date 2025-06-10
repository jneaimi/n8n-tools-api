# N8N Tools API

FastAPI-based microservice for PDF manipulation and AI-powered OCR designed for n8n workflow automation. Provides PDF split/merge/metadata operations and Mistral AI OCR processing via HTTP endpoints with auto-generated OpenAPI documentation.

## 🚀 Features

### PDF Operations
- **PDF Manipulation**: Split, merge, and extract metadata from PDF files
- **Batch Processing**: Handle multiple files and complex operations
- **Advanced Splitting**: By page ranges, individual pages, or batch sizes

### AI-Powered OCR (NEW)
- **Mistral AI Integration**: Native OCR using mistral-ocr-latest model
- **Enhanced Image Extraction**: Rich coordinate data and quality assessment
- **Text Recognition**: Multi-language support with high accuracy
- **Format Support**: PDF, PNG, JPEG, TIFF files up to 50MB
- **Native Processing**: Leverages Mistral's built-in capabilities for superior results

### Core Features
- **n8n Integration**: Optimized for n8n HTTP node workflows
- **Docker Ready**: Production-ready containerization
- **Auto Documentation**: OpenAPI/Swagger UI at `/docs`
- **Health Monitoring**: Built-in health checks and metrics
- **File Validation**: Comprehensive validation with error handling
- **Temporary Storage**: Automatic cleanup after processing

## 🏗️ Architecture

### Core Framework
- **FastAPI**: Modern, fast web framework for building APIs
- **pypdf**: PDF manipulation library
- **Docker**: Containerized deployment
- **Pydantic**: Data validation and settings management
- **uvicorn**: ASGI server for production

### AI & OCR Components
- **Mistral AI**: Native OCR processing with mistral-ocr-latest model
- **Enhanced Image Extraction**: Rich coordinate and quality data
- **aiohttp**: Async HTTP client for Mistral AI API integration
- **Comprehensive Error Handling**: Circuit breakers and retry logic

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

### OCR Configuration (Required for OCR endpoints)
| Variable | Default | Description |
|----------|---------|-------------|
| `MISTRAL_API_KEY` | None | Mistral AI API key for OCR processing |
| `OCR_MAX_FILE_SIZE` | `52428800` | Max OCR file size (50MB) |
| `OCR_IMAGE_LIMIT` | `50` | Max images to extract per document |
| `OCR_MIN_IMAGE_SIZE` | `30` | Minimum image size in pixels |

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

### OCR Operations (NEW)
- `GET /api/v1/ocr/` - OCR service status and capabilities
- `GET /api/v1/ocr/health` - Detailed health metrics
- `POST /api/v1/ocr/auth/test` - Test API key authentication
- `POST /api/v1/ocr/validate` - Validate file for OCR processing
- `POST /api/v1/ocr/process-file` - Process uploaded file with AI OCR
- `POST /api/v1/ocr/process-url` - Process document from URL

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
