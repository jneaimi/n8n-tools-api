"""
Comprehensive logging system for n8n Tools API.

This module provides structured JSON logging with correlation IDs, request/response
tracking, and specialized logging for PDF operations. Designed for production
monitoring and debugging of n8n workflow integrations.
"""

import logging
import json
import sys
import time
import uuid
from typing import Callable, Optional, Dict, Any
from datetime import datetime
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings

# Context variable for correlation ID
correlation_id_context: ContextVar[Optional[str]] = ContextVar(
    'correlation_id', default=None
)

class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    
    Formats log records as JSON with consistent structure including
    correlation IDs, timestamps, and application context.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        
        # Base log structure
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add correlation ID if available
        correlation_id = correlation_id_context.get()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging() -> logging.Logger:
    """
    Configure application logging with JSON formatter.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    
    # Configure root logger
    logger = logging.getLogger("n8n-tools-api")
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    # Set log level based on configuration
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)
    handler.setLevel(log_level)
    
    logger.addHandler(handler)
    
    # Prevent duplicate logs from parent loggers
    logger.propagate = False
    
    return logger

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.
    
    Generates correlation IDs for request tracking and logs detailed
    information about each HTTP transaction including timing metrics.
    """
    
    def __init__(self, app, logger: Optional[logging.Logger] = None):
        super().__init__(app)
        self.logger = logger or logging.getLogger("n8n-tools-api.middleware")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging."""
        
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        correlation_id_context.set(correlation_id)
        
        # Store correlation ID in request state for access in endpoints
        request.state.correlation_id = correlation_id
        
        # Prepare request log data
        request_data = {
            "correlation_id": correlation_id,
            "type": "request",
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": {
                "user-agent": request.headers.get("user-agent"),
                "content-type": request.headers.get("content-type"),
                "content-length": request.headers.get("content-length"),
                "origin": request.headers.get("origin"),
                "referer": request.headers.get("referer")
            },
            "client_ip": self._get_client_ip(request),
            "timestamp": time.time()
        }
        
        # Remove None values from headers
        request_data["headers"] = {
            k: v for k, v in request_data["headers"].items() if v is not None
        }
        
        # Log request
        self.logger.info(
            "HTTP Request",
            extra={"extra_fields": request_data}
        )
        
        # Process request
        start_time = time.time()
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Prepare response log data
            response_data = {
                "correlation_id": correlation_id,
                "type": "response",
                "status_code": response.status_code,
                "process_time_ms": round(process_time * 1000, 2),
                "response_size": response.headers.get("content-length"),
                "content_type": response.headers.get("content-type"),
                "timestamp": time.time()
            }
            
            # Log response
            log_level = logging.INFO
            if response.status_code >= 400:
                log_level = logging.WARNING if response.status_code < 500 else logging.ERROR
            
            self.logger.log(
                log_level,
                f"HTTP Response - {response.status_code}",
                extra={"extra_fields": response_data}
            )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Processing-Time-Ms"] = str(response_data["process_time_ms"])
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            # Prepare error log data
            error_data = {
                "correlation_id": correlation_id,
                "type": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "process_time_ms": round(process_time * 1000, 2),
                "timestamp": time.time()
            }
            
            # Log error
            self.logger.error(
                f"HTTP Request Error - {type(e).__name__}",
                extra={"extra_fields": error_data},
                exc_info=True
            )
            
            raise
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request."""
        
        # Check for forwarded headers (common in reverse proxy setups)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        if request.client:
            return request.client.host
        
        return None

def log_pdf_operation(
    operation: str,
    filename: str,
    file_size: int,
    pages: Optional[int] = None,
    processing_time_ms: Optional[float] = None,
    output_files: Optional[int] = None,
    correlation_id: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log PDF operation with structured data.
    
    Args:
        operation: Type of PDF operation (split, merge, validate, metadata)
        filename: Name of the processed file
        file_size: Size of file in bytes
        pages: Number of pages in the PDF
        processing_time_ms: Processing time in milliseconds
        output_files: Number of output files generated
        correlation_id: Request correlation ID
        **kwargs: Additional operation-specific data
    """
    
    logger = logging.getLogger("n8n-tools-api.pdf")
    
    # Use correlation ID from context if not provided
    if not correlation_id:
        correlation_id = correlation_id_context.get()
    
    # Prepare operation log data
    operation_data = {
        "correlation_id": correlation_id,
        "type": "pdf_operation",
        "operation": operation,
        "filename": filename,
        "file_size_bytes": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "timestamp": time.time()
    }
    
    # Add optional fields
    if pages is not None:
        operation_data["pages"] = pages
    
    if processing_time_ms is not None:
        operation_data["processing_time_ms"] = round(processing_time_ms, 2)
    
    if output_files is not None:
        operation_data["output_files"] = output_files
    
    # Add any additional kwargs
    operation_data.update(kwargs)
    
    logger.info(
        f"PDF Operation - {operation} on {filename}",
        extra={"extra_fields": operation_data}
    )

def log_file_upload(
    filename: str,
    file_size: int,
    content_type: str,
    correlation_id: Optional[str] = None
) -> None:
    """
    Log file upload operation.
    
    Args:
        filename: Name of uploaded file
        file_size: Size of file in bytes
        content_type: MIME type of file
        correlation_id: Request correlation ID
    """
    
    logger = logging.getLogger("n8n-tools-api.upload")
    
    if not correlation_id:
        correlation_id = correlation_id_context.get()
    
    upload_data = {
        "correlation_id": correlation_id,
        "type": "file_upload",
        "filename": filename,
        "file_size_bytes": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "content_type": content_type,
        "timestamp": time.time()
    }
    
    logger.info(
        f"File Upload - {filename}",
        extra={"extra_fields": upload_data}
    )

def log_validation_result(
    filename: str,
    is_valid: bool,
    error_message: Optional[str] = None,
    validation_time_ms: Optional[float] = None,
    correlation_id: Optional[str] = None
) -> None:
    """
    Log file validation result.
    
    Args:
        filename: Name of validated file
        is_valid: Whether file passed validation
        error_message: Validation error message if invalid
        validation_time_ms: Time taken for validation
        correlation_id: Request correlation ID
    """
    
    logger = logging.getLogger("n8n-tools-api.validation")
    
    if not correlation_id:
        correlation_id = correlation_id_context.get()
    
    validation_data = {
        "correlation_id": correlation_id,
        "type": "validation",
        "filename": filename,
        "is_valid": is_valid,
        "timestamp": time.time()
    }
    
    if error_message:
        validation_data["error_message"] = error_message
    
    if validation_time_ms is not None:
        validation_data["validation_time_ms"] = round(validation_time_ms, 2)
    
    log_level = logging.INFO if is_valid else logging.WARNING
    message = f"Validation {'Success' if is_valid else 'Failed'} - {filename}"
    
    logger.log(
        log_level,
        message,
        extra={"extra_fields": validation_data}
    )

def get_correlation_id() -> Optional[str]:
    """
    Get the current request correlation ID.
    
    Returns:
        str: Current correlation ID or None if not set
    """
    return correlation_id_context.get()

def log_performance_metric(
    metric_name: str,
    value: float,
    unit: str = "ms",
    context: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
) -> None:
    """
    Log performance metrics.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        context: Additional context data
        correlation_id: Request correlation ID
    """
    
    logger = logging.getLogger("n8n-tools-api.performance")
    
    if not correlation_id:
        correlation_id = correlation_id_context.get()
    
    metric_data = {
        "correlation_id": correlation_id,
        "type": "performance_metric",
        "metric_name": metric_name,
        "value": value,
        "unit": unit,
        "timestamp": time.time()
    }
    
    if context:
        metric_data["context"] = context
    
    logger.info(
        f"Performance Metric - {metric_name}: {value} {unit}",
        extra={"extra_fields": metric_data}
    )

# Initialize global logger
app_logger = setup_logging()

# Export commonly used functions and classes
__all__ = [
    'setup_logging',
    'RequestLoggingMiddleware', 
    'log_pdf_operation',
    'log_file_upload',
    'log_validation_result',
    'log_performance_metric',
    'get_correlation_id',
    'app_logger'
]