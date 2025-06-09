"""
Test cases for the logging system.

Tests JSON logging format, correlation IDs, request/response logging,
and PDF operation logging functionality.
"""

import pytest
import json
import uuid
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from io import StringIO
import sys

from app.main import app
from app.core.logging import (
    setup_logging,
    JSONFormatter,
    log_pdf_operation,
    log_file_upload,
    log_validation_result,
    log_performance_metric,
    get_correlation_id,
    correlation_id_context
)


class TestLoggingSystem:
    """Test suite for the logging system."""
    
    def test_json_formatter(self):
        """Test JSON formatter produces valid JSON output."""
        import logging
        
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.funcName = "test_function"
        record.module = "test_module"
        
        # Format the record
        formatted = formatter.format(record)
        
        # Should be valid JSON
        log_data = json.loads(formatted)
        
        # Check required fields
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test.logger"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test_module"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 42
        assert "timestamp" in log_data
    
    def test_json_formatter_with_correlation_id(self):
        """Test JSON formatter includes correlation ID when available."""
        import logging
        
        correlation_id = str(uuid.uuid4())
        correlation_id_context.set(correlation_id)
        
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.funcName = "test_function"
        record.module = "test_module"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["correlation_id"] == correlation_id
    
    def test_json_formatter_with_extra_fields(self):
        """Test JSON formatter includes extra fields."""
        import logging
        
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.funcName = "test_function"
        record.module = "test_module"
        record.extra_fields = {
            "operation": "test_op",
            "file_size": 1024,
            "custom_field": "value"
        }
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["operation"] == "test_op"
        assert log_data["file_size"] == 1024
        assert log_data["custom_field"] == "value"
    
    def test_setup_logging(self):
        """Test logging setup configuration."""
        logger = setup_logging()
        
        assert logger.name == "n8n-tools-api"
        assert len(logger.handlers) == 1
        
        # Test that handler uses JSON formatter
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, JSONFormatter)
    
    def test_log_pdf_operation(self):
        """Test PDF operation logging."""
        correlation_id = str(uuid.uuid4())
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_pdf_operation(
                operation="split",
                filename="test.pdf",
                file_size=1048576,  # 1MB
                pages=10,
                processing_time_ms=1500.5,
                output_files=5,
                correlation_id=correlation_id,
                custom_field="test_value"
            )
            
            # Verify logger was called with correct name
            mock_get_logger.assert_called_with("n8n-tools-api.pdf")
            
            # Verify logger.info was called
            mock_logger.info.assert_called_once()
            
            # Check the call arguments
            call_args = mock_logger.info.call_args
            message = call_args[0][0]
            extra_data = call_args[1]["extra"]["extra_fields"]
            
            assert "PDF Operation - split on test.pdf" in message
            assert extra_data["correlation_id"] == correlation_id
            assert extra_data["type"] == "pdf_operation"
            assert extra_data["operation"] == "split"
            assert extra_data["filename"] == "test.pdf"
            assert extra_data["file_size_bytes"] == 1048576
            assert extra_data["file_size_mb"] == 1.0
            assert extra_data["pages"] == 10
            assert extra_data["processing_time_ms"] == 1500.5
            assert extra_data["output_files"] == 5
            assert extra_data["custom_field"] == "test_value"
    
    def test_log_file_upload(self):
        """Test file upload logging."""
        correlation_id = str(uuid.uuid4())
        
        with patch('app.core.logging.app_logger') as mock_logger:
            log_file_upload(
                filename="upload.pdf",
                file_size=2097152,  # 2MB
                content_type="application/pdf",
                correlation_id=correlation_id
            )
            
            mock_logger.info.assert_called_once()
            
            call_args = mock_logger.info.call_args
            message = call_args[0][0]
            extra_data = call_args[1]["extra"]["extra_fields"]
            
            assert "File Upload - upload.pdf" in message
            assert extra_data["type"] == "file_upload"
            assert extra_data["filename"] == "upload.pdf"
            assert extra_data["file_size_bytes"] == 2097152
            assert extra_data["file_size_mb"] == 2.0
            assert extra_data["content_type"] == "application/pdf"
    
    def test_log_validation_result_success(self):
        """Test validation result logging for successful validation."""
        correlation_id = str(uuid.uuid4())
        
        with patch('app.core.logging.app_logger') as mock_logger:
            log_validation_result(
                filename="valid.pdf",
                is_valid=True,
                validation_time_ms=250.5,
                correlation_id=correlation_id
            )
            
            mock_logger.log.assert_called_once()
            
            call_args = mock_logger.log.call_args
            log_level = call_args[0][0]
            message = call_args[0][1]
            extra_data = call_args[1]["extra"]["extra_fields"]
            
            assert log_level == 20  # logging.INFO
            assert "Validation Success - valid.pdf" in message
            assert extra_data["is_valid"] is True
            assert extra_data["validation_time_ms"] == 250.5
    
    def test_log_validation_result_failure(self):
        """Test validation result logging for failed validation."""
        correlation_id = str(uuid.uuid4())
        
        with patch('app.core.logging.app_logger') as mock_logger:
            log_validation_result(
                filename="invalid.pdf",
                is_valid=False,
                error_message="Invalid PDF format",
                validation_time_ms=150.2,
                correlation_id=correlation_id
            )
            
            mock_logger.log.assert_called_once()
            
            call_args = mock_logger.log.call_args
            log_level = call_args[0][0]
            message = call_args[0][1]
            extra_data = call_args[1]["extra"]["extra_fields"]
            
            assert log_level == 30  # logging.WARNING
            assert "Validation Failed - invalid.pdf" in message
            assert extra_data["is_valid"] is False
            assert extra_data["error_message"] == "Invalid PDF format"
    
    def test_log_performance_metric(self):
        """Test performance metric logging."""
        correlation_id = str(uuid.uuid4())
        
        with patch('app.core.logging.app_logger') as mock_logger:
            log_performance_metric(
                metric_name="processing_time",
                value=1234.56,
                unit="ms",
                context={"operation": "split", "pages": 10},
                correlation_id=correlation_id
            )
            
            mock_logger.info.assert_called_once()
            
            call_args = mock_logger.info.call_args
            message = call_args[0][0]
            extra_data = call_args[1]["extra"]["extra_fields"]
            
            assert "Performance Metric - processing_time: 1234.56 ms" in message
            assert extra_data["type"] == "performance_metric"
            assert extra_data["metric_name"] == "processing_time"
            assert extra_data["value"] == 1234.56
            assert extra_data["unit"] == "ms"
            assert extra_data["context"]["operation"] == "split"
    
    def test_get_correlation_id(self):
        """Test correlation ID retrieval."""
        # Test when no correlation ID is set
        correlation_id_context.set(None)
        assert get_correlation_id() is None
        
        # Test when correlation ID is set
        test_id = str(uuid.uuid4())
        correlation_id_context.set(test_id)
        assert get_correlation_id() == test_id


class TestRequestLoggingMiddleware:
    """Test suite for request logging middleware."""
    
    def test_health_endpoint_logging(self):
        """Test that health endpoint requests are logged properly."""
        client = TestClient(app)
        
        # Capture log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setFormatter(JSONFormatter())
        
        # Get the middleware logger and add our handler
        middleware_logger = logging.getLogger("n8n-tools-api.middleware")
        middleware_logger.addHandler(handler)
        middleware_logger.setLevel(logging.INFO)
        
        try:
            # Make request
            response = client.get("/health")
            
            # Check response has correlation ID header
            assert "x-correlation-id" in response.headers
            assert "x-processing-time-ms" in response.headers
            
            # Check logs were generated
            log_output = log_capture.getvalue()
            log_lines = [line for line in log_output.strip().split('\n') if line]
            
            # Should have request and response logs
            assert len(log_lines) >= 2
            
            # Parse and validate request log
            request_log = json.loads(log_lines[0])
            assert request_log["type"] == "request"
            assert request_log["method"] == "GET"
            assert request_log["path"] == "/health"
            assert "correlation_id" in request_log
            
            # Parse and validate response log
            response_log = json.loads(log_lines[1])
            assert response_log["type"] == "response"
            assert response_log["status_code"] == 200
            assert "process_time_ms" in response_log
            assert response_log["correlation_id"] == request_log["correlation_id"]
            
        finally:
            middleware_logger.removeHandler(handler)


@pytest.mark.integration
class TestLoggingIntegration:
    """Integration tests for logging system."""
    
    def test_pdf_validation_endpoint_logging(self):
        """Test logging integration with PDF validation endpoint."""
        client = TestClient(app)
        
        # Create a minimal valid PDF content
        pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj xref 0 4 0000000000 65535 f 0000000010 00000 n 0000000053 00000 n 0000000100 00000 n trailer<</Size 4/Root 1 0 R>> startxref 155 %%EOF"
        
        # Create test file
        files = {"file": ("test.pdf", pdf_content, "application/pdf")}
        
        response = client.post("/api/v1/pdf/validate", files=files)
        
        # Should succeed
        assert response.status_code == 200
        
        # Should have correlation ID
        assert "x-correlation-id" in response.headers
        
        # Response should indicate validation success
        data = response.json()
        assert data["valid"] is True
        assert data["filename"] == "test.pdf"
    
    def test_request_correlation_across_logs(self):
        """Test that correlation IDs are consistent across all logs for a request."""
        client = TestClient(app)
        
        # Capture logs
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setFormatter(JSONFormatter())
        
        # Add handler to all relevant loggers
        loggers = [
            logging.getLogger("n8n-tools-api.middleware"),
            logging.getLogger("n8n-tools-api.upload"),
            logging.getLogger("n8n-tools-api.validation")
        ]
        
        for logger in loggers:
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        try:
            # Make request
            pdf_content = b"%PDF-1.4\nHello World\n%%EOF"
            files = {"file": ("test.pdf", pdf_content, "application/pdf")}
            
            response = client.post("/api/v1/pdf/validate", files=files)
            
            # Parse all log entries
            log_output = log_capture.getvalue()
            log_lines = [line for line in log_output.strip().split('\n') if line]
            
            correlation_ids = set()
            for line in log_lines:
                if line.strip():
                    log_entry = json.loads(line)
                    if "correlation_id" in log_entry:
                        correlation_ids.add(log_entry["correlation_id"])
            
            # All logs should have the same correlation ID
            assert len(correlation_ids) <= 1, f"Multiple correlation IDs found: {correlation_ids}"
            
            # Should match response header
            if correlation_ids:
                response_correlation_id = response.headers.get("x-correlation-id")
                assert list(correlation_ids)[0] == response_correlation_id
                
        finally:
            for logger in loggers:
                logger.removeHandler(handler)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
