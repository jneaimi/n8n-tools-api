"""
Pydantic models for OCR operations.

Defines request and response models for AI-powered OCR endpoints.
"""

from pydantic import BaseModel, Field, validator, HttpUrl, SecretStr
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
    """Model for extracted images with enhanced Mistral native extraction support."""
    
    id: str = Field(..., description="Unique identifier for the image")
    sequence_number: Optional[int] = Field(None, description="Global sequence number across all pages")
    page_number: Optional[int] = Field(None, description="Page number where image was found")
    
    # Enhanced coordinate information
    coordinates: Optional[Dict[str, Any]] = Field(
        None, 
        description="Enhanced coordinate information including absolute, relative, and dimensions"
    )
    
    # Backward compatibility fields
    format: Optional[str] = Field(None, description="Image format (e.g., 'png', 'jpeg')")
    size: Optional[Dict[str, int]] = Field(None, description="Image dimensions (width, height)")
    data: Optional[str] = Field(None, description="Base64 encoded image data")
    position: Optional[Dict[str, float]] = Field(
        None, 
        description="Relative position on page (x, y, width, height as percentages) - legacy field"
    )
    
    # Enhanced Mistral native fields
    base64_data: Optional[str] = Field(None, description="Base64 encoded image data from Mistral")
    annotation: Optional[str] = Field(None, description="Image annotation or description")
    extraction_quality: Optional[Dict[str, Any]] = Field(
        None, 
        description="Quality assessment of the extraction"
    )
    format_info: Optional[Dict[str, Any]] = Field(
        None, 
        description="Detailed format information and characteristics"
    )
    size_info: Optional[Dict[str, Any]] = Field(
        None, 
        description="Detailed size and compression information"
    )
    extraction_metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Metadata about the extraction process and source"
    )
    
    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow additional fields for future extensibility

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
    
    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow additional metadata fields

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
    
    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow additional fields for enhanced processing info

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
    
    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow additional fields for validation info and other enhancements

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

class S3Config(BaseModel):
    """Model for S3 configuration parameters."""
    
    endpoint: Optional[str] = Field(
        None,
        description="S3-compatible endpoint URL (optional for AWS S3)",
        example="https://s3.amazonaws.com"
    )
    
    access_key: str = Field(
        ...,
        description="S3 access key ID",
        min_length=1,
        max_length=128,
        example="AKIAIOSFODNN7EXAMPLE"
    )
    
    secret_key: SecretStr = Field(
        ...,
        description="S3 secret access key",
        min_length=1,
        max_length=128,
        example="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    )
    
    bucket_name: str = Field(
        ...,
        description="S3 bucket name for storing images",
        min_length=3,
        max_length=63,
        pattern=r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$',
        example="my-ocr-images-bucket"
    )
    
    region: Optional[str] = Field(
        "us-east-1",
        description="S3 region (defaults to us-east-1)",
        max_length=20,
        example="us-west-2"
    )
    
    @validator('endpoint')
    def validate_endpoint(cls, v):
        """Validate S3 endpoint URL format."""
        if v is not None:
            if not v.startswith(('http://', 'https://')):
                raise ValueError("Endpoint must start with http:// or https://")
            # Basic URL validation
            try:
                from urllib.parse import urlparse
                parsed = urlparse(v)
                if not parsed.netloc:
                    raise ValueError("Invalid endpoint URL format")
            except Exception:
                raise ValueError("Invalid endpoint URL format")
        return v
    
    @validator('bucket_name')
    def validate_bucket_name(cls, v):
        """Validate S3 bucket name according to AWS naming rules."""
        if not v:
            raise ValueError("Bucket name cannot be empty")
        
        # AWS S3 bucket naming rules
        if len(v) < 3 or len(v) > 63:
            raise ValueError("Bucket name must be between 3 and 63 characters")
        
        if not v[0].isalnum() or not v[-1].isalnum():
            raise ValueError("Bucket name must start and end with a letter or number")
        
        if '..' in v or '.-' in v or '-.' in v:
            raise ValueError("Bucket name cannot contain consecutive periods or period-dash combinations")
        
        # Check for valid characters
        valid_chars = set('abcdefghijklmnopqrstuvwxyz0123456789-.')
        if not all(c in valid_chars for c in v):
            raise ValueError("Bucket name can only contain lowercase letters, numbers, hyphens, and periods")
        
        return v
    
    @validator('region')
    def validate_region(cls, v):
        """Validate AWS region format."""
        if v and not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Invalid region format")
        return v
    
    class Config:
        """Pydantic config."""
        # Hide secret values in string representation
        json_encoders = {
            SecretStr: lambda v: v.get_secret_value() if v else None
        }

class OCRWithS3Request(BaseModel):
    """Request model for OCR processing with S3 image upload."""
    
    # S3 configuration (all fields required)
    s3_config: S3Config = Field(
        ...,
        description="S3 configuration for image upload"
    )
    
    # OCR options (inherited from existing models)
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
    
    # Image upload options
    image_upload_prefix: Optional[str] = Field(
        "ocr-images",
        description="S3 object key prefix for uploaded images",
        max_length=50,
        pattern=r'^[a-zA-Z0-9][a-zA-Z0-9\-_/]*[a-zA-Z0-9]$'
    )
    
    fallback_to_base64: bool = Field(
        True,
        description="Whether to fallback to base64 if S3 upload fails"
    )
    
    upload_timeout_seconds: Optional[int] = Field(
        30,
        description="Timeout for S3 upload operations in seconds",
        ge=5,
        le=300
    )
    
    @validator('image_upload_prefix')
    def validate_prefix(cls, v):
        """Validate S3 object key prefix."""
        if v is not None and v:
            # Remove leading/trailing slashes for consistency
            v = v.strip('/')
            if not v:
                return "ocr-images"  # Default prefix
        return v

class OCRUrlWithS3Request(OCRWithS3Request):
    """Request model for OCR processing from URL with S3 image upload."""
    
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

class OCRImageWithS3(BaseModel):
    """Model for images with S3 URLs instead of base64 data."""
    
    id: str = Field(..., description="Unique identifier for the image")
    sequence_number: Optional[int] = Field(None, description="Global sequence number across all pages")
    page_number: Optional[int] = Field(None, description="Page number where image was found")
    
    # S3-specific fields
    s3_url: str = Field(..., description="Public S3 URL for the uploaded image")
    s3_object_key: str = Field(..., description="S3 object key for the uploaded image")
    upload_timestamp: float = Field(..., description="Unix timestamp when image was uploaded")
    
    # Image metadata
    format: Optional[str] = Field(None, description="Image format (e.g., 'png', 'jpeg')")
    size: Optional[Dict[str, int]] = Field(None, description="Image dimensions (width, height)")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    content_type: Optional[str] = Field(None, description="MIME content type")
    
    # Enhanced coordinate information
    coordinates: Optional[Dict[str, Any]] = Field(
        None, 
        description="Enhanced coordinate information including absolute, relative, and dimensions"
    )
    
    # Backward compatibility with existing OCRImage model
    position: Optional[Dict[str, float]] = Field(
        None, 
        description="Relative position on page (x, y, width, height as percentages) - legacy field"
    )
    
    # Additional metadata
    annotation: Optional[str] = Field(None, description="Image annotation or description")
    extraction_quality: Optional[Dict[str, Any]] = Field(
        None, 
        description="Quality assessment of the extraction"
    )
    extraction_metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Metadata about the extraction process and source"
    )
    
    # S3 upload metadata
    upload_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadata about the S3 upload process"
    )
    
    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow additional fields for future extensibility

class OCRWithS3Response(BaseModel):
    """Response model for OCR operations with S3 image upload."""
    
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Operation message")
    extracted_text: str = Field(..., description="Extracted text content")
    
    # Images with S3 URLs instead of base64
    images: Optional[List[OCRImageWithS3]] = Field(
        None, 
        description="Extracted images uploaded to S3 with public URLs"
    )
    
    metadata: Optional[OCRMetadata] = Field(
        None, 
        description="Document metadata (if include_metadata is True)"
    )
    
    processing_info: OCRProcessingInfo = Field(..., description="Processing information")
    
    # S3-specific processing information
    s3_upload_info: Optional[Dict[str, Any]] = Field(
        None,
        description="Information about S3 upload operations"
    )
    
    # Fallback information
    fallback_images: Optional[List[OCRImage]] = Field(
        None,
        description="Images that failed S3 upload and fell back to base64 (if fallback enabled)"
    )
    
    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow additional fields for validation info and other enhancements
