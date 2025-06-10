"""
Custom HTTP-based Qdrant client implementation.

This module provides a direct HTTP implementation for Qdrant operations
to bypass issues with the official qdrant-client library.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from app.models.rag_models import CreateCollectionRequest, VectorDistance, CollectionDetails

logger = logging.getLogger(__name__)


@dataclass
class QdrantHttpResponse:
    """Response from Qdrant HTTP API."""
    status_code: int
    data: Dict[str, Any]
    success: bool


class QdrantHttpClient:
    """HTTP-based Qdrant client for direct API communication."""
    
    def __init__(self, url: str, api_key: str, timeout: int = 30):
        """
        Initialize HTTP client for Qdrant.
        
        Args:
            url: Qdrant server URL
            api_key: Qdrant API key
            timeout: Request timeout in seconds
        """
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        
        # Configure HTTP client
        self.connector = aiohttp.TCPConnector(
            ssl=True,
            use_dns_cache=False,
            ttl_dns_cache=300,
            limit=100,
            limit_per_host=30,
            enable_cleanup_closed=True
        )
        
        self.timeout_config = aiohttp.ClientTimeout(
            total=timeout,
            connect=10,
            sock_read=10
        )
        
        self.headers = {
            "api-key": api_key,
            "Content-Type": "application/json",
            "User-Agent": "n8n-tools-rag-client/1.0"
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout_config,
            headers=self.headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if hasattr(self, 'session'):
            await self.session.close()
    
    async def get_collections(self) -> QdrantHttpResponse:
        """Get all collections from Qdrant."""
        try:
            async with self.session.get(f"{self.url}/collections") as response:
                data = await response.json()
                return QdrantHttpResponse(
                    status_code=response.status,
                    data=data,
                    success=response.status == 200
                )
        except Exception as e:
            logger.error(f"Failed to get collections: {e}")
            raise
    
    async def create_collection(
        self, 
        name: str, 
        vector_size: int = 1024, 
        distance: str = "Cosine",
        force_recreate: bool = False
    ) -> QdrantHttpResponse:
        """
        Create a new collection in Qdrant.
        
        Args:
            name: Collection name
            vector_size: Vector dimension size
            distance: Distance metric (Cosine, Euclidean, Dot)
            force_recreate: Whether to recreate if exists
            
        Returns:
            QdrantHttpResponse with creation result
        """
        try:
            # Check if collection exists first
            if not force_recreate:
                existing = await self.get_collection_info(name)
                if existing.success:
                    return QdrantHttpResponse(
                        status_code=409,
                        data={"status": "error", "message": f"Collection '{name}' already exists"},
                        success=False
                    )
            else:
                # Delete existing collection if force_recreate
                await self.delete_collection(name)
            
            # Create collection payload
            payload = {
                "vectors": {
                    "size": vector_size,
                    "distance": distance
                },
                "optimizers_config": {
                    "default_segment_number": 2,
                    "max_segment_size": 20000,
                    "memmap_threshold": 50000,
                    "indexing_threshold": 20000,
                    "flush_interval_sec": 1,
                    "max_optimization_threads": 2
                },
                "wal_config": {
                    "wal_capacity_mb": 32,
                    "wal_segments_ahead": 0
                },
                "hnsw_config": {
                    "m": 16,
                    "ef_construct": 100,
                    "full_scan_threshold": 10000,
                    "max_indexing_threads": 2,
                    "on_disk": False
                }
            }
            
            async with self.session.put(f"{self.url}/collections/{name}", json=payload) as response:
                data = await response.json()
                return QdrantHttpResponse(
                    status_code=response.status,
                    data=data,
                    success=response.status == 200
                )
                
        except Exception as e:
            logger.error(f"Failed to create collection {name}: {e}")
            raise
    
    async def get_collection_info(self, name: str) -> QdrantHttpResponse:
        """Get information about a specific collection."""
        try:
            async with self.session.get(f"{self.url}/collections/{name}") as response:
                if response.status == 404:
                    return QdrantHttpResponse(
                        status_code=404,
                        data={"status": "error", "message": f"Collection '{name}' not found"},
                        success=False
                    )
                
                data = await response.json()
                return QdrantHttpResponse(
                    status_code=response.status,
                    data=data,
                    success=response.status == 200
                )
        except Exception as e:
            logger.error(f"Failed to get collection info for {name}: {e}")
            raise
    
    async def delete_collection(self, name: str) -> QdrantHttpResponse:
        """Delete a collection."""
        try:
            async with self.session.delete(f"{self.url}/collections/{name}") as response:
                data = await response.json() if response.content_length else {}
                return QdrantHttpResponse(
                    status_code=response.status,
                    data=data,
                    success=response.status in [200, 404]  # 404 is OK (already deleted)
                )
        except Exception as e:
            logger.error(f"Failed to delete collection {name}: {e}")
            raise


class QdrantHttpService:
    """Service wrapper for HTTP-based Qdrant operations."""
    
    async def test_connection(self, url: str, api_key: str, timeout: int = 30) -> bool:
        """Test connection to Qdrant server."""
        try:
            async with QdrantHttpClient(url, api_key, timeout) as client:
                response = await client.get_collections()
                return response.success
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def create_collection_http(
        self, 
        request: CreateCollectionRequest,
        timeout: int = 60
    ) -> tuple[CollectionDetails, float, Dict[str, Any]]:
        """
        Create collection using HTTP client.
        
        Returns:
            Tuple of (collection_details, processing_time_ms, raw_response)
        """
        import time
        start_time = time.time()
        
        url = str(request.qdrant_url)
        api_key = request.qdrant_api_key.get_secret_value()
        
        # Map VectorDistance enum to string
        distance_map = {
            VectorDistance.COSINE: "Cosine",
            VectorDistance.EUCLIDEAN: "Euclidean", 
            VectorDistance.DOT: "Dot"
        }
        distance = distance_map.get(request.distance_metric, "Cosine")
        
        try:
            async with QdrantHttpClient(url, api_key, timeout) as client:
                response = await client.create_collection(
                    name=request.collection_name,
                    vector_size=request.vector_size,
                    distance=distance,
                    force_recreate=request.force_recreate
                )
                
                if not response.success:
                    if response.status_code == 409:
                        from app.services.qdrant_exceptions import QdrantCollectionExistsError
                        raise QdrantCollectionExistsError(f"Collection '{request.collection_name}' already exists")
                    else:
                        from app.services.qdrant_exceptions import QdrantCollectionCreationError
                        raise QdrantCollectionCreationError(f"Failed to create collection: {response.data}")
                
                # Get collection info to build details
                info_response = await client.get_collection_info(request.collection_name)
                collection_info = info_response.data.get('result', {}) if info_response.success else {}
                
                # Build collection details
                vector_config = collection_info.get('config', {}).get('params', {}).get('vectors', {})
                
                details = CollectionDetails(
                    name=request.collection_name,
                    vector_size=vector_config.get('size', request.vector_size),
                    distance_metric=vector_config.get('distance', distance).lower(),
                    points_count=collection_info.get('points_count', 0),
                    indexed_vectors_count=collection_info.get('indexed_vectors_count', 0),
                    storage_type="memory",  # Default for our HNSW config
                    config=collection_info.get('config', {})
                )
                
                processing_time = (time.time() - start_time) * 1000
                
                return details, processing_time, response.data
                
        except Exception as e:
            logger.error(f"HTTP collection creation failed: {e}")
            raise


# Global HTTP service instance
qdrant_http_service = QdrantHttpService()
