"""
Tests for PDF service functionality.

Tests PDF split operations, metadata extraction, and error handling.
"""

import pytest
import io
from unittest.mock import AsyncMock, MagicMock

from app.services.pdf_service import PDFService
from app.core.errors import PDFProcessingError


class TestPDFService:
    """Test PDF service methods."""
    
    def create_mock_pdf_content(self, pages: int = 3) -> bytes:
        """Create a simple mock PDF content for testing."""
        # This is a minimal valid PDF structure
        pdf_content = b'%PDF-1.4\n'
        
        # Add catalog and pages
        pdf_content += b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
        pdf_content += f'2 0 obj\n<< /Type /Pages /Kids ['.encode()
        
        for i in range(pages):
            pdf_content += f' {i+3} 0 R'.encode()
        
        pdf_content += f'] /Count {pages} >>\nendobj\n'.encode()
        
        # Add individual pages
        for i in range(pages):
            page_num = i + 3
            pdf_content += f'{page_num} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n'.encode()
        
        pdf_content += b'xref\n'
        pdf_content += f'0 {pages + 3}\n'.encode()
        pdf_content += b'0000000000 65535 f \n'
        
        # Simple xref entries
        for i in range(pages + 2):
            pdf_content += f'{str(i*20).zfill(10)} 00000 n \n'.encode()
        
        pdf_content += b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'
        pdf_content += f'{len(pdf_content)}\n'.encode()
        pdf_content += b'%%EOF'
        
        return pdf_content
    
    @pytest.mark.asyncio
    async def test_parse_page_range_single_page(self):
        """Test parsing single page range."""
        start, end = PDFService._parse_page_range("5", 10)
        assert start == 4  # 0-based indexing
        assert end == 4
    
    @pytest.mark.asyncio
    async def test_parse_page_range_multi_page(self):
        """Test parsing multi-page range."""
        start, end = PDFService._parse_page_range("3-7", 10)
        assert start == 2  # 0-based indexing
        assert end == 6
    
    @pytest.mark.asyncio
    async def test_parse_page_range_invalid_format(self):
        """Test parsing invalid page range format."""
        with pytest.raises(PDFProcessingError, match="Invalid page range format"):
            PDFService._parse_page_range("invalid", 10)
    
    @pytest.mark.asyncio
    async def test_parse_page_range_out_of_bounds(self):
        """Test parsing page range that exceeds document bounds."""
        with pytest.raises(PDFProcessingError, match="out of range"):
            PDFService._parse_page_range("15", 10)
    
    @pytest.mark.asyncio 
    async def test_parse_page_range_invalid_order(self):
        """Test parsing page range with start > end."""
        with pytest.raises(PDFProcessingError, match="start page.*greater than end page"):
            PDFService._parse_page_range("7-3", 10)
    
    @pytest.mark.asyncio
    async def test_validate_pdf_valid(self):
        """Test PDF validation with valid content."""
        pdf_content = self.create_mock_pdf_content(2)
        result = await PDFService.validate_pdf(pdf_content)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_pdf_invalid(self):
        """Test PDF validation with invalid content."""
        invalid_content = b"This is not a PDF"
        result = await PDFService.validate_pdf(invalid_content)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_metadata(self):
        """Test metadata extraction."""
        pdf_content = self.create_mock_pdf_content(5)
        metadata = await PDFService.get_metadata(pdf_content)
        
        assert "page_count" in metadata
        assert "file_size_bytes" in metadata
        assert "file_size_mb" in metadata
        assert "encrypted" in metadata
        assert metadata["page_count"] > 0
        assert metadata["file_size_bytes"] == len(pdf_content)
