"""
Basic test for RAG operations endpoint.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_rag_service_status():
    """Test RAG service status endpoint."""
    response = client.get("/api/v1/rag-operations/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "RAG Operations"
    assert data["status"] == "ready"


def test_rag_health_check():
    """Test RAG health check endpoint."""
    response = client.get("/api/v1/rag-operations/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "rag-operations"


def test_create_collection_validation():
    """Test create collection endpoint validation."""
    # Test with missing required fields
    response = client.post("/api/v1/rag-operations/create-collection", json={})
    assert response.status_code == 422  # Validation error
    
    # Test with invalid collection name
    invalid_request = {
        "mistral_api_key": "test-key",
        "qdrant_url": "https://test.qdrant.com",
        "qdrant_api_key": "test-qdrant-key", 
        "collection_name": "invalid name with spaces"
    }
    response = client.post("/api/v1/rag-operations/create-collection", json=invalid_request)
    assert response.status_code == 422  # Validation error


def test_test_connection_validation():
    """Test connection test endpoint validation."""
    # Test with missing required fields
    response = client.post("/api/v1/rag-operations/test-connection", json={})
    assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    # Run basic tests
    test_rag_service_status()
    test_rag_health_check()
    test_create_collection_validation()
    test_test_connection_validation()
    print("✅ All basic tests passed!")
