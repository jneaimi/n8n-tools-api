"""
Tests for PDF API routes.

Basic tests to validate the FastAPI application structure and endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "n8n-tools-api"
    assert data["version"] == "0.1.0"

def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "N8N Tools API"
    assert data["version"] == "0.1.0"
    assert "/docs" in data["docs"]
    assert "/health" in data["health"]

def test_pdf_service_status():
    """Test PDF service status endpoint."""
    response = client.get("/api/v1/pdf/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "PDF Operations"
    assert data["status"] == "ready"
    assert len(data["operations"]) > 0

def test_pdf_split_placeholder():
    """Test PDF split legacy endpoint."""
    response = client.post("/api/v1/pdf/split")
    assert response.status_code == 200  # Now returns info about new endpoints
    data = response.json()
    assert "use /split/ranges or /split/pages" in data["message"]
    assert "endpoints" in data
    assert "/split/ranges" in data["endpoints"]
    assert "/split/pages" in data["endpoints"]

def test_pdf_merge_placeholder():
    """Test PDF merge placeholder endpoint."""
    response = client.post("/api/v1/pdf/merge")
    assert response.status_code == 501  # Not implemented yet
    data = response.json()
    assert "coming soon" in data["message"]

def test_openapi_docs():
    """Test that OpenAPI docs are available."""
    response = client.get("/docs")
    assert response.status_code == 200
    
def test_openapi_schema():
    """Test that OpenAPI schema is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "N8N Tools API"
