"""
Unit tests for OCR S3 processing functionality.

Tests base64 image detection, S3 upload logic, and URL replacement
in OCR responses with comprehensive mocking.
"""

import pytest
import json
import base64
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import dataclass
from typing import Dict, Any

from app.utils.ocr_s3_processor import (
    Base64Image, Base64ImageDetector, OCRImageUploader, 
    OCRResponseProcessor
)
from app.models.ocr_models import S3Config, OCRImageWithS3
from app.utils.s3_client import S3Client, S3UploadError
from pydantic import SecretStr

class TestBase64Image:
    """Test Base64Image dataclass."""
    
    def test_base64_image_creation(self):
        """Test creating Base64Image object."""
        content = b"fake image data"
        b64_content = base64.b64encode(content).decode()
        
        img = Base64Image(
            raw_data=f"data:image/png;base64,{b64_content}",
            format="png",
            base64_content=b64_content,
            binary_content=content,
            size_bytes=len(content),
            source_location="test.images[0]",
            image_id="img_001",
            page_number=1
        )
        
        assert img.format == "png"
        assert img.size_bytes == len(content)
        assert img.image_id == "img_001"
        assert img.page_number == 1

class TestBase64ImageDetector:
    """Test Base64ImageDetector functionality."""
    
    @pytest.fixture
    def detector(self):
        """Create detector with test parameters."""
        return Base64ImageDetector(min_size_bytes=50, max_size_mb=1)
    
    def test_detect_data_url_images(self, detector):
        """Test detection of data URL format images."""
        # Create test image data
        test_content = b"fake PNG image data" * 10  # Make it larger than min size
        b64_content = base64.b64encode(test_content).decode()
        
        response = {
            "text": "Some text",
            "image_data": f"data:image/png;base64,{b64_content}",
            "more_text": "More content"
        }
        
        images = detector.detect_images_in_response(response)
        
        assert len(images) == 1
        assert images[0].format == "png"
        assert images[0].binary_content == test_content
        assert images[0].size_bytes == len(test_content)
    
    def test_detect_structured_images(self, detector):
        """Test detection of images in structured format."""
        test_content = b"fake image content for testing" * 5
        b64_content = base64.b64encode(test_content).decode()
        
        response = {
            "images": [
                {
                    "id": "img_001",
                    "data": f"data:image/jpeg;base64,{b64_content}",
                    "page_number": 1,
                    "sequence_number": 1
                }
            ]
        }
        
        images = detector.detect_images_in_response(response)
        
        assert len(images) == 1
        assert images[0].image_id == "img_001"
        assert images[0].format == "jpeg"
        assert images[0].page_number == 1
        assert images[0].sequence_number == 1
    
    def test_detect_pages_with_images(self, detector):
        """Test detection of images in pages structure."""
        test_content = b"test image data" * 10
        b64_content = base64.b64encode(test_content).decode()
        
        response = {
            "pages": [
                {
                    "page_number": 1,
                    "images": [
                        {
                            "id": "page1_img1",
                            "base64_data": b64_content,
                            "format": "png"
                        }
                    ]
                },
                {
                    "page_number": 2,
                    "images": [
                        {
                            "id": "page2_img1",
                            "content": f"data:image/gif;base64,{b64_content}"
                        }
                    ]
                }
            ]
        }
        
        images = detector.detect_images_in_response(response)
        
        assert len(images) == 2
        assert images[0].image_id == "page1_img1"
        assert images[0].format == "png"
        assert images[1].image_id == "page2_img1"
        assert images[1].format == "gif"
    
    def test_size_filtering(self, detector):
        """Test that images are filtered by size constraints."""
        # Too small image
        small_content = b"tiny"
        small_b64 = base64.b64encode(small_content).decode()
        
        # Good size image  
        good_content = b"good size image content" * 5
        good_b64 = base64.b64encode(good_content).decode()
        
        # Too large image (over 1MB limit)
        large_content = b"x" * (2 * 1024 * 1024)  # 2MB
        large_b64 = base64.b64encode(large_content).decode()
        
        response = {
            "images": [
                {"id": "small", "data": f"data:image/png;base64,{small_b64}"},
                {"id": "good", "data": f"data:image/png;base64,{good_b64}"},
                {"id": "large", "data": f"data:image/png;base64,{large_b64}"}
            ]
        }
        
        images = detector.detect_images_in_response(response)
        
        # Only the good-sized image should be detected
        assert len(images) == 1
        assert images[0].image_id == "good"
    
    def test_is_base64_image(self, detector):
        """Test base64 image validation."""
        # Valid base64 PNG content
        png_content = b'\x89PNG\r\n\x1a\n' + b'fake png data' * 10
        valid_b64 = base64.b64encode(png_content).decode()
        
        assert detector._is_base64_image(valid_b64) is True
        
        # Too short
        assert detector._is_base64_image("short") is False
        
        # Invalid base64
        assert detector._is_base64_image("not!base64!content!") is False
        
        # Valid base64 but not image content
        text_b64 = base64.b64encode(b"just text content").decode()
        assert detector._is_base64_image(text_b64) is False
    
    def test_has_image_signature(self, detector):
        """Test image signature detection."""
        # PNG signature
        png_data = b'\x89PNG\r\n\x1a\n' + b'fake png data'
        assert detector._has_image_signature(png_data) is True
        
        # JPEG signature
        jpeg_data = b'\xff\xd8\xff' + b'fake jpeg data'
        assert detector._has_image_signature(jpeg_data) is True
        
        # GIF signature
        gif_data = b'GIF87a' + b'fake gif data'
        assert detector._has_image_signature(gif_data) is True
        
        # Not an image
        text_data = b'just plain text'
        assert detector._has_image_signature(text_data) is False
        
        # Too short
        short_data = b'short'
        assert detector._has_image_signature(short_data) is False

class TestOCRImageUploader:
    """Test OCRImageUploader functionality."""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Create mock S3 client."""
        client = Mock(spec=S3Client)
        return client
    
    @pytest.fixture
    def uploader(self, mock_s3_client):
        """Create OCR image uploader with mock S3 client."""
        return OCRImageUploader(mock_s3_client, "test-prefix")
    
    @pytest.fixture
    def sample_base64_image(self):
        """Create sample Base64Image for testing."""
        content = b"fake image content for testing"
        b64_content = base64.b64encode(content).decode()
        
        return Base64Image(
            raw_data=f"data:image/png;base64,{b64_content}",
            format="png",
            base64_content=b64_content,
            binary_content=content,
            size_bytes=len(content),
            source_location="test.images[0]",
            image_id="test_img_001",
            page_number=1,
            sequence_number=1
        )
    
    @pytest.mark.asyncio
    async def test_upload_single_image_success(self, uploader, mock_s3_client, sample_base64_image):
        """Test successful single image upload."""
        # Mock S3 upload response
        mock_s3_client.upload_file.return_value = ("test-prefix/img_001.png", "https://bucket.s3.amazonaws.com/test-prefix/img_001.png")
        
        result = await uploader._upload_single_image(sample_base64_image)
        
        assert isinstance(result, OCRImageWithS3)
        assert result.s3_url == "https://bucket.s3.amazonaws.com/test-prefix/img_001.png"
        assert result.s3_object_key == "test-prefix/img_001.png"
        assert result.format == "png"
        assert result.file_size_bytes == len(sample_base64_image.binary_content)
        
        # Verify S3 client was called correctly
        mock_s3_client.upload_file.assert_called_once()
        call_args = mock_s3_client.upload_file.call_args
        assert call_args[1]['content'] == sample_base64_image.binary_content
        assert 'metadata' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_upload_single_image_failure(self, uploader, mock_s3_client, sample_base64_image):
        """Test single image upload failure."""
        # Mock S3 upload failure
        mock_s3_client.upload_file.side_effect = S3UploadError("Upload failed")
        
        with pytest.raises(S3UploadError, match="Upload failed"):
            await uploader._upload_single_image(sample_base64_image)
    
    @pytest.mark.asyncio
    async def test_upload_images_concurrently_success(self, uploader, mock_s3_client):
        """Test concurrent upload of multiple images."""
        # Create multiple test images
        images = []
        for i in range(3):
            content = f"image content {i}".encode()
            b64_content = base64.b64encode(content).decode()
            
            img = Base64Image(
                raw_data=f"data:image/png;base64,{b64_content}",
                format="png",
                base64_content=b64_content,
                binary_content=content,
                size_bytes=len(content),
                source_location=f"test.images[{i}]",
                image_id=f"img_{i:03d}"
            )
            images.append(img)
        
        # Mock successful uploads
        mock_s3_client.upload_file.side_effect = [
            (f"test-prefix/img_{i:03d}.png", f"https://bucket.s3.amazonaws.com/test-prefix/img_{i:03d}.png")
            for i in range(3)
        ]
        
        successful, failed = await uploader.upload_images_concurrently(images, max_concurrent=2)
        
        assert len(successful) == 3
        assert len(failed) == 0
        assert mock_s3_client.upload_file.call_count == 3
        
        # Verify all successful uploads are OCRImageWithS3 objects
        for upload in successful:
            assert isinstance(upload, OCRImageWithS3)
            assert upload.s3_url.startswith("https://")
    
    @pytest.mark.asyncio
    async def test_upload_images_concurrently_partial_failure(self, uploader, mock_s3_client):
        """Test concurrent upload with some failures."""
        # Create test images
        images = []
        for i in range(3):
            content = f"image content {i}".encode()
            b64_content = base64.b64encode(content).decode()
            
            img = Base64Image(
                raw_data=f"data:image/png;base64,{b64_content}",
                format="png",
                base64_content=b64_content,
                binary_content=content,
                size_bytes=len(content),
                source_location=f"test.images[{i}]",
                image_id=f"img_{i:03d}"
            )
            images.append(img)
        
        # Mock mixed results (first succeeds, second fails, third succeeds)
        def upload_side_effect(*args, **kwargs):
            call_count = mock_s3_client.upload_file.call_count
            if call_count == 2:  # Second call fails
                raise S3UploadError("Upload failed for image 1")
            return (f"test-prefix/img.png", "https://bucket.s3.amazonaws.com/test-prefix/img.png")
        
        mock_s3_client.upload_file.side_effect = upload_side_effect
        
        successful, failed = await uploader.upload_images_concurrently(images)
        
        assert len(successful) == 2
        assert len(failed) == 1
        assert failed[0].image_id == "img_001"  # The middle one that failed
    
    def test_generate_filename(self, uploader):
        """Test filename generation."""
        # Test with image ID
        img_with_id = Mock()
        img_with_id.image_id = "test_image_123"
        img_with_id.format = "png"
        
        filename = uploader._generate_filename(img_with_id)
        assert filename == "img_test_image_123.png"
        
        # Test without image ID (uses content hash)
        img_without_id = Mock()
        img_without_id.image_id = None
        img_without_id.format = "jpeg"
        img_without_id.binary_content = b"test content"
        
        filename = uploader._generate_filename(img_without_id)
        assert filename.startswith("img_")
        assert filename.endswith(".jpeg")
        assert len(filename.split('.')[0]) > 10  # Should include hash
    
    def test_get_content_type(self, uploader):
        """Test content type detection."""
        assert uploader._get_content_type("png") == "image/png"
        assert uploader._get_content_type("jpeg") == "image/jpeg"
        assert uploader._get_content_type("jpg") == "image/jpeg"
        assert uploader._get_content_type("gif") == "image/gif"
        assert uploader._get_content_type("unknown") == "application/octet-stream"
        assert uploader._get_content_type(None) == "application/octet-stream"

class TestOCRResponseProcessor:
    """Test OCRResponseProcessor end-to-end functionality."""
    
    @pytest.fixture
    def s3_config(self):
        """Create test S3 configuration."""
        return S3Config(
            access_key="test_access_key",
            secret_key=SecretStr("test_secret_key"),
            bucket_name="test-bucket",
            region="us-east-1"
        )
    
    @pytest.fixture
    def mock_processor(self, s3_config):
        """Create processor with mocked S3 client."""
        with patch('app.utils.ocr_s3_processor.create_s3_client') as mock_create:
            mock_s3_client = Mock(spec=S3Client)
            mock_create.return_value = mock_s3_client
            
            processor = OCRResponseProcessor(s3_config, "test-prefix")
            processor.s3_client = mock_s3_client  # Ensure we can access the mock
            return processor
    
    @pytest.mark.asyncio
    async def test_process_ocr_response_success(self, mock_processor):
        """Test successful OCR response processing with S3 upload."""
        # Create test OCR response with base64 image
        test_content = b"fake image data for testing" * 10
        b64_content = base64.b64encode(test_content).decode()
        
        ocr_response = {
            "text": "Extracted text content",
            "images": [
                {
                    "id": "img_001",
                    "data": f"data:image/png;base64,{b64_content}",
                    "page_number": 1
                }
            ],
            "metadata": {"pages": 1}
        }
        
        # Mock S3 client methods
        mock_processor.s3_client.validate_connection.return_value = {"status": "validated"}
        mock_processor.s3_client.upload_file.return_value = (
            "test-prefix/img_001.png",
            "https://test-bucket.s3.amazonaws.com/test-prefix/img_001.png"
        )
        
        modified_response, upload_info = await mock_processor.process_ocr_response(
            ocr_response, 
            fallback_to_base64=True,
            upload_timeout_seconds=30
        )
        
        # Verify upload info
        assert upload_info['images_detected'] == 1
        assert upload_info['images_uploaded'] == 1
        assert upload_info['images_failed'] == 0
        assert upload_info['upload_success_rate'] == 1.0
        assert upload_info['fallback_used'] is False
        
        # Verify S3 client was called
        mock_processor.s3_client.validate_connection.assert_called_once()
        mock_processor.s3_client.upload_file.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_ocr_response_no_images(self, mock_processor):
        """Test OCR response processing with no images."""
        ocr_response = {
            "text": "Just text, no images",
            "metadata": {"pages": 1}
        }
        
        # Mock S3 connection validation
        mock_processor.s3_client.validate_connection.return_value = {"status": "validated"}
        
        modified_response, upload_info = await mock_processor.process_ocr_response(ocr_response)
        
        assert upload_info['images_detected'] == 0
        assert upload_info['images_uploaded'] == 0
        assert modified_response == ocr_response  # Should be unchanged
        
        # S3 validation should still be called, but no uploads
        mock_processor.s3_client.validate_connection.assert_called_once()
        mock_processor.s3_client.upload_file.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_ocr_response_s3_connection_failure_with_fallback(self, mock_processor):
        """Test S3 connection failure with fallback enabled."""
        test_content = b"fake image data"
        b64_content = base64.b64encode(test_content).decode()
        
        ocr_response = {
            "text": "Test content",
            "images": [{"id": "img_001", "data": f"data:image/png;base64,{b64_content}"}]
        }
        
        # Mock S3 connection failure
        from app.utils.s3_client import S3ConnectionError
        mock_processor.s3_client.validate_connection.side_effect = S3ConnectionError("Connection failed")
        
        modified_response, upload_info = await mock_processor.process_ocr_response(
            ocr_response, 
            fallback_to_base64=True
        )
        
        # Should return original response due to fallback
        assert modified_response == ocr_response
        assert upload_info['upload_attempted'] is False
        assert upload_info['connection_error'] == "Connection failed"
        assert upload_info['fallback_used'] is True
    
    @pytest.mark.asyncio
    async def test_process_ocr_response_s3_connection_failure_no_fallback(self, mock_processor):
        """Test S3 connection failure without fallback."""
        ocr_response = {"text": "Test", "images": []}
        
        # Mock S3 connection failure
        from app.utils.s3_client import S3ConnectionError
        mock_processor.s3_client.validate_connection.side_effect = S3ConnectionError("Connection failed")
        
        with pytest.raises(S3ConnectionError, match="Connection failed"):
            await mock_processor.process_ocr_response(ocr_response, fallback_to_base64=False)
    
    def test_recursive_replace_images(self, mock_processor):
        """Test recursive image replacement in response structure."""
        # Create test response structure
        response = {
            "text": "Main text",
            "images": [
                {"id": "img_001", "data": "original_base64_data"}
            ],
            "pages": [
                {
                    "page_number": 1,
                    "images": [
                        {"id": "img_002", "content": "another_base64_data"}
                    ]
                }
            ]
        }
        
        # Create replacement map
        replacement_map = {
            "root.images[0]": {
                'type': 's3_url',
                'url': 'https://bucket.s3.amazonaws.com/img_001.png',
                'image_object': {
                    'id': 'img_001',
                    's3_url': 'https://bucket.s3.amazonaws.com/img_001.png',
                    's3_object_key': 'img_001.png'
                }
            }
        }
        
        # Test replacement
        mock_processor._recursive_replace_images(response, replacement_map)
        
        # Verify replacement occurred
        assert response["images"][0]["s3_url"] == "https://bucket.s3.amazonaws.com/img_001.png"