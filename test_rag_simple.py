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
    print("✅ RAG service status test passed")


def test_rag_health_check():
    """Test RAG health check endpoint."""
    response = client.get("/api/v1/rag-operations/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "rag-operations"
    print("✅ RAG health check test passed")


def test_create_collection_missing_fields():
    """Test create collection endpoint with missing fields."""
    response = client.post("/api/v1/rag-operations/create-collection", json={})
    assert response.status_code == 422  # Validation error
    print("✅ Create collection validation test passed")


if __name__ == "__main__":
    # Run basic tests
    test_rag_service_status()
    test_rag_health_check()
    test_create_collection_missing_fields()
    print("✅ All basic endpoint tests passed!")
