"""
Pydantic models for RAG (Retrieval-Augmented Generation) operations.

Defines request and response models for RAG-related API endpoints including
Qdrant collection management and Mistral embedding operations.
"""

from pydantic import BaseModel, Field, validator, HttpUrl, SecretStr
from typing import Dict, Any, Optional, List
from enum import Enum
import re

class VectorDistance(str, Enum):
    """Supported vector distance metrics for Qdrant collections."""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT = "dot"

class CreateCollectionRequest(BaseModel):
    """Request model for creating a Qdrant collection optimized for Mistral embeddings."""
    
    mistral_api_key: SecretStr = Field(
        ...,
        description="Mistral AI API key for authentication and validation",
        example="your-mistral-api-key-here-at-least-32-chars-long"
    )
    
    qdrant_url: HttpUrl = Field(
        ...,
        description="Qdrant server URL (including protocol and port if needed)",
        example="https://your-qdrant-instance.com:6333"
    )
    
    qdrant_api_key: SecretStr = Field(
        ...,
        description="Qdrant API key for authentication",
        example="your-qdrant-api-key-here-secure-string"
    )
    
    collection_name: str = Field(
        ...,
        description="Name for the new Qdrant collection (alphanumeric, underscores, hyphens only)",
        min_length=1,
        max_length=255,
        example="mistral_embeddings_collection"
    )
    
    vector_size: Optional[int] = Field(
        1024,
        description="Vector dimensions for embeddings (default: 1024 for Mistral)",
        ge=1,
        le=4096,
        example=1024
    )
    
    distance_metric: Optional[VectorDistance] = Field(
        VectorDistance.COSINE,
        description="Distance metric for vector similarity (default: cosine)",
        example="cosine"
    )
    
    force_recreate: Optional[bool] = Field(
        False,
        description="Whether to delete and recreate collection if it already exists",
        example=False
    )
    
    class Config:
        """Pydantic configuration for enhanced OpenAPI documentation."""
        json_schema_extra = {
            "examples": [
                {
                    "summary": "Basic Mistral collection",
                    "description": "Standard collection for Mistral embeddings with default settings",
                    "value": {
                        "mistral_api_key": "your-mistral-api-key-here-at-least-32-chars-long",
                        "qdrant_url": "https://your-qdrant-instance.com:6333",
                        "qdrant_api_key": "your-qdrant-api-key-here-secure-string",
                        "collection_name": "mistral_embeddings_default",
                        "vector_size": 1024,
                        "distance_metric": "cosine",
                        "force_recreate": False
                    }
                },
                {
                    "summary": "Custom dimensions collection",
                    "description": "Collection with custom vector dimensions and euclidean distance",
                    "value": {
                        "mistral_api_key": "your-mistral-api-key-here-at-least-32-chars-long",
                        "qdrant_url": "https://your-qdrant-instance.com:6333",
                        "qdrant_api_key": "your-qdrant-api-key-here-secure-string",
                        "collection_name": "custom_embeddings_512",
                        "vector_size": 512,
                        "distance_metric": "euclidean",
                        "force_recreate": False
                    }
                },
                {
                    "summary": "Force recreate existing collection",
                    "description": "Overwrite existing collection with new configuration",
                    "value": {
                        "mistral_api_key": "your-mistral-api-key-here-at-least-32-chars-long",
                        "qdrant_url": "https://your-qdrant-instance.com:6333",
                        "qdrant_api_key": "your-qdrant-api-key-here-secure-string",
                        "collection_name": "existing_collection_name",
                        "vector_size": 1024,
                        "distance_metric": "cosine",
                        "force_recreate": True
                    }
                }
            ]
        }
    
    @validator('collection_name')
    def validate_collection_name(cls, v):
        """Validate collection name format."""
        # Qdrant collection names should be alphanumeric with underscores and hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "Collection name must contain only alphanumeric characters, underscores, and hyphens"
            )
        return v.strip()
    
    @validator('qdrant_url')
    def validate_qdrant_url(cls, v):
        """Validate Qdrant URL format."""
        url_str = str(v)
        if not url_str.startswith(('http://', 'https://')):
            raise ValueError("Qdrant URL must use HTTP or HTTPS scheme")
        return v

class CollectionDetails(BaseModel):
    """Detailed information about a created collection."""
    
    name: str = Field(..., description="Collection name")
    vector_size: int = Field(..., description="Vector dimensions")
    distance_metric: str = Field(..., description="Distance metric used")
    points_count: Optional[int] = Field(None, description="Number of vectors in collection")
    indexed_vectors_count: Optional[int] = Field(None, description="Number of indexed vectors")
    storage_type: Optional[str] = Field(None, description="Storage type (memory/disk)")
    config: Optional[Dict[str, Any]] = Field(None, description="Collection configuration details")

class CollectionResponse(BaseModel):
    """Response model for collection creation operations."""
    
    status: str = Field(
        ..., 
        description="Operation status (success/error)",
        example="success"
    )
    
    collection_name: str = Field(
        ..., 
        description="Name of the created/affected collection",
        example="mistral_embeddings_collection"
    )
    
    message: str = Field(
        ..., 
        description="Human-readable message about the operation",
        example="Collection created successfully with Mistral embedding configuration"
    )
    
    details: Optional[CollectionDetails] = Field(
        None, 
        description="Detailed information about the collection"
    )
    
    processing_time_ms: Optional[float] = Field(
        None, 
        description="Processing time in milliseconds",
        example=150.5
    )
    
    qdrant_response: Optional[Dict[str, Any]] = Field(
        None,
        description="Raw response from Qdrant server (for debugging)"
    )

class CollectionInfoResponse(BaseModel):
    """Response model for collection information queries."""
    
    status: str = Field(..., description="Operation status")
    exists: bool = Field(..., description="Whether the collection exists")
    details: Optional[CollectionDetails] = Field(None, description="Collection details if exists")
    message: str = Field(..., description="Status message")

class ErrorResponse(BaseModel):
    """Standard error response model for RAG operations."""
    
    error: str = Field(
        ..., 
        description="Error type/category",
        example="ValidationError"
    )
    
    message: str = Field(
        ..., 
        description="Human-readable error message",
        example="Invalid collection name format"
    )
    
    type: str = Field(
        ..., 
        description="Error category for programmatic handling",
        example="validation_error"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional error context and debugging information"
    )
    
    collection_name: Optional[str] = Field(
        None,
        description="Collection name that caused the error (if applicable)"
    )

# Additional models for future RAG operations

class EmbeddingRequest(BaseModel):
    """Request model for generating embeddings (future implementation)."""
    
    text: str = Field(
        ...,
        description="Text to generate embeddings for",
        min_length=1,
        max_length=8192
    )
    
    mistral_api_key: SecretStr = Field(
        ...,
        description="Mistral AI API key"
    )
    
    model: Optional[str] = Field(
        "mistral-embed",
        description="Mistral embedding model to use"
    )

class EmbeddingResponse(BaseModel):
    """Response model for embedding generation (future implementation)."""
    
    status: str = Field(..., description="Operation status")
    embeddings: List[float] = Field(..., description="Generated embedding vector")
    model: str = Field(..., description="Model used for embedding generation")
    token_count: Optional[int] = Field(None, description="Number of tokens processed")
    processing_time_ms: Optional[float] = Field(None, description="Processing time")
