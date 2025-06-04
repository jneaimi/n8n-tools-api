"""
Pydantic models for PDF operations.

Defines request and response models for API endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
import re

class PageRangeRequest(BaseModel):
    """Request model for PDF split by page ranges."""
    
    ranges: List[str] = Field(
        ..., 
        description="List of page ranges (e.g., ['1-3', '5', '7-9'])",
        min_items=1,
        max_items=50
    )
    
    @validator('ranges')
    def validate_ranges(cls, v):
        """Validate page range format."""
        for range_str in v:
            if not re.match(r'^\d+(-\d+)?$', range_str.strip()):
                raise ValueError(f"Invalid page range format: {range_str}")
        return v

class SplitOptions(BaseModel):
    """Options for PDF splitting operations."""
    
    filename_prefix: Optional[str] = Field(
        None,
        description="Prefix for output filenames",
        max_length=50
    )
    
    include_metadata: bool = Field(
        True,
        description="Whether to include metadata in response"
    )

class PDFSplitResponse(BaseModel):
    """Response model for PDF split operations."""
    
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Operation message")
    file_count: int = Field(..., description="Number of output files")
    files: Dict[str, str] = Field(..., description="Map of filename to download URL/ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Source PDF metadata")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")

class PDFMetadataResponse(BaseModel):
    """Response model for PDF metadata extraction."""
    
    status: str = Field(..., description="Operation status")
    page_count: int = Field(..., description="Number of pages")
    file_size_bytes: int = Field(..., description="File size in bytes")
    file_size_mb: float = Field(..., description="File size in MB")
    encrypted: bool = Field(..., description="Whether PDF is encrypted")
    metadata: Dict[str, Any] = Field(..., description="PDF metadata")
    page_dimensions: Optional[Dict[str, float]] = Field(None, description="Page dimensions")

class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    type: str = Field(..., description="Error category")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
