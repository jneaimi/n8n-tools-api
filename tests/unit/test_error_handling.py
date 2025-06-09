"""
Unit tests for error handling functionality.

Tests custom exceptions, error response formatting, logging,
and error recovery mechanisms.
"""

import pytest
from unittest.mock import patch, MagicMock
import logging

from app.core.errors import (
    PDFProcessingError,
    FileValidationError,
    APIError,
    format_error_response,
    handle_pdf_error,
    handle_validation_error
)


@pytest.mark.unit
class TestCustomExceptions:
    """Test custom exception classes."""
    
    def test_pdf_processing_error_creation(self):
        """Test PDFProcessingError exception creation."""
        message = "Test PDF processing error"
        error = PDFProcessingError(message)
        
        assert str(error) == message
        assert error.message == message
        assert isinstance(error, Exception)
    
    def test_pdf_processing_error_with_details(self):
        """Test PDFProcessingError with additional details."""
        message = "PDF processing failed"
        details = {"page": 5, "operation": "split"}
        error = PDFProcessingError(message, details=details)
        
        assert error.message == message
        assert error.details == details
    
    def test_file_validation_error_creation(self):
        """Test FileValidationError exception creation."""
        message = "Invalid file format"
        filename = "test.txt"
        error = FileValidationError(message, filename=filename)
        
        assert str(error) == message
        assert error.filename == filename
    
    def test_api_error_creation(self):
        """Test APIError exception creation."""
        message = "API error occurred"
        status_code = 400
        error_code = "INVALID_REQUEST"
        error = APIError(message, status_code=status_code, error_code=error_code)
        
        assert error.message == message
        assert error.status_code == status_code
        assert error.error_code == error_code
    
    def test_api_error_default_values(self):
        """Test APIError with default values."""
        message = "Generic API error"
        error = APIError(message)
        
        assert error.message == message
        assert error.status_code == 500
        assert error.error_code == "INTERNAL_ERROR"


@pytest.mark.unit
class TestErrorFormatting:
    """Test error response formatting."""
    
    def test_format_error_response_basic(self):
        """Test basic error response formatting."""
        message = "Test error"
        response = format_error_response(message)
        
        assert "error" in response
        assert response["error"] == message
        assert "timestamp" in response
        assert "request_id" in response
    
    def test_format_error_response_with_details(self):
        """Test error response formatting with details."""
        message = "Detailed error"
        details = {"field": "value", "code": 123}
        response = format_error_response(message, details=details)
        
        assert response["error"] == message
        assert response["details"] == details
    
    def test_format_error_response_with_suggestions(self):
        """Test error response formatting with suggestions."""
        message = "User error"
        suggestions = ["Check file format", "Reduce file size"]
        response = format_error_response(message, suggestions=suggestions)
        
        assert response["error"] == message
        assert response["suggestions"] == suggestions
    
    def test_format_error_response_complete(self):
        """Test error response formatting with all fields."""
        message = "Complete error"
        details = {"page": 1}
        suggestions = ["Try again"]
        error_code = "PDF_ERROR"
        
        response = format_error_response(
            message,
            details=details,
            suggestions=suggestions,
            error_code=error_code
        )
        
        assert response["error"] == message
        assert response["details"] == details
        assert response["suggestions"] == suggestions
        assert response["error_code"] == error_code


@pytest.mark.unit
class TestErrorHandlers:
    """Test error handling functions."""
    
    @patch('app.core.errors.logger')
    def test_handle_pdf_error_logging(self, mock_logger):
        """Test that PDF errors are properly logged."""
        error = PDFProcessingError("Test PDF error")
        operation = "split"
        
        response = handle_pdf_error(error, operation)
        
        # Verify logging was called
        mock_logger.error.assert_called_once()
        
        # Verify response format
        assert "error" in response
        assert "PDF processing failed" in response["error"]
        assert response["operation"] == operation
    
    @patch('app.core.errors.logger')
    def test_handle_validation_error_logging(self, mock_logger):
        """Test that validation errors are properly logged."""
        error = FileValidationError("Invalid file", filename="test.txt")
        
        response = handle_validation_error(error)
        
        # Verify logging was called
        mock_logger.warning.assert_called_once()
        
        # Verify response format
        assert "error" in response
        assert response["filename"] == "test.txt"
    
    def test_handle_pdf_error_with_suggestions(self):
        """Test PDF error handling includes helpful suggestions."""
        error = PDFProcessingError("Corrupted PDF")
        
        response = handle_pdf_error(error, "merge")
        
        assert "suggestions" in response
        assert isinstance(response["suggestions"], list)
        assert len(response["suggestions"]) > 0
    
    def test_handle_validation_error_with_suggestions(self):
        """Test validation error handling includes helpful suggestions."""
        error = FileValidationError("File too large", filename="huge.pdf")
        
        response = handle_validation_error(error)
        
        assert "suggestions" in response
        assert any("size" in suggestion.lower() for suggestion in response["suggestions"])


@pytest.mark.unit
class TestErrorRecovery:
    """Test error recovery mechanisms."""
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self):
        """Test retry mechanism for transient errors."""
        from app.utils.retry import retry_on_error
        
        call_count = 0
        
        @retry_on_error(max_retries=3, delay=0.1)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise PDFProcessingError("Transient error")
            return "success"
        
        result = await failing_function()
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self):
        """Test retry mechanism when all retries are exhausted."""
        from app.utils.retry import retry_on_error
        
        @retry_on_error(max_retries=2, delay=0.1)
        async def always_failing_function():
            raise PDFProcessingError("Persistent error")
        
        with pytest.raises(PDFProcessingError, match="Persistent error"):
            await always_failing_function()
    
    def test_graceful_degradation(self):
        """Test graceful degradation when optional features fail."""
        from app.utils.error_recovery import graceful_fallback
        
        def primary_function():
            raise Exception("Primary failed")
        
        def fallback_function():
            return "fallback_result"
        
        result = graceful_fallback(primary_function, fallback_function)
        
        assert result == "fallback_result"


@pytest.mark.unit
class TestErrorContext:
    """Test error context and tracing."""
    
    def test_error_context_manager(self):
        """Test error context manager for operation tracking."""
        from app.utils.error_context import error_context
        
        with error_context("pdf_split", file_id="123") as ctx:
            ctx.add_info("pages", "1-5")
            ctx.add_info("user", "test_user")
            
            # Simulate an error
            try:
                raise PDFProcessingError("Test error")
            except PDFProcessingError as e:
                error_data = ctx.format_error(e)
                
                assert error_data["operation"] == "pdf_split"
                assert error_data["context"]["file_id"] == "123"
                assert error_data["context"]["pages"] == "1-5"
                assert error_data["context"]["user"] == "test_user"
    
    @patch('app.core.errors.logger')
    def test_error_correlation_id(self, mock_logger):
        """Test error correlation ID for request tracing."""
        from app.utils.error_context import generate_correlation_id, set_correlation_id
        
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)
        
        error = PDFProcessingError("Test error")
        response = handle_pdf_error(error, "test")
        
        assert response["correlation_id"] == correlation_id
    
    def test_error_metrics_collection(self):
        """Test error metrics collection for monitoring."""
        from app.utils.metrics import ErrorMetrics
        
        metrics = ErrorMetrics()
        
        # Simulate various errors
        metrics.record_error("pdf_processing", "split", "INVALID_RANGE")
        metrics.record_error("file_validation", "upload", "TOO_LARGE")
        metrics.record_error("pdf_processing", "merge", "CORRUPTED_PDF")
        
        stats = metrics.get_stats()
        
        assert stats["total_errors"] == 3
        assert stats["by_category"]["pdf_processing"] == 2
        assert stats["by_category"]["file_validation"] == 1
        assert stats["by_operation"]["split"] == 1
        assert stats["by_operation"]["upload"] == 1
        assert stats["by_operation"]["merge"] == 1


@pytest.mark.unit
class TestErrorSanitization:
    """Test error message sanitization for security."""
    
    def test_sanitize_error_message(self):
        """Test error message sanitization removes sensitive information."""
        from app.utils.error_sanitizer import sanitize_error_message
        
        sensitive_messages = [
            "Error accessing /secret/path/file.pdf",
            "Database password: secret123 failed",
            "API key abc123xyz failed validation",
            "Internal server error: connection to 192.168.1.100 failed"
        ]
        
        for message in sensitive_messages:
            sanitized = sanitize_error_message(message)
            
            # Should not contain paths, passwords, keys, or IPs
            assert "/secret/" not in sanitized
            assert "secret123" not in sanitized
            assert "abc123xyz" not in sanitized
            assert "192.168.1.100" not in sanitized
    
    def test_error_message_for_production(self):
        """Test error messages are appropriate for production."""
        from app.utils.error_sanitizer import get_user_friendly_message
        
        technical_errors = [
            "AttributeError: 'NoneType' object has no attribute 'read'",
            "FileNotFoundError: [Errno 2] No such file or directory",
            "MemoryError: Unable to allocate 4.00 GiB for an array",
            "ConnectionError: HTTPSConnectionPool(host='api.example.com')"
        ]
        
        for error in technical_errors:
            user_message = get_user_friendly_message(error)
            
            # Should be user-friendly and not expose technical details
            assert "AttributeError" not in user_message
            assert "FileNotFoundError" not in user_message
            assert "MemoryError" not in user_message
            assert "ConnectionError" not in user_message
            assert len(user_message) > 0
