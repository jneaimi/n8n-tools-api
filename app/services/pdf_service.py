"""
PDF processing service.

Handles PDF manipulation operations including split, merge, and metadata extraction.
"""

from pypdf import PdfReader, PdfWriter
from typing import List, Dict, Any, BinaryIO, Union
import tempfile
import os
import io
import re
import logging

from app.core.errors import PDFProcessingError

logger = logging.getLogger(__name__)

class PDFService:
    """Service class for PDF operations."""
    
    @staticmethod
    def _parse_page_range(page_range: str, total_pages: int) -> tuple[int, int]:
        """Parse page range string and return (start, end) indices (0-based)."""
        page_range = page_range.strip()
        
        # Handle single page (e.g., "5")
        if '-' not in page_range:
            try:
                page_num = int(page_range)
            except ValueError:
                raise PDFProcessingError(f"Invalid page range format: {page_range}")
            if page_num < 1 or page_num > total_pages:
                raise PDFProcessingError(f"Page {page_num} is out of range (1-{total_pages})")
            return page_num - 1, page_num - 1
        
        # Handle range (e.g., "1-5")
        parts = page_range.split('-', 1)
        if len(parts) != 2:
            raise PDFProcessingError(f"Invalid page range format: {page_range}")
        
        try:
            start = int(parts[0].strip()) if parts[0].strip() else 1
            end = int(parts[1].strip()) if parts[1].strip() else total_pages
        except ValueError:
            raise PDFProcessingError(f"Invalid page numbers in range: {page_range}")
        
        # Validate range
        if start < 1 or end < 1:
            raise PDFProcessingError("Page numbers must be greater than 0")
        if start > total_pages or end > total_pages:
            raise PDFProcessingError(f"Page range {start}-{end} exceeds document length ({total_pages} pages)")
        if start > end:
            raise PDFProcessingError(f"Invalid range: start page ({start}) is greater than end page ({end})")
        
        return start - 1, end - 1  # Convert to 0-based indexing
    
    @staticmethod
    async def split_by_ranges(pdf_content: bytes, ranges: List[str]) -> Dict[str, bytes]:
        """Split PDF by page ranges.
        
        Args:
            pdf_content: PDF file content as bytes
            ranges: List of page ranges (e.g., ['1-3', '5', '7-9'])
            
        Returns:
            Dictionary mapping output filenames to PDF content bytes
        """
        try:
            # Create PDF reader from bytes
            pdf_io = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_io)
            total_pages = len(reader.pages)
            
            if total_pages == 0:
                raise PDFProcessingError("PDF has no pages")
            
            result = {}
            
            for i, page_range in enumerate(ranges):
                try:
                    start_idx, end_idx = PDFService._parse_page_range(page_range, total_pages)
                    
                    # Create new PDF with specified range
                    writer = PdfWriter()
                    for page_idx in range(start_idx, end_idx + 1):
                        writer.add_page(reader.pages[page_idx])
                    
                    # Write to bytes
                    output = io.BytesIO()
                    writer.write(output)
                    output_bytes = output.getvalue()
                    
                    # Generate filename
                    if start_idx == end_idx:
                        filename = f"page_{start_idx + 1}.pdf"
                    else:
                        filename = f"pages_{start_idx + 1}-{end_idx + 1}.pdf"
                    
                    result[filename] = output_bytes
                    
                except Exception as e:
                    logger.error(f"Failed to process range '{page_range}': {str(e)}")
                    raise PDFProcessingError(f"Failed to process range '{page_range}': {str(e)}")
            
            logger.info(f"Successfully split PDF into {len(result)} files")
            return result
            
        except Exception as e:
            logger.error(f"Failed to split PDF by ranges: {str(e)}")
            if isinstance(e, PDFProcessingError):
                raise
            raise PDFProcessingError(f"Failed to split PDF: {str(e)}")
    
    @staticmethod
    async def split_to_individual_pages(pdf_content: bytes) -> Dict[str, bytes]:
        """Split PDF into individual pages.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Dictionary mapping page filenames to PDF content bytes
        """
        try:
            # Create PDF reader from bytes
            pdf_io = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_io)
            total_pages = len(reader.pages)
            
            if total_pages == 0:
                raise PDFProcessingError("PDF has no pages")
            
            result = {}
            
            for i in range(total_pages):
                # Create new PDF with single page
                writer = PdfWriter()
                writer.add_page(reader.pages[i])
                
                # Write to bytes
                output = io.BytesIO()
                writer.write(output)
                output_bytes = output.getvalue()
                
                # Generate filename (1-based page numbering)
                filename = f"page_{i + 1}.pdf"
                result[filename] = output_bytes
            
            logger.info(f"Successfully split PDF into {total_pages} individual pages")
            return result
            
        except Exception as e:
            logger.error(f"Failed to split PDF to individual pages: {str(e)}")
            if isinstance(e, PDFProcessingError):
                raise
            raise PDFProcessingError(f"Failed to split PDF: {str(e)}")
    
    @staticmethod
    async def get_metadata(pdf_content: bytes) -> Dict[str, Any]:
        """Extract comprehensive PDF metadata.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Dictionary containing PDF metadata
        """
        try:
            pdf_io = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_io)
            
            # Extract metadata
            metadata = {}
            if reader.metadata:
                for key, value in reader.metadata.items():
                    # Clean up metadata keys (remove leading slash)
                    clean_key = key.lstrip('/')
                    metadata[clean_key] = str(value) if value else None
            
            # Basic document info
            result = {
                "page_count": len(reader.pages),
                "file_size_bytes": len(pdf_content),
                "file_size_mb": round(len(pdf_content) / (1024 * 1024), 2),
                "encrypted": reader.is_encrypted,
                "metadata": metadata
            }
            
            # Add page dimensions for first page (if available)
            if len(reader.pages) > 0:
                first_page = reader.pages[0]
                mediabox = first_page.mediabox
                result["page_dimensions"] = {
                    "width": float(mediabox.width),
                    "height": float(mediabox.height),
                    "width_inches": round(float(mediabox.width) / 72, 2),
                    "height_inches": round(float(mediabox.height) / 72, 2)
                }
            
            logger.info(f"Successfully extracted metadata for PDF ({result['page_count']} pages)")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract PDF metadata: {str(e)}")
            raise PDFProcessingError(f"Failed to extract metadata: {str(e)}")
    
    @staticmethod
    async def get_pdf_info(pdf_content: bytes) -> Dict[str, Any]:
        """Extract basic information from PDF."""
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(pdf_content)
                tmp_file.flush()
                
                reader = PdfReader(tmp_file.name)
                
                info = {
                    "pages": len(reader.pages),
                    "metadata": dict(reader.metadata) if reader.metadata else {},
                    "encrypted": reader.is_encrypted,
                    "file_size": len(pdf_content)
                }
                
                # Clean up temporary file
                os.unlink(tmp_file.name)
                
                return info
                
        except Exception as e:
            logger.error(f"Failed to extract PDF info: {str(e)}")
            raise PDFProcessingError(f"Failed to process PDF: {str(e)}")
    
    @staticmethod
    async def validate_pdf(pdf_content: bytes) -> bool:
        """Validate if content is a valid PDF."""
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(pdf_content)
                tmp_file.flush()
                
                # Try to read the PDF
                reader = PdfReader(tmp_file.name)
                
                # Basic validation - can we read pages?
                pages = len(reader.pages)
                
                # Clean up
                os.unlink(tmp_file.name)
                
                return pages > 0
                
        except Exception as e:
            logger.error(f"PDF validation failed: {str(e)}")
            return False
    
    @staticmethod
    async def get_pdf_info(pdf_content: bytes) -> Dict[str, Any]:
        """Extract basic information from PDF (legacy method - use get_metadata instead)."""
        try:
            return await PDFService.get_metadata(pdf_content)
        except Exception as e:
            logger.error(f"Failed to extract PDF info: {str(e)}")
            raise PDFProcessingError(f"Failed to process PDF: {str(e)}")
    
    @staticmethod
    async def validate_pdf(pdf_content: bytes) -> bool:
        """Validate if content is a valid PDF."""
        try:
            pdf_io = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_io)
            
            # Basic validation - can we read pages?
            pages = len(reader.pages)
            return pages > 0
            
        except Exception as e:
            logger.error(f"PDF validation failed: {str(e)}")
            return False
