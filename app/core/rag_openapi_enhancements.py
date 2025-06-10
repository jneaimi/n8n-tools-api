"""
Enhanced OpenAPI specification for RAG API endpoints.

This module provides additional OpenAPI documentation and examples
for RAG (Retrieval-Augmented Generation) operations beyond the auto-generated FastAPI documentation.
"""

from typing import Dict, Any

def get_rag_openapi_examples() -> Dict[str, Any]:
    """
    Get enhanced OpenAPI examples for RAG endpoints.
    
    Returns comprehensive examples for n8n integration and API testing.
    """
    return {
        "rag_collection_creation_examples": {
            "basic_mistral_collection": {
                "summary": "Basic Mistral collection creation",
                "description": "Example for n8n: Create standard Mistral embedding collection",
                "value": {
                    "mistral_api_key": "your-mistral-api-key-here-at-least-32-chars-long",
                    "qdrant_url": "https://your-qdrant-instance.com:6333",
                    "qdrant_api_key": "your-qdrant-api-key-here-secure-string",
                    "collection_name": "mistral_embeddings_prod",
                    "vector_size": 1024,
                    "distance_metric": "cosine",
                    "force_recreate": False
                }
            },
            "custom_dimensions_collection": {
                "summary": "Custom vector dimensions",
                "description": "Example for n8n: Collection with custom vector size and euclidean distance",
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
            "force_recreate_collection": {
                "summary": "Force recreate existing collection",
                "description": "Example for n8n: Overwrite existing collection with new settings",
                "value": {
                    "mistral_api_key": "your-mistral-api-key-here-at-least-32-chars-long",
                    "qdrant_url": "https://your-qdrant-instance.com:6333",
                    "qdrant_api_key": "your-qdrant-api-key-here-secure-string",
                    "collection_name": "existing_collection_to_recreate",
                    "vector_size": 1024,
                    "distance_metric": "dot",
                    "force_recreate": True
                }
            }
        },
        "rag_connection_testing_examples": {
            "basic_connection_test": {
                "summary": "Basic connection test",
                "description": "Example for n8n: Test Qdrant and Mistral connectivity",
                "value": {
                    "mistral_api_key": "your-mistral-api-key-here-at-least-32-chars-long",
                    "qdrant_url": "https://your-qdrant-instance.com:6333",
                    "qdrant_api_key": "your-qdrant-api-key-here-secure-string",
                    "collection_name": "test_connection_check"
                }
            }
        },
        "rag_response_examples": {
            "successful_collection_creation": {
                "summary": "Successful collection creation",
                "description": "Complete response when collection is created successfully",
                "value": {
                    "status": "success",
                    "collection_name": "mistral_embeddings_prod",
                    "message": "Collection 'mistral_embeddings_prod' created successfully with Mistral embedding configuration",
                    "details": {
                        "name": "mistral_embeddings_prod",
                        "vector_size": 1024,
                        "distance_metric": "cosine",
                        "points_count": 0,
                        "indexed_vectors_count": 0,
                        "storage_type": "memory",
                        "config": {
                            "hnsw_config": {
                                "m": 16,
                                "ef_construct": 100,
                                "full_scan_threshold": 10000
                            },
                            "optimizer_config": {
                                "max_segment_size": 20000,
                                "memmap_threshold": 50000
                            }
                        }
                    },
                    "processing_time_ms": 247.3,
                    "qdrant_response": {
                        "result": True,
                        "status": "acknowledged",
                        "time": 0.247
                    }
                }
            },
            "successful_connection_test": {
                "summary": "Successful connection test",
                "description": "Response when connection test passes",
                "value": {
                    "status": "success",
                    "message": "Successfully connected to Qdrant server",
                    "qdrant_url": "https://your-qdrant-instance.com:6333",
                    "connection_validated": True,
                    "client_type": "http_client"
                }
            }
        },
        "rag_error_examples": {
            "invalid_api_key_format": {
                "summary": "Invalid Mistral API key format",
                "description": "Error when API key doesn't meet format requirements",
                "value": {
                    "status": "error",
                    "error_code": "INVALID_API_KEY_FORMAT",
                    "message": "Invalid Mistral API key format",
                    "details": {
                        "requirements": [
                            "Minimum 32 characters",
                            "Alphanumeric characters, hyphens, underscores, and dots only"
                        ]
                    }
                }
            },
            "invalid_mistral_key": {
                "summary": "Invalid Mistral API key",
                "description": "Error when Mistral API key is not valid",
                "value": {
                    "status": "error",
                    "error_code": "INVALID_API_KEY",
                    "message": "Invalid Mistral AI API key",
                    "details": {
                        "help": "Ensure you're using a valid Mistral AI API key"
                    }
                }
            },
            "collection_already_exists": {
                "summary": "Collection already exists",
                "description": "Error when collection exists and force_recreate is false",
                "value": {
                    "error": "CollectionExistsError",
                    "message": "Collection 'existing_collection' already exists in Qdrant",
                    "collection_name": "existing_collection",
                    "suggestion": "Use force_recreate=true to overwrite existing collection"
                }
            },
            "qdrant_connection_error": {
                "summary": "Qdrant connection error",
                "description": "Error when unable to connect to Qdrant server",
                "value": {
                    "error": "ConnectionError",
                    "message": "Failed to connect to Qdrant server",
                    "qdrant_url": "https://your-qdrant-instance.com:6333",
                    "details": "Connection timeout after 30 seconds"
                }
            },
            "rate_limit_exceeded": {
                "summary": "Rate limit exceeded",
                "description": "Error when API request rate limit is exceeded",
                "value": {
                    "status": "error",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": "Rate limit exceeded",
                    "details": {
                        "limit": "100 requests per 60 seconds",
                        "retry_after": 60
                    }
                }
            }
        }
    }

def get_rag_openapi_schemas() -> Dict[str, Any]:
    """
    Get enhanced OpenAPI schemas for RAG models.
    
    Returns additional schema definitions and examples for better documentation.
    """
    return {
        "RAGServiceStatus": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "example": "RAG Operations"},
                "status": {"type": "string", "example": "ready"},
                "operations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "example": [
                        "create-collection - Create Qdrant collections for Mistral embeddings",
                        "test-connection - Test Qdrant server connectivity"
                    ]
                },
                "supported_embedding_models": {
                    "type": "array",
                    "items": {"type": "string"},
                    "example": ["mistral-embed"]
                },
                "vector_database": {"type": "string", "example": "Qdrant"},
                "default_vector_size": {"type": "integer", "example": 1024},
                "default_distance_metric": {"type": "string", "example": "cosine"}
            },
            "example": {
                "service": "RAG Operations",
                "status": "ready",
                "operations": [
                    "create-collection - Create Qdrant collections for Mistral embeddings",
                    "test-connection - Test Qdrant server connectivity",
                    "list-collections - List existing collections",
                    "get-collection-info - Get detailed collection information"
                ],
                "supported_embedding_models": ["mistral-embed"],
                "vector_database": "Qdrant",
                "default_vector_size": 1024,
                "default_distance_metric": "cosine"
            }
        },
        "RAGHealthStatus": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "example": "healthy"},
                "service": {"type": "string", "example": "rag-operations"},
                "version": {"type": "string", "example": "1.0.0"},
                "timestamp": {"type": "string", "example": "2024-06-10T18:30:45Z"},
                "capabilities": {
                    "type": "object",
                    "properties": {
                        "qdrant_integration": {"type": "boolean", "example": True},
                        "mistral_embeddings": {"type": "boolean", "example": True},
                        "collection_management": {"type": "boolean", "example": True},
                        "connection_validation": {"type": "boolean", "example": True}
                    }
                },
                "supported_operations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "example": ["collection_creation", "connection_testing"]
                },
                "vector_config": {
                    "type": "object",
                    "properties": {
                        "default_dimensions": {"type": "integer", "example": 1024},
                        "supported_distances": {
                            "type": "array",
                            "items": {"type": "string"},
                            "example": ["cosine", "euclidean", "dot"]
                        },
                        "optimization": {"type": "string", "example": "hnsw"}
                    }
                }
            },
            "example": {
                "status": "healthy",
                "service": "rag-operations",
                "version": "1.0.0",
                "timestamp": "2024-06-10T18:30:45Z",
                "capabilities": {
                    "qdrant_integration": True,
                    "mistral_embeddings": True,
                    "collection_management": True,
                    "connection_validation": True
                },
                "supported_operations": [
                    "collection_creation",
                    "connection_testing",
                    "collection_listing",
                    "collection_info_retrieval"
                ],
                "vector_config": {
                    "default_dimensions": 1024,
                    "supported_distances": ["cosine", "euclidean", "dot"],
                    "optimization": "hnsw"
                }
            }
        }
    }

def get_rag_n8n_integration_examples() -> Dict[str, Any]:
    """
    Get n8n-specific integration examples and workflow snippets.
    
    Returns examples optimized for n8n HTTP Request nodes and workflow automation.
    """
    return {
        "n8n_workflow_examples": {
            "create_collection_workflow": {
                "summary": "n8n Workflow: Create Qdrant Collection",
                "description": "Complete n8n workflow for creating and validating Qdrant collections",
                "workflow_steps": [
                    {
                        "step": 1,
                        "node_type": "HTTP Request",
                        "operation": "Test Connection",
                        "url": "{{$node[\"Set Variables\"].json[\"api_base_url\"]}}/api/v1/rag-operations/test-connection",
                        "method": "POST",
                        "body": {
                            "mistral_api_key": "{{$node[\"Set Variables\"].json[\"mistral_key\"]}}",
                            "qdrant_url": "{{$node[\"Set Variables\"].json[\"qdrant_url\"]}}",
                            "qdrant_api_key": "{{$node[\"Set Variables\"].json[\"qdrant_key\"]}}",
                            "collection_name": "test_connection"
                        }
                    },
                    {
                        "step": 2,
                        "node_type": "HTTP Request",
                        "operation": "Create Collection",
                        "url": "{{$node[\"Set Variables\"].json[\"api_base_url\"]}}/api/v1/rag-operations/create-collection",
                        "method": "POST",
                        "condition": "{{$node[\"Test Connection\"].json[\"status\"] === \"success\"}}",
                        "body": {
                            "mistral_api_key": "{{$node[\"Set Variables\"].json[\"mistral_key\"]}}",
                            "qdrant_url": "{{$node[\"Set Variables\"].json[\"qdrant_url\"]}}",
                            "qdrant_api_key": "{{$node[\"Set Variables\"].json[\"qdrant_key\"]}}",
                            "collection_name": "{{$node[\"Set Variables\"].json[\"collection_name\"]}}",
                            "vector_size": 1024,
                            "distance_metric": "cosine",
                            "force_recreate": False
                        }
                    }
                ]
            },
            "health_monitoring_workflow": {
                "summary": "n8n Workflow: RAG Service Health Monitoring",
                "description": "n8n workflow for monitoring RAG service health and capabilities",
                "workflow_steps": [
                    {
                        "step": 1,
                        "node_type": "Schedule Trigger",
                        "operation": "Monitor Health",
                        "interval": "5 minutes"
                    },
                    {
                        "step": 2,
                        "node_type": "HTTP Request",
                        "operation": "Health Check",
                        "url": "{{$node[\"Set Variables\"].json[\"api_base_url\"]}}/api/v1/rag-operations/health",
                        "method": "GET"
                    },
                    {
                        "step": 3,
                        "node_type": "IF",
                        "operation": "Check Health Status",
                        "condition": "{{$node[\"Health Check\"].json[\"status\"] !== \"healthy\"}}"
                    }
                ]
            }
        }
    }
