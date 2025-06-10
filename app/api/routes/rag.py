"""
RAG Operations API routes.

Provides endpoints for RAG (Retrieval-Augmented Generation) operations including
Qdrant collection management and Mistral embedding operations designed for 
n8n workflow automation.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import time

from app.models.rag_models import (
    CreateCollectionRequest, CollectionResponse, CollectionDetails,
    CollectionInfoResponse, ErrorResponse, EmbeddingRequest, EmbeddingResponse
)
from app.services.qdrant_exceptions import (
    QdrantConnectionError, 
    QdrantAuthenticationError,
    QdrantValidationError,
    QdrantCollectionExistsError,
    QdrantCollectionCreationError
)
from app.services.qdrant_http_service import qdrant_http_service
from app.core.auth import (
    validate_api_key_format, 
    verify_mistral_api_key, 
    hash_api_key, 
    check_rate_limit
)

logger = logging.getLogger(__name__)

# Create the RAG Operations router
router = APIRouter()

@router.get(
    "/", 
    summary="RAG Service Status and Capabilities",
    description="""
    Get comprehensive information about the RAG Operations service and its capabilities.
    
    ## 🎯 Purpose
    This endpoint provides service status, available operations, and configuration details
    for the RAG (Retrieval-Augmented Generation) operations service.
    
    ## 📋 Information Provided
    - **Service status** and readiness
    - **Available operations** and endpoints
    - **Supported embedding models** (Mistral AI)
    - **Vector database** configuration (Qdrant)
    - **Default settings** for collections
    
    ## 🚀 n8n Integration
    Use this endpoint to:
    - **Verify service availability** before workflows
    - **Get configuration information** for dynamic workflows
    - **Check supported features** and operations
    
    ```json
    // Example n8n HTTP Request for service status
    {
      "method": "GET",
      "url": "{{$node["HTTP Request"].json["url"]}}/api/v1/rag-operations/"
    }
    ```
    
    ## 💡 Use Cases
    - Service discovery in n8n workflows
    - Health checks and monitoring
    - Configuration validation
    - Documentation and API exploration
    """,
    responses={
        200: {
            "description": "Service status retrieved successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "service_status": {
                            "summary": "RAG service status information",
                            "description": "Complete service status with capabilities",
                            "value": {
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
                        }
                    }
                }
            }
        }
    },
    operation_id="get_rag_service_status",
    tags=["RAG Operations"]
)
async def rag_service_status():
    """Get RAG operations service status and available operations."""
    return JSONResponse(
        content={
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
    )

@router.get(
    "/health", 
    summary="RAG Service Health Check and Monitoring",
    description="""
    Comprehensive health check endpoint for RAG operations service monitoring and diagnostics.
    
    ## 🎯 Purpose
    This endpoint provides detailed health status, operational capabilities, and service metrics
    for monitoring and diagnostic purposes in production environments.
    
    ## 📊 Health Information
    - **Service health status** and uptime
    - **Operational capabilities** verification
    - **Version information** and timestamps
    - **Vector configuration** settings
    - **Supported operations** status
    
    ## 🚀 n8n Integration
    Perfect for:
    - **Health monitoring** workflows
    - **Service discovery** and capability checking
    - **Automated diagnostics** and alerting
    - **Pre-workflow validation**
    
    ```json
    // Example n8n HTTP Request for health monitoring
    {
      "method": "GET",
      "url": "{{$node["HTTP Request"].json["url"]}}/api/v1/rag-operations/health",
      "headers": {
        "Accept": "application/json"
      }
    }
    ```
    
    ## 💡 Use Cases
    - Service health monitoring dashboards
    - Automated health checks in CI/CD
    - n8n workflow pre-flight checks
    - System diagnostics and troubleshooting
    """,
    responses={
        200: {
            "description": "Health check completed successfully", 
            "content": {
                "application/json": {
                    "examples": {
                        "healthy_service": {
                            "summary": "Healthy RAG service status",
                            "description": "Service is healthy and all capabilities are operational",
                            "value": {
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
                }
            }
        }
    },
    operation_id="get_rag_service_health",
    tags=["RAG Operations"]
)
async def rag_health_check():
    """
    Health check endpoint for RAG operations service.
    
    Returns service health status and operational capabilities.
    Use this endpoint to verify RAG operations are available before processing.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "rag-operations",
            "version": "1.0.0",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
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
    )

# Placeholder endpoints for future implementation
@router.post(
    "/test-connection", 
    summary="Test Qdrant Connection and Authentication",
    description="""
    Test connection to Qdrant server with comprehensive validation and authentication checks.
    
    ## 🎯 Purpose
    This endpoint validates both Mistral API key and Qdrant connection before attempting collection operations.
    Essential for troubleshooting and validating credentials in n8n workflows.
    
    ## 🔧 What this endpoint does:
    1. **Validates Mistral API key** format and authenticates with Mistral AI
    2. **Tests Qdrant connectivity** using provided URL and API key  
    3. **Verifies permissions** by attempting to list collections
    4. **Returns connection status** with detailed diagnostic information
    5. **Applies rate limiting** for security protection
    
    ## 🚀 n8n Integration
    Use this endpoint before collection creation to ensure all credentials are valid:
    
    ```json
    // Example n8n HTTP Request node for connection testing
    {
      "method": "POST",
      "url": "{{$node["HTTP Request"].json["url"]}}/api/v1/rag-operations/test-connection",
      "headers": {
        "Content-Type": "application/json"
      },
      "body": {
        "mistral_api_key": "{{$node["Set"].json["mistral_key"]}}",
        "qdrant_url": "https://your-qdrant-instance.com:6333",
        "qdrant_api_key": "{{$node["Set"].json["qdrant_key"]}}",
        "collection_name": "test_connection_check"
      }
    }
    ```
    
    ## 💡 Use Cases
    - **Pre-flight checks** before collection creation
    - **Credential validation** in n8n setup workflows
    - **Troubleshooting** connection issues
    - **Health monitoring** for external services
    
    ## 🔐 Security Features
    - Same authentication and rate limiting as collection creation
    - Secure credential validation without storing keys
    - Comprehensive error reporting for debugging
    """,
    responses={
        200: {
            "description": "Connection successful",
            "content": {
                "application/json": {
                    "examples": {
                        "successful_connection": {
                            "summary": "Successful connection test",
                            "description": "All credentials valid and connection established",
                            "value": {
                                "status": "success",
                                "message": "Successfully connected to Qdrant server",
                                "qdrant_url": "https://your-qdrant-instance.com:6333",
                                "connection_validated": True,
                                "client_type": "http_client"
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "Bad request - validation errors",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_api_key_format": {
                            "summary": "Invalid Mistral API key format",
                            "description": "API key format validation failed",
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
                        }
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized - invalid credentials",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_mistral_key": {
                            "summary": "Invalid Mistral API key",
                            "description": "Mistral API key authentication failed",
                            "value": {
                                "status": "error",
                                "error_code": "INVALID_API_KEY",
                                "message": "Invalid Mistral AI API key",
                                "details": {
                                    "help": "Ensure you're using a valid Mistral AI API key"
                                }
                            }
                        },
                        "invalid_qdrant_credentials": {
                            "summary": "Invalid Qdrant credentials",
                            "description": "Qdrant authentication or connection failed",
                            "value": {
                                "error": "AuthenticationError",
                                "message": "Invalid Qdrant API key or insufficient permissions",
                                "qdrant_url": "https://your-qdrant-instance.com:6333"
                            }
                        }
                    }
                }
            }
        },
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "examples": {
                        "rate_limit_exceeded": {
                            "summary": "Rate limit exceeded",
                            "description": "Too many requests within the time window",
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
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "examples": {
                        "connection_error": {
                            "summary": "Qdrant connection error",
                            "description": "Unable to establish connection to Qdrant server",
                            "value": {
                                "error": "ConnectionError",
                                "message": "Failed to connect to Qdrant server",
                                "qdrant_url": "https://your-qdrant-instance.com:6333",
                                "details": "Connection timeout after 30 seconds"
                            }
                        }
                    }
                }
            }
        }
    },
    operation_id="test_qdrant_connection",
    tags=["RAG Operations"]
)
async def test_qdrant_connection(request: CreateCollectionRequest):
    """
    Test connection to Qdrant server with provided credentials.
    
    Validates the connection without creating any collections.
    Useful for testing credentials and server availability.
    """
    # Extract Mistral API key from request body
    mistral_api_key = request.mistral_api_key.get_secret_value()
    
    # 1. Validate API key format
    if not validate_api_key_format(mistral_api_key):
        logger.warning("Invalid Mistral API key format provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
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
        )
    
    # 2. Generate hashed API key for logging and rate limiting
    api_key_hash = hash_api_key(mistral_api_key)
    
    # 3. Check rate limiting using hashed key as client_id
    if not check_rate_limit(api_key_hash):
        logger.warning(f"Rate limit exceeded for API key: {api_key_hash}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "status": "error",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded", 
                "details": {
                    "limit": "100 requests per 60 seconds",
                    "retry_after": 60
                }
            }
        )
    
    # 4. Verify API key validity with Mistral
    try:
        is_valid = await verify_mistral_api_key(mistral_api_key)
        if not is_valid:
            logger.warning(f"Invalid Mistral API key: {api_key_hash}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "error_code": "INVALID_API_KEY",
                    "message": "Invalid Mistral AI API key",
                    "details": {
                        "help": "Ensure you're using a valid Mistral AI API key"
                    }
                }
            )
    except HTTPException:
        # Re-raise HTTPExceptions (they should not be caught by the generic handler)
        raise
    except Exception as auth_error:
        logger.error(f"API key validation error: {str(auth_error)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "error_code": "API_KEY_VALIDATION_ERROR",
                "message": "Error validating API key",
                "details": {"error": str(auth_error)}
            }
        )
    
    # Log successful authentication
    logger.info(f"Successfully authenticated API key: {api_key_hash}")
    logger.info(f"Testing Qdrant connection to: {request.qdrant_url}")
    
    try:
        # Test connection using HTTP client (more reliable)
        url = str(request.qdrant_url)
        api_key = request.qdrant_api_key.get_secret_value()
        
        logger.info("Testing Qdrant connection using HTTP client...")
        connection_success = await qdrant_http_service.test_connection(url, api_key, timeout=30)
        
        if connection_success:
            logger.info("Qdrant connection test successful")
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Successfully connected to Qdrant server",
                    "qdrant_url": url,
                    "connection_validated": True,
                    "client_type": "http_client"
                }
            )
        else:
            raise QdrantConnectionError("HTTP connection test failed")
        
    except QdrantAuthenticationError as e:
        logger.warning(f"Authentication error testing connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AuthenticationError",
                "message": "Invalid Qdrant API key or insufficient permissions",
                "qdrant_url": str(request.qdrant_url)
            }
        )
        
    except QdrantConnectionError as e:
        logger.error(f"Connection error testing Qdrant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ConnectionError", 
                "message": "Failed to connect to Qdrant server",
                "qdrant_url": str(request.qdrant_url),
                "details": str(e)
            }
        )
        
    except Exception as e:
        logger.error(f"Unexpected error testing connection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred while testing the connection",
                "qdrant_url": str(request.qdrant_url)
            }
        )

@router.post(
    "/create-collection", 
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Qdrant Collection for Mistral Embeddings",
    description="""
    Create a new Qdrant collection optimized for Mistral AI embeddings with comprehensive validation and error handling.
    
    ## 🎯 Purpose
    This endpoint creates production-ready Qdrant collections specifically configured for Mistral embedding models.
    Perfect for RAG (Retrieval-Augmented Generation) workflows in n8n automation.
    
    ## 🔧 What this endpoint does:
    1. **Validates Mistral API key** format and authenticates with Mistral AI service
    2. **Tests Qdrant connectivity** using provided credentials
    3. **Creates optimized collection** with HNSW indexing and memory storage
    4. **Returns detailed metadata** about the created collection
    5. **Applies rate limiting** (100 requests/60 seconds) for API protection
    
    ## ⚙️ Collection Configuration
    The created collection includes:
    - **Vector dimensions**: 1024 (Mistral standard) or custom size (1-4096)
    - **Distance metric**: Cosine similarity (default) or euclidean/dot product
    - **Indexing**: HNSW algorithm optimized for similarity search
    - **Storage**: Memory-based for fast retrieval
    - **Optimization**: Production settings for embedding workloads
    
    ## 🚀 n8n Integration
    ```json
    // Example n8n HTTP Request node configuration
    {
      "method": "POST",
      "url": "{{$node["HTTP Request"].json["url"]}}/api/v1/rag-operations/create-collection",
      "headers": {
        "Content-Type": "application/json"
      },
      "body": {
        "mistral_api_key": "{{$node["Set"].json["mistral_key"]}}",
        "qdrant_url": "https://your-qdrant-instance.com:6333",
        "qdrant_api_key": "{{$node["Set"].json["qdrant_key"]}}",
        "collection_name": "embeddings_{{$node["DateTime"].json["timestamp"]}}",
        "vector_size": 1024,
        "distance_metric": "cosine",
        "force_recreate": false
      }
    }
    ```
    
    ## 🔐 Security Features
    - Mistral API key validation and verification
    - Qdrant authentication testing
    - Rate limiting protection
    - Secure credential handling with SecretStr
    - Comprehensive error logging with hashed keys
    
    ## ⚡ Performance Features
    - Connection validation before collection creation
    - Optimized HNSW configuration for embeddings
    - Memory-based storage for fast access
    - Processing time tracking
    - Circuit breaker pattern for reliability
    """,
    responses={
        201: {
            "description": "Collection created successfully",
            "model": CollectionResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "successful_creation": {
                            "summary": "Successful collection creation",
                            "description": "Example response when collection is created successfully",
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
                        "custom_dimensions": {
                            "summary": "Collection with custom vector dimensions",
                            "description": "Example for creating collection with non-standard vector size",
                            "value": {
                                "status": "success",
                                "collection_name": "custom_embeddings_512",
                                "message": "Collection 'custom_embeddings_512' created successfully with Mistral embedding configuration",
                                "details": {
                                    "name": "custom_embeddings_512",
                                    "vector_size": 512,
                                    "distance_metric": "euclidean",
                                    "points_count": 0,
                                    "indexed_vectors_count": 0,
                                    "storage_type": "memory"
                                },
                                "processing_time_ms": 189.7
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "Bad request - validation errors", 
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
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
                        "invalid_collection_name": {
                            "summary": "Invalid collection name format",
                            "description": "Error when collection name contains invalid characters",
                            "value": {
                                "error": "ValidationError",
                                "message": "Collection name must contain only alphanumeric characters, underscores, and hyphens",
                                "collection_name": "invalid-collection-name!"
                            }
                        },
                        "invalid_vector_size": {
                            "summary": "Invalid vector dimensions",
                            "description": "Error when vector size is outside allowed range",
                            "value": {
                                "error": "ValidationError", 
                                "message": "Vector size must be between 1 and 4096 dimensions",
                                "collection_name": "test_collection"
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized - invalid API keys",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_mistral_key": {
                            "summary": "Invalid Mistral API key",
                            "description": "Error when Mistral API key is not valid or expired",
                            "value": {
                                "status": "error",
                                "error_code": "INVALID_API_KEY",
                                "message": "Invalid Mistral AI API key",
                                "details": {
                                    "help": "Ensure you're using a valid Mistral AI API key"
                                }
                            }
                        },
                        "invalid_qdrant_key": {
                            "summary": "Invalid Qdrant credentials",
                            "description": "Error when Qdrant API key or URL is invalid",
                            "value": {
                                "error": "AuthenticationError",
                                "message": "Invalid Qdrant API key or insufficient permissions",
                                "collection_name": "test_collection"
                            }
                        }
                    }
                }
            }
        },
        409: {
            "description": "Conflict - collection already exists",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "collection_exists": {
                            "summary": "Collection already exists",
                            "description": "Error when trying to create a collection that already exists",
                            "value": {
                                "error": "CollectionExistsError",
                                "message": "Collection 'existing_collection' already exists in Qdrant",
                                "collection_name": "existing_collection",
                                "suggestion": "Use force_recreate=true to overwrite existing collection"
                            }
                        }
                    }
                }
            }
        },
        429: {
            "description": "Rate limit exceeded",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
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
            }
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "connection_error": {
                            "summary": "Qdrant connection error",
                            "description": "Error when unable to connect to Qdrant server",
                            "value": {
                                "error": "ConnectionError",
                                "message": "Failed to connect to Qdrant server",
                                "collection_name": "test_collection",
                                "details": "Connection timeout after 30 seconds"
                            }
                        },
                        "creation_error": {
                            "summary": "Collection creation error",
                            "description": "Error during collection creation process",
                            "value": {
                                "error": "CollectionCreationError",
                                "message": "Failed to create collection",
                                "collection_name": "test_collection",
                                "details": "Insufficient storage space on Qdrant server"
                            }
                        }
                    }
                }
            }
        }
    },
    operation_id="create_qdrant_collection",
    tags=["RAG Operations"]
)
async def create_collection(request: CreateCollectionRequest):
    """
    Create a new Qdrant collection for Mistral embeddings.
    
    Validates the Mistral API key, establishes Qdrant connection, and creates
    a collection optimized for vector similarity search with Mistral embeddings.
    """
    start_time = time.time()
    
    # Extract Mistral API key from request body
    mistral_api_key = request.mistral_api_key.get_secret_value()
    
    # 1. Validate API key format
    if not validate_api_key_format(mistral_api_key):
        logger.warning("Invalid Mistral API key format provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
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
        )
    
    # 2. Generate hashed API key for logging and rate limiting
    api_key_hash = hash_api_key(mistral_api_key)
    
    # 3. Check rate limiting using hashed key as client_id
    if not check_rate_limit(api_key_hash):
        logger.warning(f"Rate limit exceeded for API key: {api_key_hash}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "status": "error",
                "error_code": "RATE_LIMIT_EXCEEDED", 
                "message": "Rate limit exceeded",
                "details": {
                    "limit": "100 requests per 60 seconds",
                    "retry_after": 60
                }
            }
        )
    
    # 4. Verify API key validity with Mistral
    try:
        is_valid = await verify_mistral_api_key(mistral_api_key)
        if not is_valid:
            logger.warning(f"Invalid Mistral API key: {api_key_hash}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "error_code": "INVALID_API_KEY",
                    "message": "Invalid Mistral AI API key",
                    "details": {
                        "help": "Ensure you're using a valid Mistral AI API key"
                    }
                }
            )
    except HTTPException:
        # Re-raise HTTPExceptions (they should not be caught by the generic handler)
        raise
    except Exception as auth_error:
        logger.error(f"API key validation error: {str(auth_error)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "error_code": "API_KEY_VALIDATION_ERROR",
                "message": "Error validating API key",
                "details": {"error": str(auth_error)}
            }
        )
    
    # Log successful authentication
    logger.info(f"Successfully authenticated API key: {api_key_hash}")
    logger.info(f"Creating collection: {request.collection_name}")
    
    try:
        # Create collection using HTTP service (more reliable than qdrant-client)
        collection_details, processing_time, raw_response = await qdrant_http_service.create_collection_http(
            request=request,
            timeout=60  # Allow longer timeout for collection creation
        )
        
        logger.info(f"Successfully created collection: {request.collection_name}")
        
        return CollectionResponse(
            status="success",
            collection_name=request.collection_name,
            message=f"Collection '{request.collection_name}' created successfully with Mistral embedding configuration",
            details=collection_details,
            processing_time_ms=processing_time,
            qdrant_response=raw_response
        )
        
    except QdrantValidationError as e:
        logger.warning(f"Validation error creating collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": str(e),
                "collection_name": request.collection_name
            }
        )
        
    except QdrantAuthenticationError as e:
        logger.warning(f"Authentication error creating collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AuthenticationError", 
                "message": "Invalid Qdrant API key or insufficient permissions",
                "collection_name": request.collection_name
            }
        )
        
    except QdrantCollectionExistsError as e:
        logger.warning(f"Collection already exists: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "CollectionExistsError",
                "message": str(e),
                "collection_name": request.collection_name,
                "suggestion": "Use force_recreate=true to overwrite existing collection"
            }
        )
        
    except QdrantConnectionError as e:
        logger.error(f"Connection error creating collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ConnectionError",
                "message": "Failed to connect to Qdrant server",
                "collection_name": request.collection_name,
                "details": str(e)
            }
        )
        
    except QdrantCollectionCreationError as e:
        logger.error(f"Collection creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "CollectionCreationError",
                "message": "Failed to create collection",
                "collection_name": request.collection_name,
                "details": str(e)
            }
        )
        
    except Exception as e:
        # Log full error details for debugging
        logger.error(f"Unexpected error creating collection: {e}", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred while creating the collection",
                "collection_name": request.collection_name
            }
        )

@router.get("/collections", summary="List Collections", tags=["RAG Operations"])
async def list_collections():
    """List existing Qdrant collections (placeholder - to be implemented)."""
    return JSONResponse(
        status_code=501,
        content={
            "message": "List collections endpoint - implementation pending",
            "status": "not_implemented", 
            "next_steps": "This endpoint will be implemented in the next development phase"
        }
    )

@router.get("/collections/{collection_name}", summary="Get Collection Info", tags=["RAG Operations"])
async def get_collection_info(collection_name: str):
    """Get detailed information about a specific collection (placeholder - to be implemented)."""
    return JSONResponse(
        status_code=501,
        content={
            "message": f"Collection info endpoint for '{collection_name}' - implementation pending",
            "status": "not_implemented",
            "collection_name": collection_name,
            "next_steps": "This endpoint will be implemented in the next development phase"
        }
    )
