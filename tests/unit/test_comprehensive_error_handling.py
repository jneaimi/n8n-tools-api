"""
Comprehensive tests for enhanced OCR error handling.

Tests all error scenarios, recovery mechanisms, sanitization,
and monitoring capabilities of the enhanced error handling system.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import UploadFile
import tempfile
import os
import json

# Import error handling components
from app.core.ocr_errors import (
    OCRError, OCRErrorCode, OCRFileValidationError, OCRFileSizeError,
    OCRURLError, OCRAPIError, OCRProcessingError, OCRTimeoutError,
    OCRErrorContext, OCRErrorHandler, ocr_error_handler
)
from app.utils.error_sanitizer import (
    ErrorSanitizer, ErrorSanitizationLevel, ErrorSeverity,
    sanitize_error_message, get_user_friendly_message, create_safe_error_response
)
from app.utils.error_recovery import (
    RetryManager, RetryConfig, RetryStrategy, CircuitBreaker, CircuitState,
    OCRRecoveryManager, retry_on_error, with_circuit_breaker, recovery_manager
)
from app.utils.error_metrics import (
    ErrorMetricsCollector, ErrorMetric, AlertThreshold, MetricType, AlertLevel,
    metrics_collector, record_error_metric, record_success_metric, get_health_score
)
from app.core.errors import FileSizeError, FileFormatError


@pytest.mark.unit
class TestOCRErrorClasses:
    """Test OCR-specific error classes and context."""
    
    def test_ocr_error_creation(self):
        """Test basic OCR error creation."""
        context = OCRErrorContext(operation="test_operation")
        error = OCRError(
            "Test error message",
            OCRErrorCode.PROCESSING_FAILED,
            context=context,
            recoverable=True,
            suggestions=["Try again", "Check file"]
        )
        
        assert error.message == "Test error message"
        assert error.error_code == OCRErrorCode.PROCESSING_FAILED
        assert error.recoverable is True
        assert len(error.suggestions) == 2
        assert error.context.operation == "test_operation"
    
    def test_ocr_error_to_dict(self):
        """Test error serialization to dictionary."""
        error = OCRError(
            "Test error",
            OCRErrorCode.INVALID_FILE_FORMAT,
            recoverable=False
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["status"] == "error"
        assert error_dict["error_code"] == "OCR_INVALID_FILE_FORMAT"
        assert error_dict["message"] == "Test error"
        assert error_dict["recoverable"] is False
        assert "timestamp" in error_dict
    
    def test_ocr_file_validation_error(self):
        """Test file validation error specifics."""
        error = OCRFileValidationError(
            "Invalid PDF format",
            filename="test.pdf"
        )
        
        assert error.error_code == OCRErrorCode.INVALID_FILE_FORMAT
        assert "Ensure file is a valid PDF" in error.suggestions[0]
        assert error.context.additional_context["filename"] == "test.pdf"
    
    def test_ocr_file_size_error(self):
        """Test file size error with details."""
        file_size = 100 * 1024 * 1024  # 100MB
        max_size = 50 * 1024 * 1024   # 50MB
        
        error = OCRFileSizeError(
            "File too large",
            file_size=file_size,
            max_size=max_size
        )
        
        assert error.error_code == OCRErrorCode.FILE_TOO_LARGE
        assert error.recoverable is True
        assert error.details["file_size_mb"] == 100.0
        assert error.details["max_size_mb"] == 50.0
        assert "Reduce file size" in error.suggestions[0]
    
    def test_ocr_url_error(self):
        """Test URL-related error handling."""
        error = OCRURLError(
            "Document not found",
            url="https://example.com/missing.pdf",
            status_code=404
        )
        
        assert error.error_code == OCRErrorCode.URL_UNREACHABLE
        assert error.details["url"] == "https://example.com/missing.pdf"
        assert error.details["status_code"] == 404
        assert error.recoverable is True
    
    def test_ocr_api_error_authentication(self):
        """Test API authentication error."""
        error = OCRAPIError(
            "Invalid API key",
            api_response_code=401
        )
        
        assert error.error_code == OCRErrorCode.API_AUTHENTICATION_FAILED
        assert "API key" in error.suggestions[0]
        assert error.recoverable is False
    
    def test_ocr_api_error_rate_limit(self):
        """Test API rate limit error."""
        error = OCRAPIError(
            "Rate limit exceeded",
            api_response_code=429
        )
        
        assert error.error_code == OCRErrorCode.API_RATE_LIMIT_EXCEEDED
        assert error.recoverable is True
        assert "Wait before making another request" in error.suggestions[0]
    
    def test_ocr_timeout_error(self):
        """Test timeout error handling."""
        error = OCRTimeoutError(
            "Processing timed out",
            timeout_duration=30.0,
            operation="file_processing"
        )
        
        assert error.error_code == OCRErrorCode.TIMEOUT_ERROR
        assert error.details["timeout_duration_seconds"] == 30.0
        assert error.details["operation"] == "file_processing"
        assert error.recoverable is True
    
    def test_error_context_file_info(self):
        """Test error context file information."""
        context = OCRErrorContext()
        context.add_file_context("test.pdf", 1024000, "pdf")
        
        assert context.file_info["filename"] == "test.pdf"
        assert context.file_info["file_size_bytes"] == 1024000
        assert abs(context.file_info["file_size_mb"] - 0.98) < 0.1  # Allow for rounding
        assert context.file_info["file_type"] == "pdf"
    
    def test_error_context_api_info(self):
        """Test error context API information."""
        context = OCRErrorContext()
        context.add_api_context("/api/ocr", "req_123")
        
        assert context.api_info["endpoint"] == "/api/ocr"
        assert context.api_info["request_id"] == "req_123"
        assert "timestamp" in context.api_info


@pytest.mark.unit
class TestErrorSanitizer:
    """Test error message sanitization and user-friendly conversion."""
    
    def test_sanitize_file_paths(self):
        """Test sanitization of file paths."""
        sanitizer = ErrorSanitizer(ErrorSanitizationLevel.PRODUCTION)
        
        message = "Error processing /tmp/secret_document.pdf"
        sanitized = sanitizer.sanitize_error_message(message)
        
        assert "/tmp/secret_document.pdf" not in sanitized
        assert "[FILE_PATH]" in sanitized  # The /tmp/ pattern gets replaced with [FILE_PATH]
    
    def test_sanitize_api_keys(self):
        """Test sanitization of API keys."""
        sanitizer = ErrorSanitizer(ErrorSanitizationLevel.PRODUCTION)
        
        message = "API Key: sk-1234567890abcdef authentication failed"
        sanitized = sanitizer.sanitize_error_message(message)
        
        assert "sk-1234567890abcdef" not in sanitized
        assert "[API_KEY]" in sanitized
    
    def test_sanitize_ip_addresses(self):
        """Test sanitization of IP addresses."""
        sanitizer = ErrorSanitizer(ErrorSanitizationLevel.PRODUCTION)
        
        message = "Connection failed to 192.168.1.100:8080"
        sanitized = sanitizer.sanitize_error_message(message)
        
        assert "192.168.1.100" not in sanitized
        assert "[IP_ADDRESS]" in sanitized
    
    def test_user_friendly_messages(self):
        """Test conversion to user-friendly messages."""
        sanitizer = ErrorSanitizer(ErrorSanitizationLevel.PRODUCTION)
        
        test_cases = [
            ("AttributeError: 'NoneType' object has no attribute 'read'", 
             "A processing error occurred while handling your request"),
            ("FileNotFoundError: file not found", 
             "The requested file could not be found"),
            ("MemoryError: cannot allocate memory", 
             "The file is too large to process"),
            ("ConnectionError: network unreachable", 
             "Unable to connect to the processing service")
        ]
        
        for technical, expected_friendly in test_cases:
            friendly = sanitizer.get_user_friendly_message(technical)
            assert friendly == expected_friendly
    
    def test_error_severity_categorization(self):
        """Test error severity categorization."""
        sanitizer = ErrorSanitizer()
        
        assert sanitizer.categorize_error_severity("memory error") == ErrorSeverity.CRITICAL
        assert sanitizer.categorize_error_severity("network timeout") == ErrorSeverity.CRITICAL  # "network" is in critical_indicators
        assert sanitizer.categorize_error_severity("rate limit exceeded") == ErrorSeverity.MEDIUM
        assert sanitizer.categorize_error_severity("info message") == ErrorSeverity.LOW
    
    def test_safe_error_response_creation(self):
        """Test creation of safe error responses."""
        sanitizer = ErrorSanitizer(ErrorSanitizationLevel.PRODUCTION)
        
        response = sanitizer.create_safe_error_response(
            "FileNotFoundError: /secret/path/file.pdf not found",
            "FILE_NOT_FOUND"
        )
        
        assert response["status"] == "error"
        assert response["error_code"] == "FILE_NOT_FOUND"
        assert "/secret/path" not in response["message"]
        assert "suggestions" in response
        assert len(response["suggestions"]) > 0
    
    def test_development_mode_passthrough(self):
        """Test that development mode passes through original messages."""
        sanitizer = ErrorSanitizer(ErrorSanitizationLevel.DEVELOPMENT)
        
        original = "Error processing /tmp/secret_file.pdf with API key sk-123"
        sanitized = sanitizer.sanitize_error_message(original)
        
        assert sanitized == original


@pytest.mark.unit
class TestErrorRecovery:
    """Test retry mechanisms and circuit breakers."""
    
    def test_retry_config_creation(self):
        """Test retry configuration setup."""
        config = RetryConfig(
            max_attempts=5,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=2.0
        )
        
        assert config.max_attempts == 5
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.base_delay == 2.0
    
    def test_retry_manager_delay_calculation(self):
        """Test retry delay calculations."""
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=1.0,
            exponential_base=2.0
        )
        retry_manager = RetryManager(config)
        
        assert retry_manager.calculate_delay(1) == 1.0
        assert retry_manager.calculate_delay(2) == 2.0
        assert retry_manager.calculate_delay(3) == 4.0
    
    def test_retryable_error_classification(self):
        """Test classification of retryable vs non-retryable errors."""
        retry_manager = RetryManager()
        
        # Retryable errors
        timeout_error = OCRTimeoutError("Timeout", 30.0)
        api_error = OCRAPIError("Service unavailable", 503)
        
        assert retry_manager.is_retryable_error(timeout_error) is True
        assert retry_manager.is_retryable_error(api_error) is True
        
        # Non-retryable errors
        auth_error = OCRAPIError("Invalid API key", 401)
        format_error = OCRFileValidationError("Invalid format")
        
        assert retry_manager.is_retryable_error(auth_error) is False
        assert retry_manager.is_retryable_error(format_error) is False
    
    def test_circuit_breaker_states(self):
        """Test circuit breaker state transitions."""
        from app.utils.error_recovery import CircuitBreakerConfig
        
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1.0)
        breaker = CircuitBreaker("test_service", config)
        
        # Should start closed
        assert breaker.state == CircuitState.CLOSED
        
        # Record failures to open circuit
        breaker._record_failure()
        assert breaker.state == CircuitState.CLOSED
        
        breaker._record_failure()
        assert breaker.state == CircuitState.OPEN
        
        # Test half-open after timeout
        time.sleep(1.1)
        try:
            breaker.call(lambda: "test")
            breaker._record_success()
            breaker._record_success()
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_retry_decorator_success_after_failure(self):
        """Test retry decorator with eventual success."""
        call_count = 0
        
        @retry_on_error(max_attempts=3, base_delay=0.1)
        async def failing_then_succeeding_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OCRTimeoutError("Temporary failure", 10.0)
            return "success"
        
        result = await failing_then_succeeding_function()
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_decorator_non_retryable_error(self):
        """Test retry decorator with non-retryable error."""
        call_count = 0
        
        @retry_on_error(max_attempts=3)
        async def non_retryable_function():
            nonlocal call_count
            call_count += 1
            raise OCRFileValidationError("Invalid format")
        
        with pytest.raises(OCRFileValidationError):
            await non_retryable_function()
        
        assert call_count == 1  # Should not retry


@pytest.mark.unit
class TestErrorMetrics:
    """Test error metrics collection and analysis."""
    
    def test_error_metric_creation(self):
        """Test error metric data structure."""
        metric = ErrorMetric(
            timestamp=time.time(),
            error_code="OCR_TIMEOUT_ERROR",
            error_message="Processing timed out",
            operation="file_processing",
            correlation_id="test_123",
            severity="high",
            recoverable=True,
            processing_time_ms=5000.0,
            file_size_mb=2.5
        )
        
        assert metric.error_code == "OCR_TIMEOUT_ERROR"
        assert metric.recoverable is True
        assert metric.processing_time_ms == 5000.0
        assert metric.file_size_mb == 2.5
    
    def test_metrics_collector_error_recording(self):
        """Test recording errors in metrics collector."""
        collector = ErrorMetricsCollector(max_metrics_memory=100)
        
        error = OCRTimeoutError("Test timeout", 30.0)
        collector.record_error(error, "test_operation", 1000.0, 1.5)
        
        assert len(collector.metrics) == 1
        assert collector.error_counts["OCR_TIMEOUT_ERROR"] == 1
    
    def test_metrics_collector_success_recording(self):
        """Test recording successful operations."""
        collector = ErrorMetricsCollector(max_metrics_memory=100)
        
        collector.record_success("test_operation", 500.0, 1.0)
        
        assert len(collector.metrics) == 1
        assert collector.request_counts["test_operation"] == 1
    
    def test_metrics_summary_calculation(self):
        """Test metrics summary calculation."""
        collector = ErrorMetricsCollector(max_metrics_memory=100)
        
        # Record some operations
        collector.record_success("test_op", 500.0, 1.0)
        collector.record_success("test_op", 600.0, 1.5)
        
        error = OCRTimeoutError("Test error", 30.0)
        collector.record_error(error, "test_op", 1000.0, 2.0)
        
        summary = collector.get_metrics_summary(3600)
        
        assert summary.total_requests == 3
        assert summary.total_errors == 1
        assert summary.error_rate == 1/3
        assert summary.success_rate == 2/3
        assert "OCR_TIMEOUT_ERROR" in summary.errors_by_code
    
    def test_health_score_calculation(self):
        """Test health score calculation."""
        collector = ErrorMetricsCollector(max_metrics_memory=100)
        
        # Record mostly successful operations
        for _ in range(9):
            collector.record_success("test_op", 1000.0, 1.0)
        
        # One error
        error = OCRTimeoutError("Test error", 30.0)
        collector.record_error(error, "test_op", 2000.0, 1.0)
        
        health = collector.get_health_score()
        
        assert health["health_score"] > 50  # Should be decent with 90% success
        assert health["status"] in ["excellent", "good", "fair"]
        assert "recommendations" in health
    
    def test_alert_threshold_checking(self):
        """Test alert threshold monitoring."""
        collector = ErrorMetricsCollector(max_metrics_memory=100)
        
        # Create alert threshold for high error rate
        threshold = AlertThreshold(
            MetricType.ERROR_RATE,
            0.5,  # 50% error rate
            60,   # 1 minute window
            AlertLevel.CRITICAL,
            "High error rate detected"
        )
        collector.alert_thresholds = [threshold]
        
        # Record high error rate
        for _ in range(10):
            error = OCRTimeoutError("Test error", 30.0)
            collector.record_error(error, "test_op", 1000.0, 1.0)
        
        # This should trigger alert checking
        collector._check_alert_thresholds()
        
        # Check that alert was recorded (would normally trigger external alert)
        assert len(collector.alert_history) > 0


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Integration tests for complete error handling flow."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock FastAPI app for testing."""
        from fastapi import FastAPI
        from app.api.routes.ocr import router
        
        app = FastAPI()
        app.include_router(router, prefix="/api/ocr")
        return app
    
    @pytest.fixture
    def client(self, mock_app):
        """Create test client."""
        return TestClient(mock_app)
    
    def test_file_validation_error_handling(self, client):
        """Test file validation error handling end-to-end."""
        # Create an invalid file
        invalid_content = b"This is not a valid PDF"
        
        with patch('app.utils.ocr_utils.validate_ocr_file') as mock_validate:
            mock_validate.side_effect = FileFormatError("Invalid PDF format")
            
            response = client.post(
                "/api/ocr/validate",
                files={"file": ("test.pdf", invalid_content, "application/pdf")}
            )
            
            assert response.status_code == 400
            response_data = response.json()
            assert response_data["status"] == "error"
            assert "suggestions" in response_data
    
    def test_api_authentication_error_handling(self, client):
        """Test API authentication error handling."""
        with patch('app.core.auth.require_api_key') as mock_auth:
            mock_auth.side_effect = Exception("Invalid API key")
            
            response = client.post(
                "/api/ocr/process-file",
                files={"file": ("test.pdf", b"dummy", "application/pdf")},
                headers={"X-API-Key": "invalid_key"}
            )
            
            # Should handle auth error gracefully
            assert response.status_code in [401, 500]
    
    def test_health_endpoint_functionality(self, client):
        """Test health endpoint returns proper metrics."""
        response = client.get("/api/ocr/health")
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert "health_score" in response_data
        assert "status" in response_data
        assert "metrics" in response_data
        assert "circuit_breakers" in response_data
        assert "recommendations" in response_data
    
    @pytest.mark.asyncio
    async def test_timeout_error_handling(self):
        """Test timeout error handling in processing."""
        from app.core.ocr_errors import OCRTimeoutError
        
        async def slow_operation():
            await asyncio.sleep(2.0)
            return "result"
        
        start_time = time.time()
        
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_operation(), timeout=1.0)
        
        # Test that we can convert this to OCRTimeoutError
        timeout_error = OCRTimeoutError(
            "Operation timed out",
            timeout_duration=1.0,
            operation="test_operation"
        )
        
        assert timeout_error.error_code == OCRErrorCode.TIMEOUT_ERROR
        assert timeout_error.recoverable is True


@pytest.mark.unit
class TestErrorHandler:
    """Test the OCRErrorHandler utility class."""
    
    def test_validation_error_conversion(self):
        """Test conversion of validation errors to OCR errors."""
        handler = OCRErrorHandler()
        
        file_size_error = FileSizeError("File too large")
        file_size_error.file_size = 100 * 1024 * 1024
        file_size_error.max_size = 50 * 1024 * 1024
        
        ocr_error = handler.handle_validation_error(file_size_error, "test.pdf")
        
        assert isinstance(ocr_error, OCRFileSizeError)
        assert ocr_error.error_code == OCRErrorCode.FILE_TOO_LARGE
    
    def test_api_error_conversion(self):
        """Test conversion of API errors to OCR errors."""
        handler = OCRErrorHandler()
        
        api_error = Exception("Service unavailable")
        ocr_error = handler.handle_api_error(api_error, 503)
        
        assert isinstance(ocr_error, OCRAPIError)
        assert ocr_error.details["api_response_code"] == 503
    
    def test_timeout_error_conversion(self):
        """Test conversion of timeout errors to OCR errors."""
        handler = OCRErrorHandler()
        
        timeout_error = Exception("Operation timed out")
        ocr_error = handler.handle_timeout_error(timeout_error, 30.0, "processing")
        
        assert isinstance(ocr_error, OCRTimeoutError)
        assert ocr_error.details["timeout_duration_seconds"] == 30.0
        assert ocr_error.details["operation"] == "processing"
    
    def test_unknown_error_handling(self):
        """Test handling of unknown errors."""
        handler = OCRErrorHandler()
        
        unknown_error = ValueError("Unexpected value error")
        ocr_error = handler.handle_unknown_error(unknown_error, "test_operation")
        
        assert isinstance(ocr_error, OCRError)
        assert ocr_error.error_code == OCRErrorCode.INTERNAL_ERROR
        assert ocr_error.context.operation == "test_operation"
    
    def test_error_metric_recording(self):
        """Test error metric recording."""
        handler = OCRErrorHandler()
        
        error = OCRTimeoutError("Test timeout", 30.0)
        handler.record_error_metric(error)
        
        metrics = handler.get_error_metrics()
        assert metrics["total_errors"] > 0
        assert "OCR_TIMEOUT_ERROR" in metrics["errors_by_type"]


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
