"""
Tests for file utility functions.

Tests file validation, sanitization, and temporary file handling.
"""

import pytest
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile
from io import BytesIO

from app.utils.file_utils import (
    validate_pdf_file,
    sanitize_filename,
    save_temp_file,
    cleanup_temp_file,
    get_file_info
)
from app.core.errors import FileSizeError, FileFormatError


class TestSanitizeFilename:
    """Test filename sanitization."""
    
    def test_sanitize_valid_filename(self):
        """Test sanitizing a valid filename."""
        result = sanitize_filename("document.pdf")
        assert result == "document.pdf"
    
    def test_sanitize_special_characters(self):
        """Test sanitizing filename with special characters."""
        result = sanitize_filename("my<>document|?.pdf")
        assert result == "my__document__.pdf"
    
    def test_sanitize_path_traversal(self):
        """Test sanitizing filename with path traversal attempt."""
        result = sanitize_filename("../../../etc/passwd.pdf")
        assert result == "passwd.pdf"  # os.path.basename removes the path
    
    def test_sanitize_empty_filename(self):
        """Test sanitizing empty filename."""
        result = sanitize_filename("")
        assert result.startswith("upload_")
        assert result.endswith(".pdf")

    def test_sanitize_none_filename(self):
        """Test sanitizing None filename."""
        result = sanitize_filename(None)
        assert result.startswith("upload_")
        assert result.endswith(".pdf")
    
    def test_sanitize_long_filename(self):
        """Test sanitizing very long filename."""
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".pdf")


class TestValidatePDFFile:
    """Test PDF file validation."""
    
    def create_mock_file(self, filename: str, content: bytes, content_type: str = "application/pdf") -> UploadFile:
        """Create a mock UploadFile for testing."""
        file_obj = BytesIO(content)
        upload_file = UploadFile(filename=filename, file=file_obj)
        
        # Mock the content_type property directly using property
        type(upload_file).content_type = MagicMock(return_value=content_type)
        upload_file.content_type = content_type
        
        # Mock the async methods
        async def mock_read():
            return content
        
        async def mock_seek(position):
            file_obj.seek(position)
        
        upload_file.read = mock_read
        upload_file.seek = mock_seek
        
        return upload_file
    
    @pytest.mark.asyncio
    async def test_validate_valid_pdf(self):
        """Test validating a valid PDF file."""
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF'
        file = self.create_mock_file("test.pdf", pdf_content)
        
        result = await validate_pdf_file(file)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_no_filename(self):
        """Test validation with no filename."""
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF'
        file = self.create_mock_file(None, pdf_content)
        
        with pytest.raises(FileFormatError, match="No filename provided"):
            await validate_pdf_file(file)

    @pytest.mark.asyncio
    async def test_validate_wrong_extension(self):
        """Test validation with wrong file extension."""
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF'
        file = self.create_mock_file("test.txt", pdf_content)
        
        with pytest.raises(FileFormatError, match="Invalid file format"):
            await validate_pdf_file(file)
    
    @pytest.mark.asyncio
    async def test_validate_wrong_content_type(self):
        """Test validation with wrong content type."""
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF'
        file = self.create_mock_file("test.pdf", pdf_content, "text/plain")
        
        with pytest.raises(FileFormatError, match="Invalid content type"):
            await validate_pdf_file(file)
    
    @pytest.mark.asyncio
    async def test_validate_empty_file(self):
        """Test validation with empty file."""
        file = self.create_mock_file("test.pdf", b"")
        
        with pytest.raises(FileFormatError, match="Empty file uploaded"):
            await validate_pdf_file(file)
    
    @pytest.mark.asyncio
    async def test_validate_invalid_pdf_header(self):
        """Test validation with invalid PDF header."""
        file = self.create_mock_file("test.pdf", b"Not a PDF file")
        
        with pytest.raises(FileFormatError, match="missing PDF header"):
            await validate_pdf_file(file)
    
    @pytest.mark.asyncio
    async def test_validate_missing_eof(self):
        """Test validation with missing EOF marker."""
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n'
        file = self.create_mock_file("test.pdf", pdf_content)
        
        with pytest.raises(FileFormatError, match="missing EOF marker"):
            await validate_pdf_file(file)
    
    @pytest.mark.asyncio
    async def test_validate_large_file(self):
        """Test validation with file exceeding size limit."""
        # Create a large PDF content (>50MB)
        large_content = b'%PDF-1.4\n' + b'A' * (51 * 1024 * 1024) + b'\n%%EOF'
        file = self.create_mock_file("large.pdf", large_content)
        
        with pytest.raises(FileSizeError, match="File too large"):
            await validate_pdf_file(file)
