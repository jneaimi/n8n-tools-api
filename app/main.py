"""
FastAPI application main entry point.

This module initializes the FastAPI application with proper configuration
for n8n workflow automation integration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.api.routes import pdf
from app.core.config import settings
from app.core.errors import setup_exception_handlers

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="N8N Tools API",
        description="FastAPI-based microservice for PDF manipulation designed for n8n workflow automation",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
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
    
    # Include routers
    app.include_router(pdf.router, prefix="/api/v1/pdf", tags=["PDF Operations"])
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint for monitoring."""
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "service": "n8n-tools-api",
                "version": "0.1.0"
            }
        )
    
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information."""
        return JSONResponse(
            content={
                "message": "N8N Tools API",
                "version": "0.1.0",
                "docs": "/docs",
                "health": "/health"
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
