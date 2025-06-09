"""
Unit tests for file validation functionality.

Tests file upload validation, file size limits, MIME type checking,
and security validation.
"""

import pytest
from io import BytesIO
from unittest.mock import patch

from app.utils.file_utils import validate_file_upload, get_file_info
from app.core.errors import FileValidationError
from fastapi import UploadFile


@pytest.mark.unit
class TestFileValidation:
    """Test file validation utilities."""
    
    def create_upload_file(self, content: bytes, filename: str, content_type: str = "application/pdf") -> UploadFile:
        """Helper to create UploadFile objects for testing."""
        file_obj = BytesIO(content)
        return UploadFile(
            filename=filename,
            file=file_obj,
            content_type=content_type
        )
    
    @pytest.mark.asyncio
    async def test_validate_file_upload_valid_pdf(self, valid_pdf_bytes):
        """Test validation of valid PDF upload."""
        upload_file = self.create_upload_file(valid_pdf_bytes, "test.pdf")
        
        # Should not raise any exception
        await validate_file_upload(upload_file)
    
    @pytest.mark.asyncio
    async def test_validate_file_upload_invalid_extension(self, valid_pdf_bytes):
        """Test validation rejects invalid file extensions."""
        upload_file = self.create_upload_file(valid_pdf_bytes, "test.txt")
        
        with pytest.raises(FileValidationError, match="Invalid file extension"):
            await validate_file_upload(upload_file)
    
    @pytest.mark.asyncio
    async def test_validate_file_upload_no_extension(self, valid_pdf_bytes):
        """Test validation rejects files without extension."""
        upload_file = self.create_upload_file(valid_pdf_bytes, "test")
        
        with pytest.raises(FileValidationError, match="No file extension"):
            await validate_file_upload(upload_file)
    
    @pytest.mark.asyncio
    async def test_validate_file_upload_wrong_mime_type(self, valid_pdf_bytes):
        """Test validation checks MIME type."""
        upload_file = self.create_upload_file(valid_pdf_bytes, "test.pdf", "text/plain")
        
        with pytest.raises(FileValidationError, match="Invalid MIME type"):
            await validate_file_upload(upload_file)
    
    @pytest.mark.asyncio
    async def test_validate_file_upload_file_too_large(self):
        """Test validation rejects files that are too large."""
        # Create a file larger than the limit (assume 50MB limit)
        large_content = b"x" * (51 * 1024 * 1024)  # 51 MB
        upload_file = self.create_upload_file(large_content, "large.pdf")
        
        with pytest.raises(FileValidationError, match="File too large"):
            await validate_file_upload(upload_file)
    
    @pytest.mark.asyncio
    async def test_validate_file_upload_empty_file(self):
        """Test validation rejects empty files."""
        upload_file = self.create_upload_file(b"", "empty.pdf")
        
        with pytest.raises(FileValidationError, match="Empty file"):
            await validate_file_upload(upload_file)
    
    @pytest.mark.asyncio
    async def test_validate_file_upload_no_filename(self, valid_pdf_bytes):
        """Test validation handles missing filename."""
        upload_file = self.create_upload_file(valid_pdf_bytes, None)
        
        with pytest.raises(FileValidationError, match="No filename"):
            await validate_file_upload(upload_file)
    
    @pytest.mark.asyncio
    async def test_validate_file_upload_suspicious_filename(self, valid_pdf_bytes):
        """Test validation rejects suspicious filenames."""
        suspicious_names = [
            "../../../etc/passwd.pdf",
            "..\\..\\windows\\system32\\config.pdf",
            "test\x00.pdf",
            "con.pdf",  # Windows reserved name
            "prn.pdf",  # Windows reserved name
        ]
        
        for filename in suspicious_names:
            upload_file = self.create_upload_file(valid_pdf_bytes, filename)
            with pytest.raises(FileValidationError, match="Invalid filename"):
                await validate_file_upload(upload_file)
    
    @pytest.mark.asyncio
    async def test_get_file_info_valid_file(self, valid_pdf_bytes):
        """Test getting file information from valid upload."""
        upload_file = self.create_upload_file(valid_pdf_bytes, "test.pdf")
        
        info = await get_file_info(upload_file)
        
        assert info["filename"] == "test.pdf"
        assert info["size"] == len(valid_pdf_bytes)
        assert info["content_type"] == "application/pdf"
        assert info["extension"] == ".pdf"
    
    @pytest.mark.asyncio
    async def test_get_file_info_unicode_filename(self, valid_pdf_bytes):
        """Test getting file information with unicode filename."""
        unicode_filename = "测试文件.pdf"
        upload_file = self.create_upload_file(valid_pdf_bytes, unicode_filename)
        
        info = await get_file_info(upload_file)
        
        assert info["filename"] == unicode_filename
        assert info["extension"] == ".pdf"
    
    @pytest.mark.asyncio
    async def test_file_content_type_detection(self, valid_pdf_bytes, invalid_pdf_bytes):
        """Test content type detection from file content."""
        # Valid PDF should be detected correctly
        valid_upload = self.create_upload_file(valid_pdf_bytes, "test.pdf")
        await validate_file_upload(valid_upload)  # Should pass
        
        # Invalid content with PDF extension should fail validation
        invalid_upload = self.create_upload_file(invalid_pdf_bytes, "fake.pdf")
        with pytest.raises(FileValidationError):
            await validate_file_upload(invalid_upload)
    
    @pytest.mark.asyncio
    async def test_validate_multiple_files(self, valid_pdf_bytes, valid_multipage_pdf_bytes):
        """Test validation of multiple files."""
        files = [
            self.create_upload_file(valid_pdf_bytes, "file1.pdf"),
            self.create_upload_file(valid_multipage_pdf_bytes, "file2.pdf")
        ]
        
        # Should validate all files without error
        for file in files:
            await validate_file_upload(file)
    
    @pytest.mark.asyncio
    async def test_validate_file_with_special_characters(self, valid_pdf_bytes):
        """Test validation of files with special characters in name."""
        # These should be valid
        valid_names = [
            "file-name.pdf",
            "file_name.pdf",
            "file name.pdf",
            "file123.pdf",
            "FILE.PDF"
        ]
        
        for filename in valid_names:
            upload_file = self.create_upload_file(valid_pdf_bytes, filename)
            await validate_file_upload(upload_file)  # Should not raise
    
    @pytest.mark.asyncio
    async def test_case_insensitive_extension_validation(self, valid_pdf_bytes):
        """Test that file extension validation is case insensitive."""
        extensions = ["test.PDF", "test.Pdf", "test.pdF"]
        
        for filename in extensions:
            upload_file = self.create_upload_file(valid_pdf_bytes, filename)
            await validate_file_upload(upload_file)  # Should not raise
    
    @pytest.mark.asyncio
    async def test_security_scan_placeholder(self, valid_pdf_bytes):
        """Test security scanning functionality (placeholder for future implementation)."""
        upload_file = self.create_upload_file(valid_pdf_bytes, "test.pdf")
        
        # For now, just ensure validation passes
        # In the future, this could test for malicious PDF content
        await validate_file_upload(upload_file)
    
    @pytest.mark.asyncio
    async def test_concurrent_file_validation(self, valid_pdf_bytes, valid_multipage_pdf_bytes):
        """Test concurrent file validation doesn't cause issues."""
        import asyncio
        
        files = [
            self.create_upload_file(valid_pdf_bytes, f"file{i}.pdf")
            for i in range(5)
        ]
        
        # Validate all files concurrently
        tasks = [validate_file_upload(file) for file in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All validations should succeed
        assert all(result is None for result in results)


@pytest.mark.unit
class TestFileUtilities:
    """Test file utility functions."""
    
    def test_normalize_filename(self):
        """Test filename normalization."""
        from app.utils.file_utils import normalize_filename
        
        test_cases = [
            ("test file.pdf", "test_file.pdf"),
            ("Test File (1).pdf", "Test_File__1_.pdf"),
            ("file-name.pdf", "file-name.pdf"),
            ("file_name.pdf", "file_name.pdf"),
        ]
        
        for input_name, expected in test_cases:
            result = normalize_filename(input_name)
            assert result == expected
    
    def test_get_safe_filename(self):
        """Test safe filename generation."""
        from app.utils.file_utils import get_safe_filename
        
        unsafe_names = [
            "../../../etc/passwd",
            "con.pdf",
            "file\x00name.pdf",
            "very" + "long" * 100 + "name.pdf"
        ]
        
        for unsafe_name in unsafe_names:
            safe_name = get_safe_filename(unsafe_name)
            assert isinstance(safe_name, str)
            assert len(safe_name) > 0
            assert "../" not in safe_name
            assert "\x00" not in safe_name
    
    def test_calculate_file_hash(self, valid_pdf_bytes):
        """Test file hash calculation for duplicate detection."""
        from app.utils.file_utils import calculate_file_hash
        
        hash1 = calculate_file_hash(valid_pdf_bytes)
        hash2 = calculate_file_hash(valid_pdf_bytes)
        
        # Same content should produce same hash
        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) > 0
    
    def test_estimate_processing_time(self, valid_pdf_bytes, large_pdf_bytes):
        """Test processing time estimation."""
        from app.utils.file_utils import estimate_processing_time
        
        small_time = estimate_processing_time(len(valid_pdf_bytes))
        large_time = estimate_processing_time(len(large_pdf_bytes))
        
        # Larger files should have longer estimated processing time
        assert large_time > small_time
        assert small_time > 0
        assert isinstance(small_time, (int, float))
