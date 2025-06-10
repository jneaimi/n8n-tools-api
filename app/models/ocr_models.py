"""
Pydantic models for OCR operations.

Defines request and response models for AI-powered OCR endpoints.
"""

from pydantic import BaseModel, Field, validator, HttpUrl
from typing import List, Dict, Any, Optional, Union
from enum import Enum

class OCRSource(str, Enum):
    """Supported OCR source types."""
    FILE_UPLOAD = "file_upload"
    URL = "url"

class SupportedFileType(str, Enum):
    """Supported file types for OCR processing."""
    PDF = "pdf"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    TIFF = "tiff"

class OCRUrlRequest(BaseModel):
    """Request model for OCR processing from URL."""
    
    url: HttpUrl = Field(
        ...,
        description="URL to the document to process (PDF or image)",
        example="https://example.com/document.pdf"
    )
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format and supported schemes."""
        url_str = str(v)
        if not url_str.startswith(('http://', 'https://')):
            raise ValueError("URL must use HTTP or HTTPS scheme")
        return v

class OCROptions(BaseModel):
    """Options for OCR processing."""
    
    extract_images: bool = Field(
        True,
        description="Whether to extract images from the document"
    )
    
    include_metadata: bool = Field(
        True,
        description="Whether to include document metadata in response"
    )
    
    language_hint: Optional[str] = Field(
        None,
        description="Language hint for better OCR accuracy (e.g., 'en', 'es', 'fr')",
        max_length=10
    )

class OCRImage(BaseModel):
    """Model for extracted images."""
    
    id: str = Field(..., description="Unique identifier for the image")
    format: str = Field(..., description="Image format (e.g., 'png', 'jpeg')")
    size: Dict[str, int] = Field(..., description="Image dimensions (width, height)")
    data: str = Field(..., description="Base64 encoded image data or URL")
    page_number: Optional[int] = Field(None, description="Page number where image was found")
    position: Optional[Dict[str, float]] = Field(
        None, 
        description="Relative position on page (x, y, width, height as percentages)"
    )

class OCRMetadata(BaseModel):
    """Model for document metadata."""
    
    title: Optional[str] = Field(None, description="Document title")
    author: Optional[str] = Field(None, description="Document author")
    subject: Optional[str] = Field(None, description="Document subject")
    creator: Optional[str] = Field(None, description="Document creator")
    producer: Optional[str] = Field(None, description="Document producer")
    creation_date: Optional[str] = Field(None, description="Document creation date")
    modification_date: Optional[str] = Field(None, description="Document modification date")
    page_count: Optional[int] = Field(None, description="Total number of pages")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    language: Optional[str] = Field(None, description="Detected language")

class OCRProcessingInfo(BaseModel):
    """Model for processing information."""
    
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    source_type: OCRSource = Field(..., description="Source type (file_upload or url)")
    ai_model_used: str = Field(..., description="AI model used for OCR")
    confidence_score: Optional[float] = Field(
        None, 
        description="Average confidence score (0-1)",
        ge=0.0,
        le=1.0
    )
    pages_processed: int = Field(..., description="Number of pages processed")

class OCRResponse(BaseModel):
    """Response model for OCR operations."""
    
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Operation message")
    extracted_text: str = Field(..., description="Extracted text content")
    images: Optional[List[OCRImage]] = Field(
        None, 
        description="Extracted images (if extract_images is True)"
    )
    metadata: Optional[OCRMetadata] = Field(
        None, 
        description="Document metadata (if include_metadata is True)"
    )
    processing_info: OCRProcessingInfo = Field(..., description="Processing information")

class OCRErrorResponse(BaseModel):
    """Error response model for OCR operations."""
    
    status: str = Field(..., description="Error status")
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

class OCRServiceStatus(BaseModel):
    """Model for OCR service status."""
    
    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status")
    ai_model_available: bool = Field(..., description="Whether the OCR model is available")
    supported_formats: List[str] = Field(..., description="List of supported file formats")
    max_file_size_mb: int = Field(..., description="Maximum file size in MB")
    rate_limits: Optional[Dict[str, Any]] = Field(
        None, 
        description="Rate limiting information"
    )
