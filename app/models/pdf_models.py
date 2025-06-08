"""
Pydantic models for PDF operations.

Defines request and response models for API endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Tuple, Literal
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

# ================== PDF MERGE MODELS ==================

class MergeOptions(BaseModel):
    """Options for PDF merge operations."""
    
    merge_strategy: Literal["append", "interleave"] = Field(
        "append",
        description="Strategy for merging PDFs: 'append' (sequential) or 'interleave' (alternate pages)"
    )
    
    preserve_metadata: bool = Field(
        True,
        description="Whether to preserve metadata from the first PDF"
    )
    
    output_filename: Optional[str] = Field(
        None,
        description="Custom filename for merged PDF",
        max_length=100
    )

class PageSelectionRequest(BaseModel):
    """Request model for merge with page selection."""
    
    file_pages: List[List[int]] = Field(
        ...,
        description="List of page numbers for each uploaded file (1-based indexing)",
        min_items=2
    )
    
    merge_options: Optional[MergeOptions] = Field(
        None,
        description="Merge configuration options"
    )
    
    @validator('file_pages')
    def validate_page_selections(cls, v):
        """Validate page selections."""
        if len(v) < 2:
            raise ValueError("At least 2 files with page selections required")
        
        for i, pages in enumerate(v):
            if not pages:
                continue  # Allow empty page lists (file will be skipped)
            
            for page_num in pages:
                if page_num < 1:
                    raise ValueError(f"Page numbers must be >= 1 (found {page_num} in file {i + 1})")
                if page_num > 10000:  # Reasonable upper limit
                    raise ValueError(f"Page number too large: {page_num}")
        
        return v

class RangeSelectionRequest(BaseModel):
    """Request model for merge with range selection."""
    
    file_ranges: List[List[str]] = Field(
        ...,
        description="List of page ranges for each uploaded file (e.g., [['1-3', '5'], ['2-4']])",
        min_items=2
    )
    
    merge_options: Optional[MergeOptions] = Field(
        None,
        description="Merge configuration options"
    )
    
    @validator('file_ranges')
    def validate_range_selections(cls, v):
        """Validate range selections."""
        if len(v) < 2:
            raise ValueError("At least 2 files with range selections required")
        
        for i, ranges in enumerate(v):
            if not ranges:
                continue  # Allow empty range lists (file will be skipped)
            
            for range_str in ranges:
                if not re.match(r'^\d+(-\d+)?$', range_str.strip()):
                    raise ValueError(f"Invalid page range format in file {i + 1}: {range_str}")
        
        return v

class PDFMergeResponse(BaseModel):
    """Response model for PDF merge operations."""
    
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Operation message")
    merged_file: Dict[str, Any] = Field(..., description="Information about merged PDF")
    source_files: List[Dict[str, Any]] = Field(..., description="Information about source files")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")

class MergeInfoResponse(BaseModel):
    """Response model for PDF merge preview information."""
    
    status: str = Field(..., description="Operation status")
    files_count: int = Field(..., description="Number of files to merge")
    total_pages: int = Field(..., description="Total pages across all files")
    total_size_mb: float = Field(..., description="Total size in MB")
    estimated_merged_size_mb: float = Field(..., description="Estimated merged file size in MB")
    files: List[Dict[str, Any]] = Field(..., description="Individual file information")
    merge_strategies: List[str] = Field(..., description="Available merge strategies")
    supports_page_selection: bool = Field(..., description="Whether page selection is supported")
    supports_range_selection: bool = Field(..., description="Whether range selection is supported")

# ================== PDF BATCH SPLIT MODELS ==================

class BatchSplitOptions(BaseModel):
    """Options for PDF batch split operations."""
    
    batch_size: int = Field(
        ...,
        gt=0,
        le=1000,
        description="Number of pages per batch (must be greater than 0)"
    )
    
    output_filename_prefix: Optional[str] = Field(
        None,
        description="Custom prefix for output filenames",
        max_length=50
    )
    
    include_page_info: bool = Field(
        True,
        description="Include page range information in filenames"
    )

class BatchSplitInfoRequest(BaseModel):
    """Request model for batch split preview information."""
    
    batch_size: int = Field(
        ...,
        gt=0,
        le=1000,
        description="Number of pages per batch"
    )

class BatchInfo(BaseModel):
    """Information about a single batch."""
    
    batch_number: int = Field(..., description="Batch number (1-based)")
    start_page: int = Field(..., description="Starting page number (1-based)")
    end_page: int = Field(..., description="Ending page number (1-based)")
    pages_count: int = Field(..., description="Number of pages in this batch")

class BatchSplitInfoResponse(BaseModel):
    """Response model for batch split preview information."""
    
    status: str = Field(..., description="Operation status")
    total_pages: int = Field(..., description="Total pages in source PDF")
    batch_size: int = Field(..., description="Pages per batch")
    batch_count: int = Field(..., description="Number of batches that will be created")
    batches: List[BatchInfo] = Field(..., description="Information about each batch")
    file_size_mb: float = Field(..., description="Source file size in MB")
    estimated_total_output_size_mb: float = Field(..., description="Estimated total output size in MB")

class PDFBatchSplitResponse(BaseModel):
    """Response model for PDF batch split operations."""
    
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Operation message")
    batch_count: int = Field(..., description="Number of batches created")
    total_pages: int = Field(..., description="Total pages processed")
    batch_size: int = Field(..., description="Pages per batch")
    files: Dict[str, str] = Field(..., description="Map of filename to file content/URL")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")
