"""
FastAPI application main entry point.

This module initializes the FastAPI application with proper configuration
for n8n workflow automation integration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import uvicorn

from app.api.routes import pdf, ocr, rag
from app.core.config import settings
from app.core.errors import setup_exception_handlers
from app.core.logging import RequestLoggingMiddleware, setup_logging, app_logger
from app.core.openapi_enhancements import (
    get_enhanced_openapi_examples, 
    get_enhanced_openapi_schemas,
    get_enhanced_security_schemes
)
from app.core.rag_openapi_enhancements import (
    get_rag_openapi_examples,
    get_rag_openapi_schemas,
    get_rag_n8n_integration_examples
)
# AI PDF operations disabled - removed ai_pdf_ops import

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="N8N Tools API",
        description="""
## PDF Manipulation, AI-Powered OCR & RAG Operations Service for n8n Workflow Automation

A FastAPI-based microservice specifically designed for **n8n workflow automation**. 
This service provides comprehensive PDF manipulation capabilities, AI-powered OCR 
processing using Mistral AI, and RAG (Retrieval-Augmented Generation) operations 
with Qdrant vector database integration.

### 🚀 Key Features
- **Split PDFs** by page ranges, individual pages, or batches
- **Merge multiple PDFs** with various strategies and page selection
- **Extract metadata** from PDF documents
- **AI-Powered OCR** using Mistral AI for text and image extraction
- **RAG Operations** with Qdrant collection management for vector embeddings
- **Vector Database Integration** optimized for Mistral embeddings (1024 dimensions)
- **URL Processing** for remote document OCR
- **n8n Compatible** with auto-generated OpenAPI schema
- **File validation** with comprehensive error handling
- **Streaming responses** for large file operations

### 📋 File Requirements
- **PDF Operations**: PDF files only, 50MB max per file
- **OCR Operations**: PDF, PNG, JPG, JPEG, TIFF files, 50MB max
- **RAG Operations**: API key authentication required
- **Merge Limit**: Maximum 20 files for merge operations
- **Authentication**: API key required for OCR and RAG operations

### 🔧 n8n Integration
This API is optimized for n8n HTTP nodes with:
- Detailed endpoint descriptions and examples
- Proper HTTP status codes and error responses
- Streaming file downloads with informative headers
- JSON responses for validation and information endpoints
- RAG workflow examples for vector database operations

### 📚 Available Operations
- **Validation**: Validate PDF files before processing
- **Information**: Get detailed PDF file information
- **Splitting**: Multiple splitting modes (ranges, pages, batches)
- **Merging**: Various merge strategies with page selection
- **Metadata**: Comprehensive PDF metadata extraction
- **OCR Processing**: AI-powered text and image extraction
- **URL OCR**: Process remote documents via URL
- **RAG Collection Management**: Create and manage Qdrant collections
- **Vector Database Operations**: Optimized for Mistral embeddings
- **Connection Testing**: Validate Qdrant and Mistral connectivity

Use the interactive documentation below to explore all available endpoints.
        """.strip(),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "N8N Tools API Support",
            "url": "https://github.com/your-repo/n8n-tools",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        servers=[
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            },
            {
                "url": "https://your-production-domain.com",
                "description": "Production server"
            }
        ]
    )
    
    # Configure CORS for n8n integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify actual n8n domains
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware, logger=app_logger)
    
    # Custom OpenAPI schema for n8n compatibility
    def custom_openapi():
        """Generate custom OpenAPI schema optimized for n8n integration."""
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        
        # Add enhanced OCR and RAG documentation
        enhanced_examples = get_enhanced_openapi_examples()
        enhanced_schemas = get_enhanced_openapi_schemas()
        security_schemes = get_enhanced_security_schemes()
        
        # Add RAG-specific enhancements
        rag_examples = get_rag_openapi_examples()
        rag_schemas = get_rag_openapi_schemas()
        rag_n8n_examples = get_rag_n8n_integration_examples()
        
        # Add enhanced schemas to components
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}
        if "schemas" not in openapi_schema["components"]:
            openapi_schema["components"]["schemas"] = {}
        if "securitySchemes" not in openapi_schema["components"]:
            openapi_schema["components"]["securitySchemes"] = {}
            
        # Merge enhanced schemas (OCR + RAG)
        openapi_schema["components"]["schemas"].update(enhanced_schemas)
        openapi_schema["components"]["schemas"].update(rag_schemas)
        openapi_schema["components"]["securitySchemes"].update(security_schemes)
        
        # Add n8n-specific customizations
        openapi_schema["info"]["x-logo"] = {
            "url": "https://docs.n8n.io/assets/n8n-logo.png",
            "altText": "n8n Compatible API"
        }
        
        # Add API feature information (OCR + RAG)
        openapi_schema["info"]["x-api-features"] = {
            "ocr_processing": "AI-powered OCR using Mistral AI",
            "rag_operations": "Qdrant collection management for RAG workflows",
            "file_processing": "Support for PDF and image files up to 50MB",
            "url_processing": "Remote document processing via URLs",
            "vector_databases": "Qdrant integration with optimized configurations",
            "embedding_models": "Mistral AI embedding support with 1024 dimensions",
            "n8n_optimized": "Designed for n8n workflow automation",
            "error_handling": "Comprehensive error system with detailed error codes",
            "rate_limiting": "60 requests/minute, 1000 requests/hour",
            "authentication": "API key-based authentication with secure validation"
        }
        
        # Enhance OCR endpoint documentation
        for path in openapi_schema.get("paths", {}):
            for method in openapi_schema["paths"][path]:
                endpoint_info = openapi_schema["paths"][path][method]
                
                # Enhance OCR endpoints with comprehensive examples
                if "/ocr/" in path:
                    # Add security requirements for OCR endpoints (except status endpoints)
                    if path not in ["/api/v1/ocr/", "/api/v1/ocr/health"]:
                        endpoint_info["security"] = [
                            {"ApiKeyAuth": []},
                            {"BearerAuth": []}
                        ]
                    
                    # Add comprehensive examples for OCR endpoints
                    if "process-file" in path and method.lower() == "post":
                        if "requestBody" in endpoint_info:
                            form_content = endpoint_info["requestBody"]["content"]["multipart/form-data"]
                            form_content["examples"] = enhanced_examples["ocr_file_processing_examples"]
                        
                        # Enhance responses with detailed examples
                        if "responses" in endpoint_info:
                            if "200" in endpoint_info["responses"]:
                                response_200 = endpoint_info["responses"]["200"]
                                response_content = response_200.get("content", {})
                                if "application/json" in response_content:
                                    response_content["application/json"]["examples"] = {
                                        "successful_processing": enhanced_examples["response_examples"]["successful_pdf_processing"]
                                    }
                            
                            # Add error response examples
                            for error_code in ["400", "401", "413", "422", "429", "500"]:
                                if error_code in endpoint_info["responses"]:
                                    error_response = endpoint_info["responses"][error_code]
                                    error_content = error_response.get("content", {})
                                    if "application/json" in error_content:
                                        error_examples = {}
                                        if error_code == "401":
                                            error_examples["authentication_error"] = enhanced_examples["error_examples"]["authentication_error"]
                                        elif error_code == "413":
                                            error_examples["file_too_large"] = enhanced_examples["error_examples"]["file_too_large_error"]
                                        elif error_code == "422":
                                            error_examples["invalid_format"] = enhanced_examples["error_examples"]["invalid_file_format_error"]
                                        elif error_code == "429":
                                            error_examples["rate_limit"] = enhanced_examples["error_examples"]["rate_limit_error"]
                                        elif error_code == "500":
                                            error_examples["processing_timeout"] = enhanced_examples["error_examples"]["processing_timeout_error"]
                                        
                                        if error_examples:
                                            error_content["application/json"]["examples"] = error_examples
                    
                    elif "process-url" in path and method.lower() == "post":
                        if "requestBody" in endpoint_info:
                            request_content = endpoint_info["requestBody"]["content"]
                            if "application/json" in request_content:
                                json_content = request_content["application/json"]
                                json_content["examples"] = enhanced_examples["ocr_url_processing_examples"]
                        
                        # Add URL-specific response examples
                        if "responses" in endpoint_info and "200" in endpoint_info["responses"]:
                            response_200 = endpoint_info["responses"]["200"]
                            response_content = response_200.get("content", {})
                            if "application/json" in response_content:
                                response_content["application/json"]["examples"] = {
                                    "url_processing": enhanced_examples["response_examples"]["url_processing_response"]
                                }
                    
                    elif "health" in path and method.lower() == "get":
                        if "responses" in endpoint_info and "200" in endpoint_info["responses"]:
                            response_200 = endpoint_info["responses"]["200"]
                            response_content = response_200.get("content", {})
                            if "application/json" in response_content:
                                response_content["application/json"]["examples"] = enhanced_examples["health_response_examples"]
                
                # Add n8n-specific examples for PDF endpoints (existing functionality)
                
                # Enhance RAG endpoints with comprehensive examples
                if "/rag-operations/" in path:
                    # Add authentication for RAG endpoints (except status endpoints)
                    if path not in ["/api/v1/rag-operations/", "/api/v1/rag-operations/health"]:
                        endpoint_info["security"] = [
                            {"ApiKeyAuth": []},
                            {"BearerAuth": []}
                        ]
                    
                    # Add comprehensive examples for RAG endpoints
                    if "create-collection" in path and method.lower() == "post":
                        if "requestBody" in endpoint_info:
                            request_content = endpoint_info["requestBody"]["content"]
                            if "application/json" in request_content:
                                json_content = request_content["application/json"]
                                json_content["examples"] = rag_examples["rag_collection_creation_examples"]
                        
                        # Add RAG-specific response examples
                        if "responses" in endpoint_info:
                            if "201" in endpoint_info["responses"]:
                                response_201 = endpoint_info["responses"]["201"]
                                response_content = response_201.get("content", {})
                                if "application/json" in response_content:
                                    response_content["application/json"]["examples"] = {
                                        "successful_creation": rag_examples["rag_response_examples"]["successful_collection_creation"]
                                    }
                    
                    elif "test-connection" in path and method.lower() == "post":
                        if "requestBody" in endpoint_info:
                            request_content = endpoint_info["requestBody"]["content"]
                            if "application/json" in request_content:
                                json_content = request_content["application/json"]
                                json_content["examples"] = rag_examples["rag_connection_testing_examples"]
                        
                        # Add connection test response examples
                        if "responses" in endpoint_info and "200" in endpoint_info["responses"]:
                            response_200 = endpoint_info["responses"]["200"]
                            response_content = response_200.get("content", {})
                            if "application/json" in response_content:
                                response_content["application/json"]["examples"] = {
                                    "successful_connection": rag_examples["rag_response_examples"]["successful_connection_test"]
                                }
                    
                    elif path.endswith("/health") and method.lower() == "get":
                        if "responses" in endpoint_info and "200" in endpoint_info["responses"]:
                            response_200 = endpoint_info["responses"]["200"]
                            response_content = response_200.get("content", {})
                            if "application/json" in response_content:
                                response_content["application/json"]["examples"] = {
                                    "healthy_service": {
                                        "summary": "Healthy RAG service",
                                        "value": rag_schemas["RAGHealthStatus"]["example"]
                                    }
                                }
                    
                    elif path.endswith("/") and method.lower() == "get":
                        if "responses" in endpoint_info and "200" in endpoint_info["responses"]:
                            response_200 = endpoint_info["responses"]["200"]
                            response_content = response_200.get("content", {})
                            if "application/json" in response_content:
                                response_content["application/json"]["examples"] = {
                                    "service_status": {
                                        "summary": "RAG service status",
                                        "value": rag_schemas["RAGServiceStatus"]["example"]
                                    }
                                }
                elif "pdf/" in path and method.lower() == "post":
                    if (method.lower() == "post" and 
                        "requestBody" in endpoint_info and
                        "multipart/form-data" in endpoint_info.get("requestBody", {}).get("content", {})):
                        
                        # Add comprehensive examples for n8n HTTP nodes
                        form_content = endpoint_info["requestBody"]["content"]["multipart/form-data"]
                        
                        if "pdf/split" in path:
                            form_content["examples"] = {
                                "split_by_ranges": {
                                    "summary": "Split PDF by page ranges",
                                    "description": "Example for n8n: Split a PDF into specific page ranges",
                                    "value": {
                                        "file": "(Upload your PDF file here)",
                                        "ranges": "1-3,5,7-9"
                                    }
                                },
                                "split_into_batches": {
                                    "summary": "Split PDF into batches",
                                    "description": "Example for n8n: Split a PDF into batches of equal page count",
                                    "value": {
                                        "file": "(Upload your PDF file here)",
                                        "batch_size": 4,
                                        "output_prefix": "batch_doc"
                                    }
                                }
                            }
                        
                        elif "pdf/merge" in path:
                            form_content["examples"] = {
                                "simple_merge": {
                                    "summary": "Simple PDF merge",
                                    "description": "Example for n8n: Merge multiple PDFs in order",
                                    "value": {
                                        "files": ["(Upload PDF files here)"],
                                        "merge_strategy": "append",
                                        "preserve_metadata": True,
                                        "output_filename": "merged_document.pdf"
                                    }
                                },
                                "merge_with_ranges": {
                                    "summary": "Merge with page ranges",
                                    "description": "Example for n8n: Merge specific page ranges from multiple PDFs",
                                    "value": {
                                        "files": ["(Upload PDF files here)"],
                                        "range_selections": "[['1-3', '5'], ['2-4'], ['1', '6-8']]"
                                    }
                                }
                            }
        
        # Add custom response headers documentation
        for path in openapi_schema.get("paths", {}):
            for method in openapi_schema["paths"][path]:
                endpoint_info = openapi_schema["paths"][path][method]
                
                # Add header documentation for file download endpoints
                if "responses" in endpoint_info:
                    for status_code in endpoint_info["responses"]:
                        response = endpoint_info["responses"][status_code]
                        
                        # Add header documentation for streaming responses
                        if (response.get("content") and 
                            ("application/zip" in response["content"] or 
                             "application/pdf" in response["content"])):
                            
                            response["headers"] = {
                                "Content-Disposition": {
                                    "description": "Attachment filename for download",
                                    "schema": {"type": "string"},
                                    "example": "attachment; filename=document.pdf"
                                },
                                "X-Processing-Time-Ms": {
                                    "description": "Processing time in milliseconds",
                                    "schema": {"type": "string"},
                                    "example": "1234.56"
                                },
                                "X-File-Count": {
                                    "description": "Number of files in ZIP (for split operations)",
                                    "schema": {"type": "string"},
                                    "example": "5"
                                },
                                "X-Total-Pages": {
                                    "description": "Total number of pages processed",
                                    "schema": {"type": "string"},
                                    "example": "25"
                                },
                                "X-File-Size-MB": {
                                    "description": "File size in megabytes",
                                    "schema": {"type": "string"},
                                    "example": "12.34"
                                }
                            }
        
        # Add comprehensive tags for better organization in n8n
        openapi_schema["tags"] = [
            {
                "name": "Health",
                "description": "Health check and service status endpoints",
                "externalDocs": {
                    "description": "Health monitoring guide",
                    "url": "/docs/health-monitoring"
                }
            },
            {
                "name": "PDF Operations", 
                "description": "Core PDF manipulation operations for n8n workflows",
                "externalDocs": {
                    "description": "PDF processing guide",
                    "url": "/docs/pdf-operations"
                }
            },
            {
                "name": "OCR Operations",
                "description": "AI-powered OCR processing using Mistral AI with comprehensive error handling and n8n optimization",
                "externalDocs": {
                    "description": "OCR API specification",
                    "url": "/docs/api/ocr-api-specification.md"
                }
            },
            {
                "name": "RAG Operations",
                "description": "RAG (Retrieval-Augmented Generation) operations including Qdrant collection management and Mistral embeddings for n8n workflows",
                "externalDocs": {
                    "description": "RAG operations guide",
                    "url": "/docs/rag-operations"
                }
            },
            {
                "name": "Root",
                "description": "API information and navigation endpoints"
            }
        ]
        
        # Add n8n-specific extensions
        openapi_schema["x-n8n-integration"] = {
            "version": "1.0.0",
            "compatibility": "n8n v1.0+",
            "recommended_nodes": ["HTTP Request", "Code", "If", "Set"],
            "workflow_examples": "/n8n",
            "authentication_guide": "/docs/api/ocr-api-specification.md#authentication",
            "error_handling_guide": "/docs/api/ocr-api-specification.md#error-handling"
        }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    # Override the default OpenAPI function
    app.openapi = custom_openapi
    
    # Startup event for AI PDF operations validation
    @app.on_event("startup")
    async def startup_event():
        """Validate AI PDF operations configuration on startup."""
        
        try:
            app_logger.info("N8N Tools API starting up", extra={
                "extra_fields": {
                    "type": "startup",
                    "version": "1.0.0",
                    "debug_mode": settings.DEBUG,
                    "log_level": settings.LOG_LEVEL
                }
            })
            
            # AI PDF operations temporarily disabled
            app_logger.info("AI PDF operations are disabled")
                
        except Exception as e:
            app_logger.error(f"Error during AI PDF operations startup validation: {str(e)}", exc_info=True)
    
    
    # Include routers
    app.include_router(pdf.router, prefix="/api/v1/pdf", tags=["PDF Operations"])
    app.include_router(ocr.router, prefix="/api/v1/ocr", tags=["OCR Operations"])
    app.include_router(rag.router, prefix="/api/v1/rag-operations")
    
    # Dedicated OpenAPI schema endpoint for n8n integration
    @app.get("/openapi.json", include_in_schema=False, tags=["API Schema"])
    async def get_openapi_schema():
        """
        Get OpenAPI schema specifically for n8n HTTP node integration.
        
        This endpoint provides the complete OpenAPI specification that n8n
        can use to automatically understand the API structure and parameters.
        """
        return app.openapi()
    
    # Enhanced n8n information endpoint
    @app.get("/n8n", tags=["n8n Integration"])
    async def n8n_integration_info():
        """
        Get n8n integration information and quick start guide.
        
        Provides specific information for integrating this API with n8n workflows,
        including endpoint recommendations and usage examples.
        """
        return JSONResponse(
            content={
                "service": "N8N Tools API",
                "version": "1.0.0",
                "n8n_integration": {
                    "openapi_url": "/openapi.json",
                    "documentation": "/docs",
                    "base_url": "{{your-api-domain}}",
                    "authentication": "none"
                },
                "recommended_endpoints": {
                    "pdf_validation": {
                        "url": "/api/v1/pdf/validate",
                        "method": "POST",
                        "description": "Validate PDF before processing",
                        "use_case": "Pre-validation in n8n workflows"
                    },
                    "pdf_split_ranges": {
                        "url": "/api/v1/pdf/split/ranges", 
                        "method": "POST",
                        "description": "Split PDF by page ranges",
                        "use_case": "Extract specific sections from documents"
                    },
                    "pdf_merge": {
                        "url": "/api/v1/pdf/merge",
                        "method": "POST", 
                        "description": "Merge multiple PDFs",
                        "use_case": "Combine multiple documents into one"
                    },
                    "pdf_metadata": {
                        "url": "/api/v1/pdf/metadata",
                        "method": "POST",
                        "description": "Extract PDF metadata",
                        "use_case": "Get document information for workflow decisions"
                    },
                    "ocr_process_file": {
                        "url": "/api/v1/ocr/process-file",
                        "method": "POST",
                        "description": "AI-powered OCR processing",
                        "use_case": "Extract text from images and PDFs using Mistral AI"
                    },
                    "rag_test_connection": {
                        "url": "/api/v1/rag-operations/test-connection",
                        "method": "POST",
                        "description": "Test Qdrant and Mistral connectivity",
                        "use_case": "Validate credentials before RAG operations"
                    },
                    "rag_create_collection": {
                        "url": "/api/v1/rag-operations/create-collection",
                        "method": "POST",
                        "description": "Create Qdrant collection for embeddings",
                        "use_case": "Set up vector database for RAG workflows"
                    }
                },
                "n8n_setup_tips": [
                    "Use HTTP Request node with 'Multipart/Form-Data' for file uploads",
                    "Set response format to 'File' for PDF/ZIP downloads",
                    "Use 'JSON' response format for validation and info endpoints", 
                    "Check response headers for processing information",
                    "Implement error handling for 400/500 status codes"
                ],
                "example_workflow": {
                    "description": "Basic PDF processing workflow",
                    "steps": [
                        "1. Upload PDF using 'Manual Trigger' or 'Google Drive' node",
                        "2. Validate PDF using '/api/v1/pdf/validate' endpoint",
                        "3. Process PDF using desired operation (split/merge/metadata)",
                        "4. Save result using 'Google Drive' or 'Email' node",
                        "5. Add error handling with 'If' node for failed operations"
                    ]
                }
            }
        )
    
    # Enhanced health check endpoint
    @app.get("/health", 
             tags=["Health"],
             summary="Health Check",
             description="Check service health and operational status")
    async def health_check():
        """
        Health check endpoint for monitoring and n8n workflow validation.
        
        Returns service status, version information, and operational metrics.
        Use this endpoint to verify the service is running before processing files.
        """
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "service": "n8n-tools-api",
                "version": "1.0.0",
                "timestamp": "2025-06-09T00:00:00Z",
                "capabilities": {
                    "pdf_operations": True,
                    "file_validation": True,
                    "batch_processing": True,
                    "metadata_extraction": True,
                    "ai_ocr": True,
                    "url_processing": True,
                    "rag_operations": True,
                    "qdrant_integration": True,
                    "mistral_embeddings": True
                },
                "limits": {
                    "max_file_size_mb": 50,
                    "max_merge_files": 20,
                    "supported_formats": ["pdf"],
                    "ocr_formats": ["pdf", "png", "jpg", "jpeg", "tiff"],
                    "ocr_auth_required": True
                },
                "endpoints": {
                    "documentation": "/docs",
                    "openapi": "/openapi.json",
                    "n8n_info": "/n8n",
                    "ocr_service": "/api/v1/ocr/",
                    "rag_operations": "/api/v1/rag-operations/"
                }
            }
        )
    
    @app.get("/", 
             tags=["Root"],
             summary="API Information",
             description="Get API overview and navigation links")
    async def root():
        """
        Root endpoint with comprehensive API information for n8n integration.
        
        Provides quick access to documentation, health status, and key endpoints
        for easy discovery in n8n workflow development.
        """
        return JSONResponse(
            content={
                "message": "N8N Tools API - PDF Manipulation Service",
                "version": "1.0.0",
                "description": "FastAPI microservice for PDF operations in n8n workflows",
                "documentation": {
                    "interactive_docs": "/docs",
                    "redoc": "/redoc", 
                    "openapi_schema": "/openapi.json",
                    "n8n_integration": "/n8n"
                },
                "endpoints": {
                    "health": "/health",
                    "pdf_operations": "/api/v1/pdf/",
                    "ocr_operations": "/api/v1/ocr/",
                    "rag_operations": "/api/v1/rag-operations/",
                    "validation": "/api/v1/pdf/validate",
                    "metadata": "/api/v1/pdf/metadata"
                },
                "quick_start": {
                    "1": "Check service health at /health",
                    "2": "Validate PDF files at /api/v1/pdf/validate", 
                    "3": "Process PDFs using /api/v1/pdf/* endpoints",
                    "4": "Use OCR at /api/v1/ocr/* endpoints (requires API key)",
                    "5": "View full documentation at /docs"
                },
                "support": {
                    "documentation": "/docs",
                    "n8n_examples": "/n8n",
                    "status": "healthy"
                }
            }
        )
    
    return app

# Create the FastAPI app instance
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
