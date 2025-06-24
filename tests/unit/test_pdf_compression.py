"""
Unit tests for PDF compression functionality.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import io
from pypdf import PdfReader, PdfWriter

from app.services.pdf_service import PDFService
from app.core.errors import PDFProcessingError


class TestPDFCompression:
    """Test cases for PDF compression functionality."""
    
    @pytest.fixture
    def sample_pdf_content(self):
        """Create a sample PDF content for testing."""
        # Create a simple PDF with 2 pages
        writer = PdfWriter()
        
        # Add two blank pages
        writer.add_blank_page(200, 200)
        writer.add_blank_page(200, 200)
        
        # Add some metadata
        writer.add_metadata({
            '/Title': 'Test PDF',
            '/Author': 'Test Author',
            '/Subject': 'Test Subject'
        })
        
        # Write to bytes
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
    
    @pytest.fixture
    def large_pdf_content(self):
        """Create a larger PDF content for compression testing."""
        writer = PdfWriter()
        
        # Add 10 pages with some content
        for i in range(10):
            page = writer.add_blank_page(595, 842)  # A4 size
            
            # Add some text content (simulated)
            if i % 2 == 0:
                # Simulate pages with duplicate content
                writer.add_metadata({f'/Page{i}': 'Duplicate content for compression testing'})
        
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
    
    @pytest.mark.asyncio
    async def test_compress_pdf_low_level(self, sample_pdf_content):
        """Test PDF compression with low compression level."""
        # Perform compression
        compressed_content, stats = await PDFService.compress_pdf(
            sample_pdf_content,
            compression_level="low"
        )
        
        # Verify compression results
        assert isinstance(compressed_content, bytes)
        assert len(compressed_content) > 0
        
        # Verify statistics
        assert stats["original_size_bytes"] == len(sample_pdf_content)
        assert stats["compressed_size_bytes"] <= stats["original_size_bytes"]
        assert stats["reduction_percentage"] >= 0
        assert stats["compression_level"] == "low"
        assert stats["page_count"] == 2
        
        # Verify the compressed PDF is valid
        pdf_io = io.BytesIO(compressed_content)
        reader = PdfReader(pdf_io)
        assert len(reader.pages) == 2
    
    @pytest.mark.asyncio
    async def test_compress_pdf_medium_level(self, large_pdf_content):
        """Test PDF compression with medium compression level."""
        compressed_content, stats = await PDFService.compress_pdf(
            large_pdf_content,
            compression_level="medium",
            remove_duplication=True,
            compress_streams=True
        )
        
        # Verify compression results
        assert isinstance(compressed_content, bytes)
        assert stats["compression_level"] == "medium"
        assert stats["settings"]["remove_duplication"] is True
        assert stats["settings"]["compress_streams"] is True
        
        # Medium compression should achieve better reduction than low
        assert stats["reduction_percentage"] > 0
        
        # Verify the compressed PDF maintains all pages
        pdf_io = io.BytesIO(compressed_content)
        reader = PdfReader(pdf_io)
        assert len(reader.pages) == 10
    
    @pytest.mark.asyncio
    async def test_compress_pdf_high_level(self, large_pdf_content):
        """Test PDF compression with high compression level."""
        compressed_content, stats = await PDFService.compress_pdf(
            large_pdf_content,
            compression_level="high",
            remove_duplication=True,
            compress_streams=True,
            remove_images=False  # Don't remove images in this test
        )
        
        # Verify compression results
        assert isinstance(compressed_content, bytes)
        assert stats["compression_level"] == "high"
        
        # High compression should achieve significant reduction
        assert stats["reduction_percentage"] > 0
        assert stats["compressed_size_bytes"] < stats["original_size_bytes"]
    
    @pytest.mark.asyncio
    async def test_compress_pdf_invalid_level(self, sample_pdf_content):
        """Test compression with invalid compression level."""
        with pytest.raises(PDFProcessingError) as exc_info:
            await PDFService.compress_pdf(
                sample_pdf_content,
                compression_level="invalid"
            )
        
        assert "Invalid compression level" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_compress_empty_pdf(self):
        """Test compression with empty PDF content."""
        # Create PDF with no pages
        writer = PdfWriter()
        output = io.BytesIO()
        writer.write(output)
        empty_pdf = output.getvalue()
        
        with pytest.raises(PDFProcessingError) as exc_info:
            await PDFService.compress_pdf(empty_pdf)
        
        assert "PDF has no pages" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_compress_invalid_pdf(self):
        """Test compression with invalid PDF content."""
        invalid_content = b"This is not a valid PDF"
        
        with pytest.raises(PDFProcessingError):
            await PDFService.compress_pdf(invalid_content)
    
    @pytest.mark.asyncio
    async def test_compression_preview(self, sample_pdf_content):
        """Test compression preview functionality."""
        preview = await PDFService.get_compression_preview(
            sample_pdf_content,
            compression_level="medium"
        )
        
        # Verify preview structure
        assert "original_size_bytes" in preview
        assert "estimated_compressed_size_bytes" in preview
        assert "estimated_reduction_percentage" in preview
        assert "page_count" in preview
        assert "has_images" in preview
        assert "recommendations" in preview
        
        # Verify preview values
        assert preview["original_size_bytes"] == len(sample_pdf_content)
        assert preview["page_count"] == 2
        assert preview["compression_level"] == "medium"
        assert isinstance(preview["recommendations"], list)
    
    @pytest.mark.asyncio
    async def test_compression_preview_with_images(self):
        """Test compression preview with PDF containing images."""
        # Create PDF with simulated image content
        writer = PdfWriter()
        page = writer.add_blank_page(595, 842)
        
        # Note: In a real test, we would add actual images
        # For this test, we're simulating the behavior
        
        output = io.BytesIO()
        writer.write(output)
        pdf_content = output.getvalue()
        
        preview = await PDFService.get_compression_preview(
            pdf_content,
            compression_level="high"
        )
        
        # Verify recommendations based on content
        assert isinstance(preview["recommendations"], list)
        assert preview["compression_level"] == "high"
    
    @pytest.mark.asyncio
    async def test_compression_preview_large_file(self):
        """Test compression preview with large file."""
        # Create a large PDF (> 10MB simulation)
        writer = PdfWriter()
        for _ in range(100):
            writer.add_blank_page(595, 842)
        
        output = io.BytesIO()
        writer.write(output)
        large_pdf = output.getvalue()
        
        # In real scenario, this would be > 10MB
        preview = await PDFService.get_compression_preview(large_pdf)
        
        # Should recommend compression for large files
        assert preview["page_count"] == 100
        assert len(preview["recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_compression_stats_accuracy(self, sample_pdf_content):
        """Test that compression statistics are accurate."""
        compressed_content, stats = await PDFService.compress_pdf(
            sample_pdf_content,
            compression_level="medium"
        )
        
        # Verify size calculations
        assert stats["original_size_bytes"] == len(sample_pdf_content)
        assert stats["compressed_size_bytes"] == len(compressed_content)
        assert stats["reduction_bytes"] == stats["original_size_bytes"] - stats["compressed_size_bytes"]
        
        # Verify percentage calculation
        expected_percentage = (stats["reduction_bytes"] / stats["original_size_bytes"]) * 100
        assert abs(stats["reduction_percentage"] - expected_percentage) < 0.01
        
        # Verify MB conversions
        assert stats["original_size_mb"] == round(len(sample_pdf_content) / (1024 * 1024), 2)
        assert stats["compressed_size_mb"] == round(len(compressed_content) / (1024 * 1024), 2)
    
    @pytest.mark.asyncio
    async def test_compression_preserves_content(self, sample_pdf_content):
        """Test that compression preserves PDF content and structure."""
        # Get original PDF info
        original_reader = PdfReader(io.BytesIO(sample_pdf_content))
        original_pages = len(original_reader.pages)
        original_metadata = original_reader.metadata
        
        # Compress PDF
        compressed_content, _ = await PDFService.compress_pdf(
            sample_pdf_content,
            compression_level="high"
        )
        
        # Verify compressed PDF
        compressed_reader = PdfReader(io.BytesIO(compressed_content))
        assert len(compressed_reader.pages) == original_pages
        
        # Metadata should be preserved
        if original_metadata:
            assert compressed_reader.metadata is not None