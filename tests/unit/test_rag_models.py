"""
Unit tests for RAG Pydantic models.

Tests validation, serialization, and error handling for RAG operation models.
"""

import pytest
from pydantic import ValidationError
from app.models.rag_models import (
    CreateCollectionRequest,
    CollectionResponse,
    CollectionDetails,
    CollectionInfoResponse,
    VectorDistance,
    EmbeddingRequest,
    EmbeddingResponse,
    ErrorResponse
)

class TestCreateCollectionRequest:
    """Test cases for CreateCollectionRequest model."""
    
    def test_valid_request(self):
        """Test valid collection creation request."""
        data = {
            "mistral_api_key": "test-mistral-key-123",
            "qdrant_url": "https://qdrant.example.com:6333",
            "qdrant_api_key": "test-qdrant-key-456", 
            "collection_name": "test_collection_name"
        }
        
        request = CreateCollectionRequest(**data)
        
        assert request.mistral_api_key.get_secret_value() == "test-mistral-key-123"
        assert str(request.qdrant_url) == "https://qdrant.example.com:6333/"
        assert request.qdrant_api_key.get_secret_value() == "test-qdrant-key-456"
        assert request.collection_name == "test_collection_name"
        assert request.vector_size == 1024  # default
        assert request.distance_metric == VectorDistance.COSINE  # default
        assert request.force_recreate is False  # default
    
    def test_custom_vector_size_and_distance(self):
        """Test request with custom vector size and distance metric."""
        data = {
            "mistral_api_key": "test-key",
            "qdrant_url": "https://localhost:6333", 
            "qdrant_api_key": "test-key",
            "collection_name": "custom_collection",
            "vector_size": 512,
            "distance_metric": "euclidean"
        }
        
        request = CreateCollectionRequest(**data)
        
        assert request.vector_size == 512
        assert request.distance_metric == VectorDistance.EUCLIDEAN
    
    def test_valid_collection_names(self):
        """Test various valid collection name formats."""
        valid_names = [
            "simple_name",
            "collection-with-hyphens", 
            "Collection123",
            "test_collection_v2",
            "a",  # minimum length
            "a" * 255  # maximum length
        ]
        
        base_data = {
            "mistral_api_key": "test-key",
            "qdrant_url": "https://localhost:6333",
            "qdrant_api_key": "test-key"
        }
        
        for name in valid_names:
            data = {**base_data, "collection_name": name}
            request = CreateCollectionRequest(**data)
            assert request.collection_name == name
    
    def test_invalid_collection_names(self):
        """Test invalid collection name formats."""
        invalid_names = [
            "",  # empty string
            " ",  # whitespace only
            "collection with spaces",
            "collection@special",
            "collection.with.dots",
            "collection/with/slashes",
            "collection#with#hash",
            "a" * 256  # too long
        ]
        
        base_data = {
            "mistral_api_key": "test-key",
            "qdrant_url": "https://localhost:6333",
            "qdrant_api_key": "test-key"
        }
        
        for name in invalid_names:
            data = {**base_data, "collection_name": name}
            with pytest.raises(ValidationError) as exc_info:
                CreateCollectionRequest(**data)
            
            errors = exc_info.value.errors()
            assert any("collection_name" in str(error) for error in errors)
    
    def test_invalid_urls(self):
        """Test invalid Qdrant URL formats."""
        invalid_urls = [
            "not-a-url",
            "ftp://localhost:6333",  # wrong protocol
            "localhost:6333",  # missing protocol
            "",  # empty
            "qdrant://localhost"  # unsupported protocol
        ]
        
        base_data = {
            "mistral_api_key": "test-key",
            "qdrant_api_key": "test-key", 
            "collection_name": "test_collection"
        }
        
        for url in invalid_urls:
            data = {**base_data, "qdrant_url": url}
            with pytest.raises(ValidationError) as exc_info:
                CreateCollectionRequest(**data)
            
            errors = exc_info.value.errors()
            assert any("qdrant_url" in str(error) for error in errors)
    
    def test_vector_size_validation(self):
        """Test vector size validation boundaries."""
        base_data = {
            "mistral_api_key": "test-key",
            "qdrant_url": "https://localhost:6333",
            "qdrant_api_key": "test-key",
            "collection_name": "test_collection"
        }
        
        # Valid sizes
        valid_sizes = [1, 512, 1024, 4096]
        for size in valid_sizes:
            data = {**base_data, "vector_size": size}
            request = CreateCollectionRequest(**data)
            assert request.vector_size == size
        
        # Invalid sizes
        invalid_sizes = [0, -1, 4097, 10000]
        for size in invalid_sizes:
            data = {**base_data, "vector_size": size}
            with pytest.raises(ValidationError):
                CreateCollectionRequest(**data)
    
    def test_missing_required_fields(self):
        """Test validation when required fields are missing."""
        required_fields = [
            "mistral_api_key",
            "qdrant_url", 
            "qdrant_api_key",
            "collection_name"
        ]
        
        complete_data = {
            "mistral_api_key": "test-key",
            "qdrant_url": "https://localhost:6333",
            "qdrant_api_key": "test-key",
            "collection_name": "test_collection"
        }
        
        for field in required_fields:
            data = complete_data.copy()
            del data[field]
            
            with pytest.raises(ValidationError) as exc_info:
                CreateCollectionRequest(**data)
            
            errors = exc_info.value.errors()
            assert any(error["loc"] == (field,) for error in errors)

class TestCollectionResponse:
    """Test cases for CollectionResponse model."""
    
    def test_minimal_response(self):
        """Test minimal valid response."""
        data = {
            "status": "success",
            "collection_name": "test_collection",
            "message": "Collection created successfully"
        }
        
        response = CollectionResponse(**data)
        
        assert response.status == "success"
        assert response.collection_name == "test_collection" 
        assert response.message == "Collection created successfully"
        assert response.details is None
        assert response.processing_time_ms is None
        assert response.qdrant_response is None
    
    def test_complete_response(self):
        """Test response with all fields populated."""
        details_data = {
            "name": "test_collection",
            "vector_size": 1024,
            "distance_metric": "cosine",
            "points_count": 100,
            "indexed_vectors_count": 95,
            "storage_type": "memory"
        }
        
        data = {
            "status": "success",
            "collection_name": "test_collection",
            "message": "Collection created successfully",
            "details": details_data,
            "processing_time_ms": 250.5,
            "qdrant_response": {"result": True, "time": 0.025}
        }
        
        response = CollectionResponse(**data)
        
        assert response.details.name == "test_collection"
        assert response.details.vector_size == 1024
        assert response.details.points_count == 100
        assert response.processing_time_ms == 250.5
        assert response.qdrant_response["result"] is True

class TestCollectionDetails:
    """Test cases for CollectionDetails model."""
    
    def test_valid_details(self):
        """Test valid collection details."""
        data = {
            "name": "test_collection",
            "vector_size": 1024,
            "distance_metric": "cosine"
        }
        
        details = CollectionDetails(**data)
        
        assert details.name == "test_collection"
        assert details.vector_size == 1024
        assert details.distance_metric == "cosine"
        assert details.points_count is None  # optional field

class TestErrorResponse:
    """Test cases for ErrorResponse model."""
    
    def test_minimal_error(self):
        """Test minimal error response."""
        data = {
            "error": "ValidationError",
            "message": "Invalid input provided",
            "type": "validation_error"
        }
        
        error = ErrorResponse(**data)
        
        assert error.error == "ValidationError"
        assert error.message == "Invalid input provided"
        assert error.type == "validation_error"
        assert error.details is None
        assert error.collection_name is None
    
    def test_complete_error(self):
        """Test error response with all fields."""
        data = {
            "error": "QdrantConnectionError",
            "message": "Failed to connect to Qdrant server",
            "type": "connection_error",
            "details": {"timeout": 30, "retries": 3},
            "collection_name": "failed_collection"
        }
        
        error = ErrorResponse(**data)
        
        assert error.error == "QdrantConnectionError"
        assert error.details["timeout"] == 30
        assert error.collection_name == "failed_collection"

class TestEmbeddingModels:
    """Test cases for embedding-related models (future implementation)."""
    
    def test_embedding_request(self):
        """Test embedding request validation."""
        data = {
            "text": "This is a test text for embedding generation",
            "mistral_api_key": "test-key-123"
        }
        
        request = EmbeddingRequest(**data)
        
        assert request.text == "This is a test text for embedding generation"
        assert request.mistral_api_key.get_secret_value() == "test-key-123"
        assert request.model == "mistral-embed"  # default
    
    def test_embedding_request_validation(self):
        """Test embedding request field validation."""
        # Test empty text
        with pytest.raises(ValidationError):
            EmbeddingRequest(text="", mistral_api_key="test-key")
        
        # Test too long text
        with pytest.raises(ValidationError):
            EmbeddingRequest(text="x" * 8193, mistral_api_key="test-key")
    
    def test_embedding_response(self):
        """Test embedding response model."""
        data = {
            "status": "success",
            "embeddings": [0.1, 0.2, 0.3, -0.1],
            "model": "mistral-embed",
            "token_count": 10,
            "processing_time_ms": 100.5
        }
        
        response = EmbeddingResponse(**data)
        
        assert response.status == "success"
        assert len(response.embeddings) == 4
        assert response.embeddings[0] == 0.1
        assert response.model == "mistral-embed"
        assert response.token_count == 10
        assert response.processing_time_ms == 100.5

class TestEnumValidation:
    """Test cases for enum validation."""
    
    def test_vector_distance_enum(self):
        """Test VectorDistance enum validation."""
        # Valid values
        assert VectorDistance.COSINE == "cosine"
        assert VectorDistance.EUCLIDEAN == "euclidean" 
        assert VectorDistance.DOT == "dot"
        
        # Test in model
        data = {
            "mistral_api_key": "test-key",
            "qdrant_url": "https://localhost:6333",
            "qdrant_api_key": "test-key",
            "collection_name": "test_collection",
            "distance_metric": "dot"
        }
        
        request = CreateCollectionRequest(**data)
        assert request.distance_metric == VectorDistance.DOT
    
    def test_invalid_distance_metric(self):
        """Test invalid distance metric values."""
        data = {
            "mistral_api_key": "test-key",
            "qdrant_url": "https://localhost:6333", 
            "qdrant_api_key": "test-key",
            "collection_name": "test_collection",
            "distance_metric": "invalid_metric"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            CreateCollectionRequest(**data)
        
        errors = exc_info.value.errors()
        assert any("distance_metric" in str(error) for error in errors)

class TestModelSerialization:
    """Test model serialization and deserialization."""
    
    def test_request_to_dict(self):
        """Test serializing request model to dictionary."""
        data = {
            "mistral_api_key": "test-key",
            "qdrant_url": "https://localhost:6333",
            "qdrant_api_key": "test-key", 
            "collection_name": "test_collection"
        }
        
        request = CreateCollectionRequest(**data)
        serialized = request.dict()
        
        # SecretStr fields should be included but masked as stars
        assert "mistral_api_key" in serialized
        assert "qdrant_api_key" in serialized
        assert str(serialized["mistral_api_key"]) == "**********"
        assert str(serialized["qdrant_api_key"]) == "**********"
        assert serialized["collection_name"] == "test_collection"
        assert serialized["vector_size"] == 1024
    
    def test_response_to_json(self):
        """Test serializing response model to JSON."""
        data = {
            "status": "success", 
            "collection_name": "test_collection",
            "message": "Created successfully",
            "processing_time_ms": 150.5
        }
        
        response = CollectionResponse(**data)
        json_str = response.json()
        
        assert "success" in json_str
        assert "test_collection" in json_str
        assert "150.5" in json_str
