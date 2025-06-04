"""
Global error handlers and custom exceptions.

Provides centralized error handling for the FastAPI application.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Union

logger = logging.getLogger(__name__)

class PDFProcessingError(Exception):
    """Custom exception for PDF processing errors."""
    
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class FileSizeError(Exception):
    """Custom exception for file size validation errors."""
    pass

class FileFormatError(Exception):
    """Custom exception for file format validation errors."""
    pass

def setup_exception_handlers(app: FastAPI):
    """Setup global exception handlers for the FastAPI app."""
    
    @app.exception_handler(PDFProcessingError)
    async def pdf_processing_error_handler(request: Request, exc: PDFProcessingError):
        logger.error(f"PDF processing error: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "PDF Processing Error",
                "message": exc.message,
                "type": "pdf_processing_error"
            }
        )
    
    @app.exception_handler(FileSizeError)
    async def file_size_error_handler(request: Request, exc: FileSizeError):
        logger.error(f"File size error: {str(exc)}")
        return JSONResponse(
            status_code=413,
            content={
                "error": "File Too Large",
                "message": str(exc),
                "type": "file_size_error"
            }
        )
    
    @app.exception_handler(FileFormatError)
    async def file_format_error_handler(request: Request, exc: FileFormatError):
        logger.error(f"File format error: {str(exc)}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid File Format",
                "message": str(exc),
                "type": "file_format_error"
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        logger.error(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "message": "Invalid request data",
                "details": exc.errors(),
                "type": "validation_error"
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP Error",
                "message": exc.detail,
                "type": "http_error"
            }
        )
    
    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "type": "internal_error"
            }
        )
