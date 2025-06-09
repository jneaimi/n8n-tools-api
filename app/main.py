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

from app.api.routes import pdf
from app.core.config import settings
from app.core.errors import setup_exception_handlers
from app.core.logging import RequestLoggingMiddleware, setup_logging, app_logger
from app.ai_pdf_ops.config import ai_pdf_config

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="N8N Tools API",
        description="""
## PDF Manipulation Service for n8n Workflow Automation

A FastAPI-based microservice specifically designed for **n8n workflow automation**. 
This service provides comprehensive PDF manipulation capabilities including splitting, 
merging, and metadata extraction operations.

### 🚀 Key Features
- **Split PDFs** by page ranges, individual pages, or batches
- **Merge multiple PDFs** with various strategies and page selection
- **Extract metadata** from PDF documents
- **n8n Compatible** with auto-generated OpenAPI schema
- **File validation** with comprehensive error handling
- **Streaming responses** for large file operations

### 📋 File Requirements
- **Format**: PDF files only
- **Size Limit**: 50MB per file
- **Merge Limit**: Maximum 20 files for merge operations

### 🔧 n8n Integration
This API is optimized for n8n HTTP nodes with:
- Detailed endpoint descriptions and examples
- Proper HTTP status codes and error responses
- Streaming file downloads with informative headers
- JSON responses for validation and information endpoints

### 📚 Available Operations
- **Validation**: Validate PDF files before processing
- **Information**: Get detailed PDF file information
- **Splitting**: Multiple splitting modes (ranges, pages, batches)
- **Merging**: Various merge strategies with page selection
- **Metadata**: Comprehensive PDF metadata extraction

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
        
        # Add n8n-specific customizations
        openapi_schema["info"]["x-logo"] = {
            "url": "https://docs.n8n.io/assets/n8n-logo.png",
            "altText": "n8n Compatible API"
        }
        
        # Enhance endpoint descriptions with n8n examples
        for path in openapi_schema.get("paths", {}):
            for method in openapi_schema["paths"][path]:
                endpoint_info = openapi_schema["paths"][path][method]
                
                # Add n8n-specific examples for multipart form endpoints
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
        
        # Add global tags for better organization in n8n
        openapi_schema["tags"] = [
            {
                "name": "Health",
                "description": "Health check and service status endpoints"
            },
            {
                "name": "PDF Operations", 
                "description": "Core PDF manipulation operations for n8n workflows"
            },
            {
                "name": "Root",
                "description": "API information and navigation endpoints"
            }
        ]
        
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
            
            # Validate that Mistral API key is configured if AI features are enabled
            if (ai_pdf_config.ocr_enabled or 
                ai_pdf_config.vision_enabled or 
                ai_pdf_config.embeddings_enabled):
                
                if not ai_pdf_config.mistral_api_key:
                    app_logger.warning("AI PDF operations are enabled but Mistral API key is not configured")
                else:
                    app_logger.info("AI PDF operations configured successfully")
            else:
                app_logger.info("AI PDF operations are disabled")
                
        except Exception as e:
            app_logger.error(f"Error during AI PDF operations startup validation: {str(e)}", exc_info=True)
    
    
    # Include routers
    app.include_router(pdf.router, prefix="/api/v1/pdf", tags=["PDF Operations"])
    
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
                    "metadata_extraction": True
                },
                "limits": {
                    "max_file_size_mb": 50,
                    "max_merge_files": 20,
                    "supported_formats": ["pdf"]
                },
                "endpoints": {
                    "documentation": "/docs",
                    "openapi": "/openapi.json",
                    "n8n_info": "/n8n"
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
                    "validation": "/api/v1/pdf/validate",
                    "metadata": "/api/v1/pdf/metadata"
                },
                "quick_start": {
                    "1": "Check service health at /health",
                    "2": "Validate PDF files at /api/v1/pdf/validate", 
                    "3": "Process PDFs using /api/v1/pdf/* endpoints",
                    "4": "View full documentation at /docs"
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
