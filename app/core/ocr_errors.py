"""
OCR-specific error classes and handlers.

Provides specialized exception handling for OCR operations with
enhanced error context, recovery mechanisms, and monitoring.
"""

import time
import uuid
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

from app.core.errors import PDFProcessingError, FileSizeError, FileFormatError
from app.core.logging import get_correlation_id

logger = logging.getLogger(__name__)

class OCRErrorCode(str, Enum):
    """Standardized OCR error codes."""
    
    # File validation errors
    INVALID_FILE_FORMAT = "OCR_INVALID_FILE_FORMAT"
    FILE_TOO_LARGE = "OCR_FILE_TOO_LARGE"
    FILE_CORRUPTED = "OCR_FILE_CORRUPTED"
    FILE_EMPTY = "OCR_FILE_EMPTY"
    FILE_UNREADABLE = "OCR_FILE_UNREADABLE"
    
    # Network and URL errors
    URL_UNREACHABLE = "OCR_URL_UNREACHABLE"
    URL_INVALID = "OCR_URL_INVALID"
    DOWNLOAD_FAILED = "OCR_DOWNLOAD_FAILED"
    DOWNLOAD_TIMEOUT = "OCR_DOWNLOAD_TIMEOUT"
    
    # API errors
    API_AUTHENTICATION_FAILED = "OCR_API_AUTH_FAILED"
    API_RATE_LIMIT_EXCEEDED = "OCR_API_RATE_LIMIT"
    API_QUOTA_EXCEEDED = "OCR_API_QUOTA_EXCEEDED"
    API_SERVICE_UNAVAILABLE = "OCR_API_UNAVAILABLE"
    API_TIMEOUT = "OCR_API_TIMEOUT"
    API_INVALID_RESPONSE = "OCR_API_INVALID_RESPONSE"
    
    # Processing errors
    PROCESSING_FAILED = "OCR_PROCESSING_FAILED"
    PARSING_FAILED = "OCR_PARSING_FAILED"
    EXTRACTION_FAILED = "OCR_EXTRACTION_FAILED"
    IMAGE_PROCESSING_FAILED = "OCR_IMAGE_PROCESSING_FAILED"
    
    # System errors
    STORAGE_ERROR = "OCR_STORAGE_ERROR"
    MEMORY_ERROR = "OCR_MEMORY_ERROR"
    TIMEOUT_ERROR = "OCR_TIMEOUT_ERROR"
    INTERNAL_ERROR = "OCR_INTERNAL_ERROR"
    
    # Configuration errors
    INVALID_CONFIGURATION = "OCR_INVALID_CONFIG"
    MISSING_CREDENTIALS = "OCR_MISSING_CREDENTIALS"
    SERVICE_UNAVAILABLE = "OCR_SERVICE_UNAVAILABLE"

@dataclass
class OCRErrorContext:
    """Enhanced error context for OCR operations."""
    
    correlation_id: str = field(default_factory=lambda: get_correlation_id() or str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    operation: Optional[str] = None
    file_info: Optional[Dict[str, Any]] = None
    api_info: Optional[Dict[str, Any]] = None
    processing_info: Optional[Dict[str, Any]] = None
    user_info: Optional[Dict[str, Any]] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)
    
    def add_file_context(self, filename: str, file_size: int, file_type: str):
        """Add file-related context."""
        self.file_info = {
            "filename": filename,
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "file_type": file_type
        }
    
    def add_api_context(self, api_endpoint: str, request_id: Optional[str] = None):
        """Add API-related context."""
        self.api_info = {
            "endpoint": api_endpoint,
            "request_id": request_id,
            "timestamp": time.time()
        }
    
    def add_processing_context(self, processing_time: float, pages_processed: int = 0):
        """Add processing-related context."""
        self.processing_info = {
            "processing_time_ms": processing_time * 1000,
            "pages_processed": pages_processed,
            "memory_usage_mb": self._get_memory_usage()
        }
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "operation": self.operation,
            "file_info": self.file_info,
            "api_info": self.api_info,
            "processing_info": self.processing_info,
            "user_info": self.user_info,
            "additional_context": self.additional_context
        }

class OCRError(Exception):
    """Base class for OCR-specific errors."""
    
    def __init__(
        self,
        message: str,
        error_code: OCRErrorCode,
        context: Optional[OCRErrorContext] = None,
        recoverable: bool = False,
        suggestions: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.context = context or OCRErrorContext()
        self.recoverable = recoverable
        self.suggestions = suggestions or []
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "status": "error",
            "error_code": self.error_code.value,
            "message": self.message,
            "recoverable": self.recoverable,
            "suggestions": self.suggestions,
            "details": self.details,
            "context": self.context.to_dict() if self.context else None,
            "timestamp": time.time()
        }
    
    def add_suggestion(self, suggestion: str):
        """Add a recovery suggestion."""
        if suggestion not in self.suggestions:
            self.suggestions.append(suggestion)

class OCRFileValidationError(OCRError):
    """Error for file validation failures."""
    
    def __init__(self, message: str, filename: str = None, **kwargs):
        suggestions = [
            "Ensure file is a valid PDF, PNG, JPG, JPEG, or TIFF format",
            "Check that the file is not corrupted",
            "Verify file size is under 50MB"
        ]
        super().__init__(
            message,
            OCRErrorCode.INVALID_FILE_FORMAT,
            suggestions=suggestions,
            **kwargs
        )
        if filename and self.context:
            self.context.additional_context["filename"] = filename

class OCRFileSizeError(OCRError):
    """Error for file size violations."""
    
    def __init__(self, message: str, file_size: int, max_size: int, **kwargs):
        suggestions = [
            f"Reduce file size to under {max_size / (1024*1024):.1f}MB",
            "Compress the PDF or image before uploading",
            "Split large documents into smaller files"
        ]
        super().__init__(
            message,
            OCRErrorCode.FILE_TOO_LARGE,
            suggestions=suggestions,
            recoverable=True,
            **kwargs
        )
        self.details.update({
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024*1024), 2),
            "max_size_bytes": max_size,
            "max_size_mb": round(max_size / (1024*1024), 2)
        })

class OCRURLError(OCRError):
    """Error for URL-related failures."""
    
    def __init__(self, message: str, url: str, status_code: int = None, **kwargs):
        error_code = OCRErrorCode.URL_UNREACHABLE
        suggestions = [
            "Verify the URL is accessible and points to a valid document",
            "Check that the URL returns a PDF or image file",
            "Ensure the URL is publicly accessible (not behind authentication)"
        ]
        
        if status_code:
            if status_code == 404:
                error_code = OCRErrorCode.URL_UNREACHABLE
                suggestions.append("The document was not found at the provided URL")
            elif status_code >= 500:
                error_code = OCRErrorCode.API_SERVICE_UNAVAILABLE
                suggestions.append("The remote server is experiencing issues, try again later")
        
        super().__init__(
            message,
            error_code,
            suggestions=suggestions,
            recoverable=True,
            **kwargs
        )
        self.details.update({
            "url": url,
            "status_code": status_code
        })

class OCRAPIError(OCRError):
    """Error for API communication failures."""
    
    def __init__(
        self,
        message: str,
        api_response_code: int = None,
        api_response_text: str = None,
        **kwargs
    ):
        error_code = OCRErrorCode.API_SERVICE_UNAVAILABLE
        suggestions = []
        recoverable = False
        
        if api_response_code:
            if api_response_code == 401:
                error_code = OCRErrorCode.API_AUTHENTICATION_FAILED
                suggestions = [
                    "Verify your Mistral API key is valid and active",
                    "Check that the API key has OCR permissions",
                    "Ensure the API key is not expired"
                ]
            elif api_response_code == 429:
                error_code = OCRErrorCode.API_RATE_LIMIT_EXCEEDED
                suggestions = [
                    "Wait before making another request",
                    "Implement request throttling in your application",
                    "Consider upgrading your API plan for higher limits"
                ]
                recoverable = True
            elif api_response_code >= 500:
                error_code = OCRErrorCode.API_SERVICE_UNAVAILABLE
                suggestions = [
                    "The OCR service is temporarily unavailable",
                    "Try again in a few minutes",
                    "Check the service status page"
                ]
                recoverable = True
        
        super().__init__(
            message,
            error_code,
            suggestions=suggestions,
            recoverable=recoverable,
            **kwargs
        )
        self.details.update({
            "api_response_code": api_response_code,
            "api_response_text": api_response_text
        })

class OCRProcessingError(OCRError):
    """Error for OCR processing failures."""
    
    def __init__(self, message: str, processing_stage: str = None, **kwargs):
        suggestions = [
            "Try processing the document again",
            "Ensure the document contains readable text or clear images",
            "Check if the document is password-protected or encrypted"
        ]
        
        super().__init__(
            message,
            OCRErrorCode.PROCESSING_FAILED,
            suggestions=suggestions,
            recoverable=True,
            **kwargs
        )
        if processing_stage:
            self.details["processing_stage"] = processing_stage

class OCRTimeoutError(OCRError):
    """Error for timeout situations."""
    
    def __init__(self, message: str, timeout_duration: float, operation: str = None, **kwargs):
        suggestions = [
            "Try processing a smaller document",
            "Retry the operation as it may succeed",
            "Break large documents into smaller chunks"
        ]
        
        super().__init__(
            message,
            OCRErrorCode.TIMEOUT_ERROR,
            suggestions=suggestions,
            recoverable=True,
            **kwargs
        )
        self.details.update({
            "timeout_duration_seconds": timeout_duration,
            "operation": operation
        })

class OCRErrorHandler:
    """Centralized error handling for OCR operations."""
    
    def __init__(self):
        self.error_metrics = {}
    
    def handle_validation_error(self, error: Exception, filename: str = None) -> OCRError:
        """Convert validation errors to OCR errors."""
        if isinstance(error, FileSizeError):
            # Extract size information if available
            return OCRFileSizeError(
                str(error),
                file_size=getattr(error, 'file_size', 0),
                max_size=getattr(error, 'max_size', 50 * 1024 * 1024)
            )
        elif isinstance(error, FileFormatError):
            return OCRFileValidationError(str(error), filename=filename)
        else:
            return OCRError(
                f"File validation failed: {str(error)}",
                OCRErrorCode.INVALID_FILE_FORMAT,
                recoverable=True
            )
    
    def handle_api_error(self, error: Exception, response_code: int = None) -> OCRAPIError:
        """Convert API errors to OCR errors."""
        return OCRAPIError(
            str(error),
            api_response_code=response_code,
            api_response_text=str(error)
        )
    
    def handle_timeout_error(self, error: Exception, duration: float, operation: str = None) -> OCRTimeoutError:
        """Convert timeout errors to OCR errors."""
        return OCRTimeoutError(
            f"Operation timed out after {duration:.1f} seconds: {str(error)}",
            timeout_duration=duration,
            operation=operation
        )
    
    def handle_unknown_error(self, error: Exception, operation: str = None) -> OCRError:
        """Handle unexpected errors."""
        context = OCRErrorContext()
        if operation:
            context.operation = operation
        
        return OCRError(
            f"Unexpected error during OCR processing: {str(error)}",
            OCRErrorCode.INTERNAL_ERROR,
            context=context,
            suggestions=[
                "Try the operation again",
                "Contact support if the issue persists",
                "Check the service status"
            ]
        )
    
    def record_error_metric(self, error: OCRError):
        """Record error metrics for monitoring."""
        error_type = error.error_code.value
        timestamp = int(time.time())
        
        if error_type not in self.error_metrics:
            self.error_metrics[error_type] = {
                "count": 0,
                "first_seen": timestamp,
                "last_seen": timestamp
            }
        
        self.error_metrics[error_type]["count"] += 1
        self.error_metrics[error_type]["last_seen"] = timestamp
        
        logger.error(
            f"OCR Error: {error_type}",
            extra={
                "error_code": error_type,
                "correlation_id": error.context.correlation_id if error.context else None,
                "recoverable": error.recoverable,
                "suggestions_count": len(error.suggestions)
            }
        )
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get current error metrics."""
        return {
            "total_errors": sum(metric["count"] for metric in self.error_metrics.values()),
            "error_types": len(self.error_metrics),
            "errors_by_type": self.error_metrics,
            "generated_at": time.time()
        }

# Global error handler instance
ocr_error_handler = OCRErrorHandler()
