"""
Base Classes for AI PDF Operations

Abstract base classes that define the interface for AI-powered PDF processing
operations including OCR, Vision, and Embeddings processing.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel
import asyncio
from datetime import datetime


class AIOperationResult(BaseModel):
    """Standard result format for AI operations."""
    
    success: bool
    operation_type: str
    timestamp: datetime
    processing_time_seconds: float
    data: Dict[str, Any]
    metadata: Dict[str, Any] = {}
    errors: List[str] = []
    warnings: List[str] = []


class AIOperationConfig(BaseModel):
    """Base configuration for AI operations."""
    
    enabled: bool = True
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: float = 1.0


class AIOperation(ABC):
    """Abstract base class for all AI operations."""
    
    def __init__(self, config: Optional[AIOperationConfig] = None):
        self.config = config or AIOperationConfig()
        self._operation_type = self.__class__.__name__.replace("Processor", "").lower()
    
    @abstractmethod
    async def process(self, pdf_content: bytes, **kwargs) -> AIOperationResult:
        """
        Process PDF content and return structured results.
        
        Args:
            pdf_content: Raw PDF file content as bytes
            **kwargs: Additional operation-specific parameters
            
        Returns:
            AIOperationResult with processed data and metadata
        """
        pass
    
    async def validate_input(self, pdf_content: bytes) -> bool:
        """
        Validate input PDF content.
        
        Args:
            pdf_content: Raw PDF file content as bytes
            
        Returns:
            True if valid, False otherwise
        """
        if not pdf_content or len(pdf_content) == 0:
            return False
        
        # Check if it's a PDF file (basic magic number check)
        if not pdf_content.startswith(b'%PDF-'):
            return False
            
        return True
    
    async def _execute_with_timeout(self, operation_func, *args, **kwargs) -> Any:
        """Execute an operation with timeout."""
        try:
            return await asyncio.wait_for(
                operation_func(*args, **kwargs),
                timeout=self.config.timeout_seconds
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation {self._operation_type} timed out after {self.config.timeout_seconds} seconds")
    
    def _create_result(self, 
                      success: bool, 
                      data: Dict[str, Any] = None, 
                      metadata: Dict[str, Any] = None,
                      errors: List[str] = None,
                      warnings: List[str] = None,
                      processing_time: float = 0.0) -> AIOperationResult:
        """Create standardized operation result."""
        return AIOperationResult(
            success=success,
            operation_type=self._operation_type,
            timestamp=datetime.utcnow(),
            processing_time_seconds=processing_time,
            data=data or {},
            metadata=metadata or {},
            errors=errors or [],
            warnings=warnings or []
        )


class OCROperation(AIOperation):
    """Abstract base class for OCR operations."""
    
    @abstractmethod
    async def extract_text(self, pdf_content: bytes, page_numbers: Optional[List[int]] = None) -> AIOperationResult:
        """
        Extract text from PDF pages using OCR.
        
        Args:
            pdf_content: Raw PDF file content as bytes
            page_numbers: Specific pages to process (None for all pages)
            
        Returns:
            AIOperationResult with extracted text and metadata
        """
        pass
    
    @abstractmethod
    async def extract_structured_data(self, pdf_content: bytes, schema: Optional[Dict] = None) -> AIOperationResult:
        """
        Extract structured data from PDF using OCR and AI.
        
        Args:
            pdf_content: Raw PDF file content as bytes
            schema: Optional schema for structured extraction
            
        Returns:
            AIOperationResult with structured data
        """
        pass


class VisionOperation(AIOperation):
    """Abstract base class for vision analysis operations."""
    
    @abstractmethod
    async def analyze_layout(self, pdf_content: bytes, page_numbers: Optional[List[int]] = None) -> AIOperationResult:
        """
        Analyze document layout and structure.
        
        Args:
            pdf_content: Raw PDF file content as bytes
            page_numbers: Specific pages to analyze (None for all pages)
            
        Returns:
            AIOperationResult with layout analysis
        """
        pass
    
    @abstractmethod
    async def detect_objects(self, pdf_content: bytes, object_types: Optional[List[str]] = None) -> AIOperationResult:
        """
        Detect objects in PDF pages (tables, charts, images, etc.).
        
        Args:
            pdf_content: Raw PDF file content as bytes
            object_types: Types of objects to detect
            
        Returns:
            AIOperationResult with detected objects
        """
        pass


class EmbeddingsOperation(AIOperation):
    """Abstract base class for embeddings generation operations."""
    
    @abstractmethod
    async def generate_text_embeddings(self, pdf_content: bytes, chunk_size: Optional[int] = None) -> AIOperationResult:
        """
        Generate embeddings for text content in PDF.
        
        Args:
            pdf_content: Raw PDF file content as bytes
            chunk_size: Size of text chunks for embeddings
            
        Returns:
            AIOperationResult with embeddings data
        """
        pass
    
    @abstractmethod
    async def similarity_search(self, pdf_content: bytes, query: str, top_k: int = 5) -> AIOperationResult:
        """
        Perform similarity search against PDF content.
        
        Args:
            pdf_content: Raw PDF file content as bytes
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            AIOperationResult with similarity search results
        """
        pass
