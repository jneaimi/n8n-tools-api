"""
AI PDF Operations Configuration

Manages configuration settings for AI-powered PDF processing operations
including API keys, model settings, and service configurations.
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pydantic import Field


class AIPDFConfig(BaseSettings):
    """Configuration for AI PDF operations."""
    
    # Mistral API configuration
    mistral_api_key: Optional[str] = Field(
        default=None,
        description="Mistral AI API key for text processing"
    )
    mistral_model: str = Field(
        default="mistral-medium",
        description="Mistral model to use for text processing"
    )
    mistral_max_tokens: int = Field(
        default=1000,
        description="Maximum tokens for Mistral API responses"
    )
    mistral_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for Mistral API responses"
    )
    
    # OCR configuration
    ocr_enabled: bool = Field(
        default=True,
        description="Enable OCR functionality"
    )
    ocr_model: str = Field(
        default="tesseract",
        description="OCR engine to use (tesseract, paddle, easyocr)"
    )
    ocr_languages: str = Field(
        default="eng",
        description="OCR languages (comma-separated)"
    )
    
    # Vision analysis configuration
    vision_enabled: bool = Field(
        default=True,
        description="Enable vision analysis functionality"
    )
    vision_model: str = Field(
        default="yolov5",
        description="Vision model for object detection"
    )
    vision_confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for vision detection"
    )
    
    # Embeddings configuration
    embeddings_enabled: bool = Field(
        default=True,
        description="Enable embeddings generation"
    )
    embeddings_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Model for generating text embeddings"
    )
    embeddings_chunk_size: int = Field(
        default=512,
        gt=0,
        description="Chunk size for text embeddings"
    )
    embeddings_overlap: int = Field(
        default=50,
        ge=0,
        description="Overlap between text chunks"
    )
    
    # General AI settings
    max_pages_per_request: int = Field(
        default=50,
        gt=0,
        description="Maximum pages to process per AI request"
    )
    timeout_seconds: int = Field(
        default=300,
        gt=0,
        description="Timeout for AI operations in seconds"
    )
    cache_enabled: bool = Field(
        default=True,
        description="Enable caching for AI operations"
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        gt=0,
        description="Cache TTL in seconds"
    )

    class Config:
        env_file = ".env"
        env_prefix = "AI_PDF_"
        case_sensitive = False


# Global AI PDF configuration instance
ai_pdf_config = AIPDFConfig()
