"""
S3 Client utilities for OCR image upload functionality.

Provides S3-compatible storage client setup, configuration validation,
and file upload capabilities for the OCR endpoint with image URL replacement.
"""

import boto3
import hashlib
import logging
import mimetypes
from botocore.exceptions import ClientError, BotoCoreError, NoCredentialsError
from botocore.config import Config
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse
import asyncio
import aiofiles
from functools import wraps
import time

from app.core.logging import app_logger

class S3ClientError(Exception):
    """Base exception for S3 client operations."""
    pass

class S3ConfigurationError(S3ClientError):
    """Exception raised for S3 configuration issues."""
    pass

class S3ConnectionError(S3ClientError):
    """Exception raised for S3 connection issues."""
    pass

class S3UploadError(S3ClientError):
    """Exception raised for S3 upload failures."""
    pass

class S3Config:
    """S3 configuration container with validation."""
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        region: Optional[str] = None
    ):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.region = region or 'us-east-1'  # Default region
        
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate S3 configuration parameters."""
        required_fields = ['access_key', 'secret_key', 'bucket_name']
        missing_fields = [field for field in required_fields if not getattr(self, field)]
        
        if missing_fields:
            raise S3ConfigurationError(
                f"Missing required S3 configuration: {', '.join(missing_fields)}"
            )
        
        # Validate endpoint URL if provided
        if self.endpoint:
            try:
                parsed = urlparse(self.endpoint)
                if not parsed.scheme or not parsed.netloc:
                    raise S3ConfigurationError(
                        f"Invalid S3 endpoint URL: {self.endpoint}"
                    )
            except Exception as e:
                raise S3ConfigurationError(
                    f"Invalid S3 endpoint URL format: {self.endpoint} - {str(e)}"
                )
    
    def is_aws_s3(self) -> bool:
        """Check if configuration is for AWS S3 (no custom endpoint)."""
        return self.endpoint is None
    
    def get_public_url_template(self) -> str:
        """Get the public URL template for uploaded objects."""
        if self.is_aws_s3():
            # AWS S3 public URL format
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{{object_key}}"
        else:
            # Custom S3-compatible endpoint
            parsed = urlparse(self.endpoint)
            return f"{parsed.scheme}://{parsed.netloc}/{self.bucket_name}/{{object_key}}"

def async_retry(max_attempts: int = 3, delay: float = 1.0, backoff_factor: float = 2.0):
    """Decorator for retrying async operations with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff_factor ** attempt)
                        app_logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {wait_time:.2f}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        app_logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )
            
            raise last_exception
        return wrapper
    return decorator

class S3Client:
    """S3 client wrapper with enhanced error handling and async support."""
    
    def __init__(self, config: S3Config):
        self.config = config
        self._client = None
        self._connection_validated = False
        
    def _create_client(self) -> boto3.client:
        """Create and configure S3 client."""
        try:
            # Configure boto3 client with timeout and retry settings
            boto_config = Config(
                retries={
                    'max_attempts': 3,
                    'mode': 'adaptive'
                },
                read_timeout=60,
                connect_timeout=10,
                max_pool_connections=10
            )
            
            client_kwargs = {
                'aws_access_key_id': self.config.access_key,
                'aws_secret_access_key': self.config.secret_key,
                'region_name': self.config.region,
                'config': boto_config
            }
            
            # Add custom endpoint if provided
            if self.config.endpoint:
                client_kwargs['endpoint_url'] = self.config.endpoint
            
            client = boto3.client('s3', **client_kwargs)
            
            app_logger.info(f"S3 client created for {'AWS S3' if self.config.is_aws_s3() else self.config.endpoint}")
            return client
            
        except NoCredentialsError:
            raise S3ConfigurationError("Invalid S3 credentials provided")
        except Exception as e:
            raise S3ConnectionError(f"Failed to create S3 client: {str(e)}")
    
    @property
    def client(self) -> boto3.client:
        """Get S3 client instance, creating if necessary."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    async def validate_connection(self) -> Dict[str, Any]:
        """Validate S3 connection and bucket access."""
        if self._connection_validated:
            return {"status": "validated", "cached": True}
        
        try:
            # Test connection by listing bucket (limited to 1 object)
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.list_objects_v2(
                    Bucket=self.config.bucket_name,
                    MaxKeys=1
                )
            )
            
            # Test write permissions by attempting to create a test object
            test_key = "test-connection-" + str(int(time.time()))
            test_content = b"test"
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.put_object(
                    Bucket=self.config.bucket_name,
                    Key=test_key,
                    Body=test_content,
                    ContentType='text/plain'
                )
            )
            
            # Clean up test object
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.delete_object(
                    Bucket=self.config.bucket_name,
                    Key=test_key
                )
            )
            
            self._connection_validated = True
            
            app_logger.info(f"S3 connection validated successfully for bucket: {self.config.bucket_name}")
            
            return {
                "status": "validated",
                "bucket": self.config.bucket_name,
                "region": self.config.region,
                "endpoint": self.config.endpoint or "AWS S3",
                "write_access": True
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            if error_code == 'NoSuchBucket':
                raise S3ConfigurationError(f"Bucket '{self.config.bucket_name}' does not exist")
            elif error_code == 'AccessDenied':
                raise S3ConfigurationError(f"Access denied to bucket '{self.config.bucket_name}'")
            elif error_code == 'InvalidAccessKeyId':
                raise S3ConfigurationError("Invalid S3 access key")
            elif error_code == 'SignatureDoesNotMatch':
                raise S3ConfigurationError("Invalid S3 secret key")
            else:
                raise S3ConnectionError(f"S3 connection failed: {error_code} - {error_message}")
                
        except BotoCoreError as e:
            raise S3ConnectionError(f"S3 connection error: {str(e)}")
        except Exception as e:
            raise S3ConnectionError(f"Unexpected S3 connection error: {str(e)}")
    
    def generate_object_key(self, content: bytes, original_filename: str = None, prefix: str = "ocr-images") -> str:
        """Generate a unique object key for uploaded content."""
        # Create content hash for uniqueness and deduplication
        content_hash = hashlib.sha256(content).hexdigest()[:16]
        
        # Determine file extension
        if original_filename:
            extension = original_filename.split('.')[-1].lower() if '.' in original_filename else 'bin'
        else:
            # Try to detect from content (simple magic number detection)
            if content.startswith(b'\x89PNG'):
                extension = 'png'
            elif content.startswith(b'\xff\xd8'):
                extension = 'jpg'
            elif content.startswith(b'GIF'):
                extension = 'gif'
            elif content.startswith(b'\x00\x00\x00'):
                extension = 'unknown'
            else:
                extension = 'bin'
        
        # Generate timestamp for organization
        timestamp = str(int(time.time()))
        
        # Create structured key
        object_key = f"{prefix}/{timestamp[:8]}/{content_hash}.{extension}"
        
        return object_key
    
    def detect_content_type(self, content: bytes, filename: str = None) -> str:
        """Detect content type from content and filename."""
        # Try MIME type detection from filename first
        if filename:
            content_type, _ = mimetypes.guess_type(filename)
            if content_type:
                return content_type
        
        # Fallback to magic number detection
        if content.startswith(b'\x89PNG'):
            return 'image/png'
        elif content.startswith(b'\xff\xd8'):
            return 'image/jpeg'
        elif content.startswith(b'GIF'):
            return 'image/gif'
        elif content.startswith(b'RIFF') and b'WEBP' in content[:20]:
            return 'image/webp'
        else:
            return 'application/octet-stream'
    
    @async_retry(max_attempts=3, delay=1.0, backoff_factor=2.0)
    async def upload_file(
        self, 
        content: bytes, 
        object_key: str = None, 
        filename: str = None,
        metadata: Dict[str, str] = None
    ) -> Tuple[str, str]:
        """
        Upload file content to S3 and return object key and public URL.
        
        Args:
            content: File content as bytes
            object_key: Optional custom object key (generated if not provided)
            filename: Optional original filename for content type detection
            metadata: Optional metadata to attach to the object
            
        Returns:
            Tuple of (object_key, public_url)
        """
        try:
            # Generate object key if not provided
            if object_key is None:
                object_key = self.generate_object_key(content, filename)
            
            # Detect content type
            content_type = self.detect_content_type(content, filename)
            
            # Prepare upload parameters
            upload_params = {
                'Bucket': self.config.bucket_name,
                'Key': object_key,
                'Body': content,
                'ContentType': content_type,
                'ContentLength': len(content)
            }
            
            # Add metadata if provided
            if metadata:
                # S3 metadata keys must be strings and values must be strings
                clean_metadata = {
                    str(k): str(v) for k, v in metadata.items() 
                    if isinstance(k, str) and v is not None
                }
                if clean_metadata:
                    upload_params['Metadata'] = clean_metadata
            
            # Perform upload in thread pool
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.put_object(**upload_params)
            )
            
            # Generate public URL
            public_url = self.config.get_public_url_template().format(object_key=object_key)
            
            app_logger.info(
                f"Successfully uploaded file to S3: {object_key} "
                f"({len(content)} bytes, {content_type})"
            )
            
            return object_key, public_url
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            app_logger.error(f"S3 upload failed: {error_code} - {error_message}")
            raise S3UploadError(f"Failed to upload to S3: {error_code} - {error_message}")
            
        except Exception as e:
            app_logger.error(f"Unexpected error during S3 upload: {str(e)}")
            raise S3UploadError(f"Unexpected upload error: {str(e)}")
    
    async def upload_multiple_files(
        self, 
        files: list[Tuple[bytes, str]], 
        metadata: Dict[str, str] = None
    ) -> list[Tuple[str, str]]:
        """
        Upload multiple files concurrently.
        
        Args:
            files: List of (content, filename) tuples
            metadata: Optional metadata to attach to all objects
            
        Returns:
            List of (object_key, public_url) tuples
        """
        # Create upload tasks
        tasks = [
            self.upload_file(content, filename=filename, metadata=metadata)
            for content, filename in files
        ]
        
        # Execute uploads concurrently
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle partial failures
            successful_uploads = []
            failed_uploads = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_uploads.append((i, str(result)))
                else:
                    successful_uploads.append(result)
            
            if failed_uploads:
                app_logger.warning(
                    f"Some uploads failed: {len(failed_uploads)} out of {len(files)} files"
                )
                # You might want to raise an exception here or handle partial failures differently
            
            app_logger.info(f"Successfully uploaded {len(successful_uploads)} files to S3")
            return successful_uploads
            
        except Exception as e:
            app_logger.error(f"Error in concurrent upload: {str(e)}")
            raise S3UploadError(f"Concurrent upload failed: {str(e)}")

def create_s3_client(
    endpoint: Optional[str] = None,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    bucket_name: Optional[str] = None,
    region: Optional[str] = None
) -> S3Client:
    """
    Factory function to create S3 client with configuration validation.
    
    Args:
        endpoint: S3 endpoint URL (optional for AWS S3)
        access_key: S3 access key
        secret_key: S3 secret key
        bucket_name: S3 bucket name
        region: S3 region (defaults to us-east-1)
        
    Returns:
        Configured S3Client instance
        
    Raises:
        S3ConfigurationError: If configuration is invalid
    """
    config = S3Config(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        bucket_name=bucket_name,
        region=region
    )
    
    return S3Client(config)
