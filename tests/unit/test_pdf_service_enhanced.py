"""
Enhanced unit tests for PDF service functionality.

Comprehensive tests for PDF operations, metadata extraction, validation,
split operations, merge operations, and error handling.
"""

import pytest
import io
from unittest.mock import AsyncMock, MagicMock, patch
from pypdf.errors import PdfReadError

from app.services.pdf_service import PDFService
from app.core.errors import PDFProcessingError


@pytest.mark.unit
class TestPDFService:
    """Comprehensive test suite for PDF service methods."""
    
    @pytest.mark.asyncio
    async def test_validate_pdf_valid(self, valid_pdf_bytes):
        """Test PDF validation with valid content."""
        result = await PDFService.validate_pdf(valid_pdf_bytes)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_pdf_invalid(self, invalid_pdf_bytes):
        """Test PDF validation with invalid content."""
        result = await PDFService.validate_pdf(invalid_pdf_bytes)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_pdf_empty(self):
        """Test PDF validation with empty content."""
        result = await PDFService.validate_pdf(b"")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_pdf_none(self):
        """Test PDF validation with None content."""
        with pytest.raises(TypeError):
            await PDFService.validate_pdf(None)
    
    @pytest.mark.asyncio
    async def test_get_metadata_valid_pdf(self, valid_pdf_bytes):
        """Test metadata extraction from valid PDF."""
        metadata = await PDFService.get_metadata(valid_pdf_bytes)
        
        # Check required fields
        assert "page_count" in metadata
        assert "file_size_bytes" in metadata
        assert "file_size_mb" in metadata
        assert "encrypted" in metadata
        
        # Validate field types and values
        assert isinstance(metadata["page_count"], int)
        assert metadata["page_count"] > 0
        assert metadata["file_size_bytes"] == len(valid_pdf_bytes)
        assert metadata["file_size_mb"] == round(len(valid_pdf_bytes) / (1024 * 1024), 2)
        assert isinstance(metadata["encrypted"], bool)
    
    @pytest.mark.asyncio
    async def test_get_metadata_with_document_info(self, valid_pdf_bytes):
        """Test metadata extraction includes document information when available."""
        metadata = await PDFService.get_metadata(valid_pdf_bytes)
        
        # These fields might be present depending on PDF content
        optional_fields = ["title", "author", "subject", "creator", "producer", 
                          "creation_date", "modification_date"]
        
        # At least verify the structure doesn't break with optional fields
        for field in optional_fields:
            if field in metadata:
                assert metadata[field] is not None
    
    @pytest.mark.asyncio
    async def test_get_metadata_corrupted_pdf(self, corrupted_pdf_bytes):
        """Test metadata extraction from corrupted PDF raises appropriate error."""
        with pytest.raises(PDFProcessingError, match="Failed to read PDF"):
            await PDFService.get_metadata(corrupted_pdf_bytes)
    
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
    async def test_parse_page_range_full_range(self):
        """Test parsing full document range."""
        start, end = PDFService._parse_page_range("1-10", 10)
        assert start == 0
        assert end == 9
    
    @pytest.mark.asyncio
    async def test_parse_page_range_invalid_format(self):
        """Test parsing invalid page range formats."""
        invalid_ranges = ["invalid", "1-2-3", "a-b", "", "1--3", "1-"]
        
        for invalid_range in invalid_ranges:
            with pytest.raises(PDFProcessingError, match="Invalid page range format"):
                PDFService._parse_page_range(invalid_range, 10)
    
    @pytest.mark.asyncio
    async def test_parse_page_range_out_of_bounds(self):
        """Test parsing page range that exceeds document bounds."""
        out_of_bounds_ranges = ["15", "1-15", "0", "-1", "5-15"]
        
        for range_str in out_of_bounds_ranges:
            with pytest.raises(PDFProcessingError, match="out of range"):
                PDFService._parse_page_range(range_str, 10)
    
    @pytest.mark.asyncio 
    async def test_parse_page_range_invalid_order(self):
        """Test parsing page range with start > end."""
        with pytest.raises(PDFProcessingError, match="start page.*greater than end page"):
            PDFService._parse_page_range("7-3", 10)
    
    @pytest.mark.asyncio
    async def test_split_pdf_by_ranges(self, valid_multipage_pdf_bytes):
        """Test splitting PDF by specific page ranges."""
        ranges = ["1-3", "4-6", "7-10"]
        result = await PDFService.split_pdf_by_ranges(valid_multipage_pdf_bytes, ranges)
        
        assert len(result) == 3
        assert all(isinstance(pdf_data, bytes) for pdf_data in result)
        assert all(len(pdf_data) > 0 for pdf_data in result)
    
    @pytest.mark.asyncio
    async def test_split_pdf_by_ranges_single_page(self, valid_multipage_pdf_bytes):
        """Test splitting PDF with single page ranges."""
        ranges = ["1", "5", "10"]
        result = await PDFService.split_pdf_by_ranges(valid_multipage_pdf_bytes, ranges)
        
        assert len(result) == 3
        assert all(isinstance(pdf_data, bytes) for pdf_data in result)
    
    @pytest.mark.asyncio
    async def test_split_pdf_by_ranges_invalid_range(self, valid_pdf_bytes):
        """Test splitting PDF with invalid ranges."""
        ranges = ["1-5", "15-20"]  # valid_pdf_bytes only has 3 pages
        
        with pytest.raises(PDFProcessingError):
            await PDFService.split_pdf_by_ranges(valid_pdf_bytes, ranges)
    
    @pytest.mark.asyncio
    async def test_split_pdf_into_pages(self, valid_multipage_pdf_bytes):
        """Test splitting PDF into individual pages."""
        result = await PDFService.split_pdf_into_pages(valid_multipage_pdf_bytes)
        
        # Should have 10 pages from valid_multipage_pdf_bytes
        assert len(result) == 10
        assert all(isinstance(pdf_data, bytes) for pdf_data in result)
        assert all(len(pdf_data) > 0 for pdf_data in result)
    
    @pytest.mark.asyncio
    async def test_split_pdf_into_pages_single_page(self, valid_pdf_bytes):
        """Test splitting single page PDF."""
        result = await PDFService.split_pdf_into_pages(valid_pdf_bytes)
        
        assert len(result) == 3  # valid_pdf_bytes has 3 pages
        assert all(isinstance(pdf_data, bytes) for pdf_data in result)
    
    @pytest.mark.asyncio
    async def test_split_pdf_batch(self, valid_multipage_pdf_bytes):
        """Test batch splitting PDF into chunks."""
        batch_size = 3
        result = await PDFService.split_pdf_batch(valid_multipage_pdf_bytes, batch_size)
        
        # 10 pages with batch_size 3 should give us 4 batches: 3+3+3+1
        assert len(result) == 4
        assert all(isinstance(pdf_data, bytes) for pdf_data in result)
    
    @pytest.mark.asyncio
    async def test_split_pdf_batch_exact_division(self, valid_multipage_pdf_bytes):
        """Test batch splitting with exact division."""
        batch_size = 5
        result = await PDFService.split_pdf_batch(valid_multipage_pdf_bytes, batch_size)
        
        # 10 pages with batch_size 5 should give us 2 batches
        assert len(result) == 2
        assert all(isinstance(pdf_data, bytes) for pdf_data in result)
    
    @pytest.mark.asyncio
    async def test_split_pdf_batch_invalid_size(self, valid_pdf_bytes):
        """Test batch splitting with invalid batch size."""
        with pytest.raises(PDFProcessingError, match="Batch size must be positive"):
            await PDFService.split_pdf_batch(valid_pdf_bytes, 0)
        
        with pytest.raises(PDFProcessingError, match="Batch size must be positive"):
            await PDFService.split_pdf_batch(valid_pdf_bytes, -1)
    
    @pytest.mark.asyncio
    async def test_merge_pdfs(self, valid_pdf_bytes, valid_multipage_pdf_bytes):
        """Test merging multiple PDFs."""
        pdf_files = [valid_pdf_bytes, valid_multipage_pdf_bytes]
        result = await PDFService.merge_pdfs(pdf_files)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        
        # Verify merged PDF is valid
        is_valid = await PDFService.validate_pdf(result)
        assert is_valid is True
        
        # Check that merged PDF has combined page count
        metadata = await PDFService.get_metadata(result)
        assert metadata["page_count"] == 13  # 3 + 10 pages
    
    @pytest.mark.asyncio
    async def test_merge_pdfs_single_file(self, valid_pdf_bytes):
        """Test merging single PDF file."""
        pdf_files = [valid_pdf_bytes]
        result = await PDFService.merge_pdfs(pdf_files)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        
        # Should be essentially the same as original
        is_valid = await PDFService.validate_pdf(result)
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_merge_pdfs_empty_list(self):
        """Test merging empty list of PDFs."""
        with pytest.raises(PDFProcessingError, match="No PDF files provided"):
            await PDFService.merge_pdfs([])
    
    @pytest.mark.asyncio
    async def test_merge_pdfs_with_invalid_pdf(self, valid_pdf_bytes, invalid_pdf_bytes):
        """Test merging PDFs when one is invalid."""
        pdf_files = [valid_pdf_bytes, invalid_pdf_bytes]
        
        with pytest.raises(PDFProcessingError):
            await PDFService.merge_pdfs(pdf_files)
    
    @pytest.mark.asyncio
    async def test_error_handling_with_corrupted_pdf(self, corrupted_pdf_bytes):
        """Test that corrupted PDFs raise appropriate errors."""
        # Test various operations with corrupted PDF
        with pytest.raises(PDFProcessingError):
            await PDFService.split_pdf_by_ranges(corrupted_pdf_bytes, ["1-2"])
        
        with pytest.raises(PDFProcessingError):
            await PDFService.split_pdf_into_pages(corrupted_pdf_bytes)
        
        with pytest.raises(PDFProcessingError):
            await PDFService.split_pdf_batch(corrupted_pdf_bytes, 2)
    
    @pytest.mark.asyncio
    async def test_memory_handling_large_pdf(self, large_pdf_bytes):
        """Test memory-efficient handling of large PDFs."""
        # This is more of a smoke test to ensure large PDFs don't crash
        metadata = await PDFService.get_metadata(large_pdf_bytes)
        assert metadata["page_count"] == 50
        
        # Test splitting doesn't consume excessive memory
        result = await PDFService.split_pdf_batch(large_pdf_bytes, 10)
        assert len(result) == 5  # 50 pages / 10 = 5 batches
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, valid_pdf_bytes, valid_multipage_pdf_bytes):
        """Test that PDF operations can be performed concurrently."""
        import asyncio
        
        # Run multiple operations concurrently
        tasks = [
            PDFService.get_metadata(valid_pdf_bytes),
            PDFService.get_metadata(valid_multipage_pdf_bytes),
            PDFService.split_pdf_into_pages(valid_pdf_bytes),
            PDFService.validate_pdf(valid_pdf_bytes)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All operations should succeed
        assert all(not isinstance(result, Exception) for result in results)
        assert len(results) == 4
