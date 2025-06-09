"""
Comprehensive integration tests for PDF API endpoints.

Tests complete API functionality including request/response handling,
file uploads, error scenarios, and API documentation.
"""

import pytest
import io
import zipfile
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestPDFEndpoints:
    """Integration tests for PDF manipulation endpoints."""
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "n8n-tools-api"
        assert "version" in data
        assert "timestamp" in data
    
    def test_root_endpoint_information(self, client):
        """Test root endpoint provides API information."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "N8N Tools API"
        assert "version" in data
        assert "docs" in data
        assert "health" in data
        assert "/docs" in data["docs"]
        assert "/health" in data["health"]
    
    def test_pdf_service_status_endpoint(self, client):
        """Test PDF service status endpoint."""
        response = client.get("/api/v1/pdf/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "PDF Operations"
        assert data["status"] == "ready"
        assert "operations" in data
        assert len(data["operations"]) > 0
        assert "version" in data
    
    def test_pdf_info_endpoint_valid_file(self, client, valid_pdf_upload_file):
        """Test PDF info endpoint with valid file."""
        filename, file_obj, content_type = valid_pdf_upload_file
        
        response = client.post(
            "/api/v1/pdf/info",
            files={"file": (filename, file_obj, content_type)}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required metadata fields
        assert "page_count" in data
        assert "file_size_bytes" in data
        assert "file_size_mb" in data
        assert "encrypted" in data
        assert "filename" in data
        
        # Validate data types
        assert isinstance(data["page_count"], int)
        assert isinstance(data["file_size_bytes"], int)
        assert isinstance(data["file_size_mb"], float)
        assert isinstance(data["encrypted"], bool)
        assert data["page_count"] > 0
    
    def test_pdf_info_endpoint_invalid_file(self, client, invalid_pdf_upload_file):
        """Test PDF info endpoint with invalid file."""
        filename, file_obj, content_type = invalid_pdf_upload_file
        
        response = client.post(
            "/api/v1/pdf/info",
            files={"file": (filename, file_obj, content_type)}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "Invalid PDF" in data["error"] or "Failed to process" in data["error"]
    
    def test_pdf_split_ranges_endpoint(self, client, valid_pdf_upload_file):
        """Test PDF split by ranges endpoint."""
        filename, file_obj, content_type = valid_pdf_upload_file
        
        response = client.post(
            "/api/v1/pdf/split/ranges",
            files={"file": (filename, file_obj, content_type)},
            data={"ranges": "1,2-3"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        
        # Verify ZIP content
        zip_content = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_content, 'r') as zip_file:
            files = zip_file.namelist()
            assert len(files) == 2  # Two ranges: "1" and "2-3"
            assert all(f.endswith('.pdf') for f in files)
    
    def test_pdf_split_ranges_invalid_range(self, client, valid_pdf_upload_file):
        """Test PDF split with invalid page ranges."""
        filename, file_obj, content_type = valid_pdf_upload_file
        
        response = client.post(
            "/api/v1/pdf/split/ranges",
            files={"file": (filename, file_obj, content_type)},
            data={"ranges": "10-20"}  # Assuming PDF has fewer than 10 pages
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "out of range" in data["error"]
    
    def test_pdf_split_pages_endpoint(self, client, valid_pdf_upload_file):
        """Test PDF split into individual pages endpoint."""
        filename, file_obj, content_type = valid_pdf_upload_file
        
        response = client.post(
            "/api/v1/pdf/split/pages",
            files={"file": (filename, file_obj, content_type)}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        
        # Verify ZIP content
        zip_content = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_content, 'r') as zip_file:
            files = zip_file.namelist()
            assert len(files) > 0  # Should have at least one page
            assert all(f.endswith('.pdf') for f in files)
            assert all('page_' in f for f in files)
    
    def test_pdf_split_batch_endpoint(self, client, valid_multipage_pdf_bytes):
        """Test PDF batch split endpoint."""
        file_obj = io.BytesIO(valid_multipage_pdf_bytes)
        
        response = client.post(
            "/api/v1/pdf/split/batch",
            files={"file": ("multipage.pdf", file_obj, "application/pdf")},
            data={"batch_size": "3"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        
        # Verify ZIP content
        zip_content = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_content, 'r') as zip_file:
            files = zip_file.namelist()
            assert len(files) > 0
            assert all(f.endswith('.pdf') for f in files)
            assert all('batch_' in f for f in files)
    
    def test_pdf_split_batch_invalid_size(self, client, valid_pdf_upload_file):
        """Test PDF batch split with invalid batch size."""
        filename, file_obj, content_type = valid_pdf_upload_file
        
        response = client.post(
            "/api/v1/pdf/split/batch",
            files={"file": (filename, file_obj, content_type)},
            data={"batch_size": "0"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "positive" in data["error"]
    
    def test_pdf_merge_endpoint(self, client, valid_pdf_bytes, valid_multipage_pdf_bytes):
        """Test PDF merge endpoint."""
        file1 = io.BytesIO(valid_pdf_bytes)
        file2 = io.BytesIO(valid_multipage_pdf_bytes)
        
        response = client.post(
            "/api/v1/pdf/merge",
            files=[
                ("files", ("file1.pdf", file1, "application/pdf")),
                ("files", ("file2.pdf", file2, "application/pdf"))
            ]
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        
        # Verify merged PDF is valid
        merged_content = response.content
        assert len(merged_content) > 0
        assert merged_content.startswith(b'%PDF')
    
    def test_pdf_merge_single_file(self, client, valid_pdf_upload_file):
        """Test PDF merge with single file."""
        filename, file_obj, content_type = valid_pdf_upload_file
        
        response = client.post(
            "/api/v1/pdf/merge",
            files=[("files", (filename, file_obj, content_type))]
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
    
    def test_pdf_merge_no_files(self, client):
        """Test PDF merge with no files."""
        response = client.post("/api/v1/pdf/merge")
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "No files" in data["error"]
    
    def test_file_upload_validation_wrong_type(self, client):
        """Test file upload validation with wrong file type."""
        text_content = b"This is a text file, not a PDF"
        
        response = client.post(
            "/api/v1/pdf/info",
            files={"file": ("test.txt", io.BytesIO(text_content), "text/plain")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    def test_file_upload_validation_no_file(self, client):
        """Test endpoints without file upload."""
        response = client.post("/api/v1/pdf/info")
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
    
    def test_file_upload_validation_empty_file(self, client):
        """Test file upload validation with empty file."""
        response = client.post(
            "/api/v1/pdf/info",
            files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "empty" in data["error"].lower()
    
    def test_concurrent_requests(self, client, valid_pdf_upload_file):
        """Test handling of concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            filename, file_obj, content_type = valid_pdf_upload_file
            # Create a fresh BytesIO for each thread
            fresh_file_obj = io.BytesIO(file_obj.getvalue())
            
            response = client.post(
                "/api/v1/pdf/info",
                files={"file": (filename, fresh_file_obj, content_type)}
            )
            results.append(response.status_code)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 5


@pytest.mark.integration
class TestAPIDocumentation:
    """Test API documentation and OpenAPI schema."""
    
    def test_openapi_docs_available(self, client):
        """Test that OpenAPI docs are accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_openapi_json_schema(self, client):
        """Test OpenAPI JSON schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert schema["info"]["title"] == "N8N Tools API"
        assert "paths" in schema
        assert "components" in schema
        
        # Check that key endpoints are documented
        paths = schema["paths"]
        assert "/health" in paths
        assert "/api/v1/pdf/info" in paths
        assert "/api/v1/pdf/split/ranges" in paths
        assert "/api/v1/pdf/split/pages" in paths
        assert "/api/v1/pdf/split/batch" in paths
        assert "/api/v1/pdf/merge" in paths
    
    def test_openapi_schema_validation(self, client):
        """Test that OpenAPI schema is valid for n8n integration."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Check n8n-compatible features
        assert "servers" in schema
        assert len(schema["servers"]) > 0
        
        # Check that all endpoints have proper operation IDs
        for path, methods in schema["paths"].items():
            for method, operation in methods.items():
                if method in ["get", "post", "put", "delete"]:
                    assert "operationId" in operation
                    assert "summary" in operation
                    assert "responses" in operation
    
    def test_redoc_documentation(self, client):
        """Test ReDoc documentation availability."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


@pytest.mark.integration
class TestErrorHandling:
    """Integration tests for error handling across the API."""
    
    def test_404_error_handling(self, client):
        """Test 404 error handling for non-existent endpoints."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
    
    def test_method_not_allowed_error(self, client):
        """Test 405 error handling for unsupported HTTP methods."""
        response = client.delete("/api/v1/pdf/info")
        assert response.status_code == 405
        
        data = response.json()
        assert "detail" in data
    
    def test_cors_headers(self, client):
        """Test CORS headers are properly set."""
        response = client.options("/api/v1/pdf/info")
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
    
    def test_request_validation_error(self, client):
        """Test request validation error handling."""
        # Send invalid form data
        response = client.post(
            "/api/v1/pdf/split/ranges",
            data={"invalid_field": "value"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_large_file_upload_error(self, client):
        """Test error handling for files exceeding size limit."""
        # Create a very large fake PDF (assuming 50MB limit)
        large_content = b"%PDF-1.4\n" + b"x" * (51 * 1024 * 1024)
        
        response = client.post(
            "/api/v1/pdf/info",
            files={"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")}
        )
        
        # Should either be 413 (Request Entity Too Large) or 400 (Bad Request)
        assert response.status_code in [400, 413]
        
        if response.status_code == 400:
            data = response.json()
            assert "error" in data
            assert "large" in data["error"].lower() or "size" in data["error"].lower()


@pytest.mark.integration 
class TestResponseFormats:
    """Test API response formats and headers."""
    
    def test_json_response_format(self, client, valid_pdf_upload_file):
        """Test JSON response format consistency."""
        filename, file_obj, content_type = valid_pdf_upload_file
        
        response = client.post(
            "/api/v1/pdf/info",
            files={"file": (filename, file_obj, content_type)}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        # Should have consistent timestamp format
        if "timestamp" in data:
            assert isinstance(data["timestamp"], str)
    
    def test_zip_response_format(self, client, valid_pdf_upload_file):
        """Test ZIP response format for split operations."""
        filename, file_obj, content_type = valid_pdf_upload_file
        
        response = client.post(
            "/api/v1/pdf/split/pages",
            files={"file": (filename, file_obj, content_type)}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
    
    def test_pdf_response_format(self, client, valid_pdf_bytes):
        """Test PDF response format for merge operations."""
        file_obj = io.BytesIO(valid_pdf_bytes)
        
        response = client.post(
            "/api/v1/pdf/merge",
            files=[("files", ("test.pdf", file_obj, "application/pdf"))]
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
    
    def test_error_response_format(self, client, invalid_pdf_upload_file):
        """Test error response format consistency."""
        filename, file_obj, content_type = invalid_pdf_upload_file
        
        response = client.post(
            "/api/v1/pdf/info",
            files={"file": (filename, file_obj, content_type)}
        )
        
        assert response.status_code == 400
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert "error" in data
        assert "timestamp" in data
        assert isinstance(data["error"], str)
        assert isinstance(data["timestamp"], str)


@pytest.mark.integration
@pytest.mark.slow
class TestPerformance:
    """Performance tests for API endpoints."""
    
    def test_multiple_file_processing_performance(self, client, valid_pdf_bytes):
        """Test performance with multiple file processing requests."""
        import time
        
        start_time = time.time()
        
        # Process multiple files
        for i in range(10):
            file_obj = io.BytesIO(valid_pdf_bytes)
            response = client.post(
                "/api/v1/pdf/info",
                files={"file": (f"test_{i}.pdf", file_obj, "application/pdf")}
            )
            assert response.status_code == 200
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should process 10 files in reasonable time (adjust threshold as needed)
        assert total_time < 30  # 30 seconds max for 10 files
        
        # Average processing time per file
        avg_time = total_time / 10
        assert avg_time < 3  # 3 seconds max per file
    
    def test_large_file_processing_performance(self, client, large_pdf_bytes):
        """Test performance with large file processing."""
        import time
        
        file_obj = io.BytesIO(large_pdf_bytes)
        
        start_time = time.time()
        response = client.post(
            "/api/v1/pdf/info",
            files={"file": ("large.pdf", file_obj, "application/pdf")}
        )
        end_time = time.time()
        
        assert response.status_code == 200
        
        processing_time = end_time - start_time
        # Large file should still process within reasonable time
        assert processing_time < 10  # 10 seconds max for large file
    
    def test_concurrent_processing_performance(self, client, valid_pdf_bytes):
        """Test performance under concurrent load."""
        import threading
        import time
        
        results = []
        
        def process_file():
            file_obj = io.BytesIO(valid_pdf_bytes)
            start = time.time()
            response = client.post(
                "/api/v1/pdf/info",
                files={"file": ("test.pdf", file_obj, "application/pdf")}
            )
            end = time.time()
            results.append({
                "status_code": response.status_code,
                "processing_time": end - start
            })
        
        # Start 10 concurrent requests
        threads = []
        start_time = time.time()
        
        for _ in range(10):
            thread = threading.Thread(target=process_file)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All requests should succeed
        assert all(r["status_code"] == 200 for r in results)
        assert len(results) == 10
        
        # Concurrent processing should not take much longer than sequential
        avg_processing_time = sum(r["processing_time"] for r in results) / len(results)
        assert total_time < avg_processing_time * 5  # Allow some overhead for concurrency
