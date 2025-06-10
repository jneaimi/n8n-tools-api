"""
Unit tests for S3 client functionality.

Tests S3 client configuration, connection validation, and upload operations
with mocked S3 responses to avoid requiring actual S3 credentials.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from botocore.exceptions import ClientError, NoCredentialsError
import time
import hashlib

from app.utils.s3_client import (
    S3Config, S3Client, create_s3_client,
    S3ConfigurationError, S3ConnectionError, S3UploadError
)

class TestS3Config:
    """Test S3Config validation and functionality."""
    
    def test_valid_config(self):
        """Test valid S3 configuration."""
        config = S3Config(
            access_key="AKIAIOSFODNN7EXAMPLE",
            secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            bucket_name="test-bucket",
            region="us-west-2"
        )
        
        assert config.access_key == "AKIAIOSFODNN7EXAMPLE"
        assert config.bucket_name == "test-bucket"
        assert config.region == "us-west-2"
        assert config.endpoint is None
        assert config.is_aws_s3() is True
    
    def test_config_with_custom_endpoint(self):
        """Test S3 config with custom endpoint."""
        config = S3Config(
            endpoint="https://minio.example.com:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            bucket_name="test-bucket"
        )
        
        assert config.endpoint == "https://minio.example.com:9000"
        assert config.is_aws_s3() is False
    
    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        with pytest.raises(S3ConfigurationError, match="Missing required S3 configuration"):
            S3Config(access_key="test")
    
    def test_invalid_endpoint_url(self):
        """Test validation with invalid endpoint URL."""
        with pytest.raises(S3ConfigurationError, match="Invalid S3 endpoint URL"):
            S3Config(
                endpoint="invalid-url",
                access_key="test",
                secret_key="test",
                bucket_name="test"
            )
    
    def test_get_public_url_template_aws(self):
        """Test AWS S3 public URL template generation."""
        config = S3Config(
            access_key="test",
            secret_key="test",
            bucket_name="my-bucket",
            region="us-west-2"
        )
        
        template = config.get_public_url_template()
        expected = "https://my-bucket.s3.us-west-2.amazonaws.com/{object_key}"
        assert template == expected
    
    def test_get_public_url_template_custom(self):
        """Test custom endpoint public URL template generation."""
        config = S3Config(
            endpoint="https://minio.example.com:9000",
            access_key="test",
            secret_key="test",
            bucket_name="my-bucket"
        )
        
        template = config.get_public_url_template()
        expected = "https://minio.example.com:9000/my-bucket/{object_key}"
        assert template == expected

class TestS3Client:
    """Test S3Client functionality with mocked AWS calls."""
    
    @pytest.fixture
    def s3_config(self):
        """Create test S3 configuration."""
        return S3Config(
            access_key="AKIAIOSFODNN7EXAMPLE",
            secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            bucket_name="test-bucket",
            region="us-east-1"
        )
    
    @pytest.fixture
    def s3_client(self, s3_config):
        """Create test S3 client."""
        return S3Client(s3_config)
    
    @patch('boto3.client')
    def test_client_creation(self, mock_boto_client, s3_client):
        """Test S3 client creation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        client = s3_client.client
        assert client == mock_client
        
        # Verify boto3.client was called with correct parameters
        mock_boto_client.assert_called_once()
        call_args = mock_boto_client.call_args[1]
        assert call_args['aws_access_key_id'] == "AKIAIOSFODNN7EXAMPLE"
        assert call_args['aws_secret_access_key'] == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert call_args['region_name'] == "us-east-1"
    
    @patch('boto3.client')
    def test_client_creation_with_custom_endpoint(self, mock_boto_client):
        """Test S3 client creation with custom endpoint."""
        config = S3Config(
            endpoint="https://minio.example.com",
            access_key="test",
            secret_key="test",
            bucket_name="test-bucket"
        )
        client = S3Client(config)
        
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        _ = client.client
        
        call_args = mock_boto_client.call_args[1]
        assert call_args['endpoint_url'] == "https://minio.example.com"
    
    @patch('boto3.client')
    def test_client_creation_credentials_error(self, mock_boto_client, s3_client):
        """Test S3 client creation with invalid credentials."""
        mock_boto_client.side_effect = NoCredentialsError()
        
        with pytest.raises(S3ConfigurationError, match="Invalid S3 credentials"):
            _ = s3_client.client
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_validate_connection_success(self, mock_boto_client, s3_client):
        """Test successful connection validation."""
        mock_client = Mock()
        mock_client.list_objects_v2.return_value = {'Contents': []}
        mock_client.put_object.return_value = {}
        mock_client.delete_object.return_value = {}
        mock_boto_client.return_value = mock_client
        
        result = await s3_client.validate_connection()
        
        assert result['status'] == 'validated'
        assert result['bucket'] == 'test-bucket'
        assert result['write_access'] is True
        
        # Verify all expected calls were made
        mock_client.list_objects_v2.assert_called_once()
        mock_client.put_object.assert_called_once()
        mock_client.delete_object.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_validate_connection_bucket_not_found(self, mock_boto_client, s3_client):
        """Test connection validation with non-existent bucket."""
        mock_client = Mock()
        error_response = {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket does not exist'}}
        mock_client.list_objects_v2.side_effect = ClientError(error_response, 'ListObjectsV2')
        mock_boto_client.return_value = mock_client
        
        with pytest.raises(S3ConfigurationError, match="Bucket 'test-bucket' does not exist"):
            await s3_client.validate_connection()
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_validate_connection_access_denied(self, mock_boto_client, s3_client):
        """Test connection validation with access denied."""
        mock_client = Mock()
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}
        mock_client.list_objects_v2.side_effect = ClientError(error_response, 'ListObjectsV2')
        mock_boto_client.return_value = mock_client
        
        with pytest.raises(S3ConfigurationError, match="Access denied to bucket 'test-bucket'"):
            await s3_client.validate_connection()
    
    def test_generate_object_key(self, s3_client):
        """Test object key generation."""
        content = b"test image content"
        filename = "test.png"
        
        key = s3_client.generate_object_key(content, filename, "custom-prefix")
        
        # Check structure
        assert key.startswith("custom-prefix/")
        assert key.endswith(".png")
        
        # Check that content hash is included
        content_hash = hashlib.sha256(content).hexdigest()[:16]
        assert content_hash in key
    
    def test_detect_content_type(self, s3_client):
        """Test content type detection."""
        # Test PNG
        png_content = b'\x89PNG\r\n\x1a\n'
        assert s3_client.detect_content_type(png_content) == 'image/png'
        
        # Test JPEG
        jpeg_content = b'\xff\xd8\xff'
        assert s3_client.detect_content_type(jpeg_content) == 'image/jpeg'
        
        # Test with filename
        assert s3_client.detect_content_type(b'', 'test.jpg') == 'image/jpeg'
        
        # Test fallback
        unknown_content = b'unknown'
        assert s3_client.detect_content_type(unknown_content) == 'application/octet-stream'
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_upload_file_success(self, mock_boto_client, s3_client):
        """Test successful file upload."""
        mock_client = Mock()
        mock_client.put_object.return_value = {}
        mock_boto_client.return_value = mock_client
        
        content = b"test image content"
        filename = "test.png"
        
        object_key, public_url = await s3_client.upload_file(content, filename=filename)
        
        # Verify upload was called
        mock_client.put_object.assert_called_once()
        call_args = mock_client.put_object.call_args[1]
        assert call_args['Bucket'] == 'test-bucket'
        assert call_args['Body'] == content
        assert call_args['ContentType'] == 'image/png'
        
        # Verify return values
        assert object_key is not None
        assert public_url.startswith('https://')
        assert 'test-bucket' in public_url
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_upload_file_with_metadata(self, mock_boto_client, s3_client):
        """Test file upload with metadata."""
        mock_client = Mock()
        mock_client.put_object.return_value = {}
        mock_boto_client.return_value = mock_client
        
        content = b"test content"
        metadata = {"source": "test", "page": "1"}
        
        await s3_client.upload_file(content, metadata=metadata)
        
        call_args = mock_client.put_object.call_args[1]
        assert call_args['Metadata'] == {"source": "test", "page": "1"}
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_upload_file_client_error(self, mock_boto_client, s3_client):
        """Test file upload with S3 client error."""
        mock_client = Mock()
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}
        mock_client.put_object.side_effect = ClientError(error_response, 'PutObject')
        mock_boto_client.return_value = mock_client
        
        content = b"test content"
        
        with pytest.raises(S3UploadError, match="Failed to upload to S3"):
            await s3_client.upload_file(content)
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_upload_multiple_files(self, mock_boto_client, s3_client):
        """Test uploading multiple files concurrently."""
        mock_client = Mock()
        mock_client.put_object.return_value = {}
        mock_boto_client.return_value = mock_client
        
        files = [
            (b"content1", "file1.png"),
            (b"content2", "file2.jpg"),
            (b"content3", "file3.gif")
        ]
        
        results = await s3_client.upload_multiple_files(files)
        
        assert len(results) == 3
        assert mock_client.put_object.call_count == 3
        
        # Verify each result has object_key and public_url
        for object_key, public_url in results:
            assert object_key is not None
            assert public_url.startswith('https://')

def test_create_s3_client():
    """Test S3 client factory function."""
    client = create_s3_client(
        access_key="test",
        secret_key="test",
        bucket_name="test-bucket"
    )
    
    assert isinstance(client, S3Client)
    assert client.config.bucket_name == "test-bucket"
    assert client.config.region == "us-east-1"  # Default region