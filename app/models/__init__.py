"""
Pydantic models for the application.
"""

from .pdf_models import (
    PageRangeRequest,
    SplitOptions,
    PDFSplitResponse,
    PDFMetadataResponse,
    ErrorResponse
)

from .rag_models import (
    CreateCollectionRequest,
    CollectionResponse,
    CollectionDetails,
    CollectionInfoResponse,
    VectorDistance,
    EmbeddingRequest,
    EmbeddingResponse
)

__all__ = [
    # PDF models
    "PageRangeRequest",
    "SplitOptions", 
    "PDFSplitResponse",
    "PDFMetadataResponse",
    "ErrorResponse",
    
    # RAG models
    "CreateCollectionRequest",
    "CollectionResponse", 
    "CollectionDetails",
    "CollectionInfoResponse",
    "VectorDistance",
    "EmbeddingRequest",
    "EmbeddingResponse"
]
