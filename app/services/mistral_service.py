"""
Mistral AI OCR service.

Handles communication with Mistral AI's OCR API for document understanding.
"""

import aiohttp
import asyncio
import base64
import logging
import time
from typing import Dict, Any, Optional, Union, List
import json
from urllib.parse import urlparse

from app.core.errors import PDFProcessingError
from app.core.logging import (
    log_pdf_operation, 
    log_validation_result, 
    log_performance_metric,
    get_correlation_id,
    app_logger
)



class MistralAIError(Exception):
    """Custom exception for Mistral AI API errors."""
    pass

class MistralAIRateLimitError(MistralAIError):
    """Exception for rate limit errors."""
    pass

class MistralAIAuthenticationError(MistralAIError):
    """Exception for authentication errors."""
    pass

class MistralOCRService:
    """Service class for Mistral AI OCR operations."""
    
    BASE_URL = "https://api.mistral.ai/v1"
    MODEL_NAME = "mistral-ocr-latest"
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    MAX_PAGES = 1000
    SUPPORTED_FORMATS = ["pdf", "png", "jpg", "jpeg", "tiff"]
    
    # Rate limiting configuration
    MAX_REQUESTS_PER_MINUTE = 60
    MAX_REQUESTS_PER_HOUR = 1000
    RETRY_DELAYS = [1, 2, 5, 10]  # Exponential backoff delays in seconds
    
    def __init__(self):
        """Initialize the Mistral OCR Service."""
        self.session = None
        self.rate_limit_tracker = {
            'minute': {'count': 0, 'reset_time': time.time() + 60},
            'hour': {'count': 0, 'reset_time': time.time() + 3600}
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes timeout
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def _close_session(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _check_rate_limits(self) -> bool:
        """Check if we're within rate limits."""
        current_time = time.time()
        
        # Reset counters if time windows have passed
        if current_time >= self.rate_limit_tracker['minute']['reset_time']:
            self.rate_limit_tracker['minute'] = {
                'count': 0, 
                'reset_time': current_time + 60
            }
        
        if current_time >= self.rate_limit_tracker['hour']['reset_time']:
            self.rate_limit_tracker['hour'] = {
                'count': 0, 
                'reset_time': current_time + 3600
            }
        
        # Check limits
        minute_ok = self.rate_limit_tracker['minute']['count'] < self.MAX_REQUESTS_PER_MINUTE
        hour_ok = self.rate_limit_tracker['hour']['count'] < self.MAX_REQUESTS_PER_HOUR
        
        return minute_ok and hour_ok
    
    def _increment_rate_limit_counters(self):
        """Increment rate limit counters."""
        self.rate_limit_tracker['minute']['count'] += 1
        self.rate_limit_tracker['hour']['count'] += 1
    
    def _validate_api_key(self, api_key: str) -> bool:
        """Validate Mistral API key format."""
        if not api_key or not isinstance(api_key, str):
            return False
        
        # Basic validation - Mistral API keys should be substantial length
        if len(api_key) < 20:
            return False
        
        # Check for suspicious patterns
        if any(pattern in api_key.lower() for pattern in ['test', 'fake', 'demo', 'invalid']):
            return False
        
        return True
    
    def _prepare_file_data(self, file_content: bytes, filename: str) -> str:
        """Prepare file data for Mistral API by encoding as base64 data URL."""
        try:
            # Determine MIME type based on file extension
            file_ext = filename.lower().split('.')[-1] if '.' in filename else 'pdf'
            
            mime_types = {
                'pdf': 'application/pdf',
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'tiff': 'image/tiff'
            }
            
            mime_type = mime_types.get(file_ext, 'application/pdf')
            
            # Encode file content as base64
            base64_content = base64.b64encode(file_content).decode('utf-8')
            
            # Create data URL
            data_url = f"data:{mime_type};base64,{base64_content}"
            
            return data_url
            
        except Exception as e:
            app_logger.error(f"Failed to prepare file data: {str(e)}")
            raise MistralAIError(f"Failed to prepare file data: {str(e)}")
    
    def _validate_file(self, file_content: bytes, filename: str) -> tuple[bool, str]:
        """Validate file for OCR processing."""
        try:
            # Check file size
            if len(file_content) > self.MAX_FILE_SIZE:
                return False, f"File size ({len(file_content)} bytes) exceeds maximum allowed ({self.MAX_FILE_SIZE} bytes)"
            
            # Check file format
            file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
            if file_ext not in self.SUPPORTED_FORMATS:
                return False, f"Unsupported file format: {file_ext}. Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            
            # Basic content validation
            if len(file_content) < 100:  # Minimum reasonable file size
                return False, "File appears to be too small or corrupted"
            
            return True, "File validation passed"
            
        except Exception as e:
            app_logger.error(f"File validation failed: {str(e)}")
            return False, f"File validation error: {str(e)}"
    
    async def _make_api_request(
        self, 
        api_key: str, 
        payload: Dict[str, Any],
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """Make API request to Mistral OCR endpoint with retry logic."""
        if not self._check_rate_limits():
            raise MistralAIRateLimitError("Rate limit exceeded. Please try again later.")
        
        session = await self._get_session()
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'n8n-tools-ocr-service/1.0'
        }
        
        try:
            async with session.post(
                f"{self.BASE_URL}/ocr",
                headers=headers,
                json=payload
            ) as response:
                
                self._increment_rate_limit_counters()
                
                # Handle different response status codes
                if response.status == 200:
                    result = await response.json()
                    app_logger.info(f"Mistral OCR API request successful")
                    return result
                
                elif response.status == 401:
                    error_text = await response.text()
                    app_logger.error(f"Mistral API authentication failed: {error_text}")
                    raise MistralAIAuthenticationError(f"Invalid API key or authentication failed: {error_text}")
                
                elif response.status == 429:
                    # Rate limit exceeded
                    retry_after = response.headers.get('Retry-After', '60')
                    app_logger.warning(f"Mistral API rate limit exceeded. Retry after: {retry_after} seconds")
                    
                    if retry_count < len(self.RETRY_DELAYS):
                        delay = int(retry_after) if retry_after.isdigit() else self.RETRY_DELAYS[retry_count]
                        app_logger.info(f"Retrying after {delay} seconds (attempt {retry_count + 1})")
                        await asyncio.sleep(delay)
                        return await self._make_api_request(api_key, payload, retry_count + 1)
                    else:
                        raise MistralAIRateLimitError(f"Rate limit exceeded after {retry_count} retries")
                
                elif response.status == 400:
                    error_text = await response.text()
                    app_logger.error(f"Mistral API bad request: {error_text}")
                    raise MistralAIError(f"Bad request to Mistral API: {error_text}")
                
                elif response.status == 422:
                    error_text = await response.text()
                    app_logger.error(f"Mistral API validation error: {error_text}")
                    raise MistralAIError(f"Invalid request data: {error_text}")
                
                elif response.status >= 500:
                    error_text = await response.text()
                    app_logger.error(f"Mistral API server error: {response.status} - {error_text}")
                    
                    if retry_count < len(self.RETRY_DELAYS):
                        delay = self.RETRY_DELAYS[retry_count]
                        app_logger.info(f"Retrying after {delay} seconds due to server error (attempt {retry_count + 1})")
                        await asyncio.sleep(delay)
                        return await self._make_api_request(api_key, payload, retry_count + 1)
                    else:
                        raise MistralAIError(f"Mistral API server error after {retry_count} retries: {error_text}")
                
                else:
                    error_text = await response.text()
                    app_logger.error(f"Unexpected Mistral API response: {response.status} - {error_text}")
                    raise MistralAIError(f"Unexpected API response: {response.status} - {error_text}")
        
        except aiohttp.ClientError as e:
            app_logger.error(f"Network error communicating with Mistral API: {str(e)}")
            raise MistralAIError(f"Network error: {str(e)}")
        except asyncio.TimeoutError:
            app_logger.error("Timeout communicating with Mistral API")
            raise MistralAIError("Request timeout - Mistral API did not respond in time")
        except Exception as e:
            app_logger.error(f"Unexpected error during Mistral API request: {str(e)}")
            raise MistralAIError(f"Unexpected error: {str(e)}")
    
    async def process_file_ocr(
        self,
        file_content: bytes,
        filename: str,
        api_key: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process file using Mistral OCR API.
        
        Args:
            file_content: Binary content of the file
            filename: Original filename for context
            api_key: Mistral AI API key
            options: Additional processing options
            
        Returns:
            Dictionary containing OCR results with structured text, images, and metadata
        """
        start_time = time.time()
        correlation_id = get_correlation_id()
        
        try:
            # Validate API key
            if not self._validate_api_key(api_key):
                raise MistralAIAuthenticationError("Invalid API key format")
            
            # Validate file
            is_valid, validation_message = self._validate_file(file_content, filename)
            if not is_valid:
                raise MistralAIError(validation_message)
            
            # Prepare file data
            data_url = self._prepare_file_data(file_content, filename)
            
            # Set default options
            default_options = {
                'include_image_base64': True,
                'image_limit': 10,
                'image_min_size': 50,
                'pages': None  # Process all pages by default
            }
            
            if options:
                default_options.update(options)
            
            # Prepare API payload
            payload = {
                'model': self.MODEL_NAME,
                'document': {
                    'type': 'document_url',
                    'document_url': data_url,
                    'document_name': filename
                },
                'include_image_base64': default_options['include_image_base64'],
                'image_limit': default_options['image_limit'],
                'image_min_size': default_options['image_min_size']
            }
            
            # Add page specification if provided
            if default_options['pages'] is not None:
                payload['pages'] = default_options['pages']
            
            app_logger.info(f"Starting Mistral OCR processing for {filename} ({len(file_content)} bytes)")
            
            # Make API request
            api_response = await self._make_api_request(api_key, payload)
            
            # Process and structure the response
            processed_result = self._process_ocr_response(api_response, filename)
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            
            # Log successful operation
            log_pdf_operation(
                operation="mistral_ocr",
                filename=filename,
                file_size=len(file_content),
                pages=processed_result.get('pages_processed', 0),
                processing_time_ms=processing_time,
                correlation_id=correlation_id
            )
            
            app_logger.info(f"Mistral OCR processing completed for {filename} in {processing_time:.2f}ms")
            
            return processed_result
            
        except (MistralAIError, MistralAIAuthenticationError, MistralAIRateLimitError) as e:
            # Re-raise Mistral-specific errors
            processing_time = (time.time() - start_time) * 1000
            log_pdf_operation(
                operation="mistral_ocr",
                filename=filename,
                file_size=len(file_content),
                processing_time_ms=processing_time,
                error=str(e),
                correlation_id=correlation_id
            )
            raise
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            app_logger.error(f"Unexpected error in Mistral OCR processing: {str(e)}")
            log_pdf_operation(
                operation="mistral_ocr",
                filename=filename,
                file_size=len(file_content),
                processing_time_ms=processing_time,
                error=str(e),
                correlation_id=correlation_id
            )
            raise MistralAIError(f"OCR processing failed: {str(e)}")
        finally:
            await self._close_session()
    
    async def process_url_ocr(
        self,
        document_url: str,
        api_key: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process document from URL using Mistral OCR API.
        
        Args:
            document_url: URL to the document
            api_key: Mistral AI API key
            options: Additional processing options
            
        Returns:
            Dictionary containing OCR results
        """
        start_time = time.time()
        correlation_id = get_correlation_id()
        
        try:
            # Validate API key
            if not self._validate_api_key(api_key):
                raise MistralAIAuthenticationError("Invalid API key format")
            
            # Validate URL
            parsed_url = urlparse(document_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise MistralAIError("Invalid document URL format")
            
            # Set default options
            default_options = {
                'include_image_base64': True,
                'image_limit': 10,
                'image_min_size': 50,
                'pages': None
            }
            
            if options:
                default_options.update(options)
            
            # Prepare API payload
            payload = {
                'model': self.MODEL_NAME,
                'document': {
                    'type': 'document_url',
                    'document_url': document_url
                },
                'include_image_base64': default_options['include_image_base64'],
                'image_limit': default_options['image_limit'],
                'image_min_size': default_options['image_min_size']
            }
            
            # Add page specification if provided
            if default_options['pages'] is not None:
                payload['pages'] = default_options['pages']
            
            app_logger.info(f"Starting Mistral OCR processing for URL: {document_url}")
            
            # Make API request
            api_response = await self._make_api_request(api_key, payload)
            
            # Process and structure the response
            processed_result = self._process_ocr_response(api_response, document_url)
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            
            app_logger.info(f"Mistral OCR URL processing completed in {processing_time:.2f}ms")
            
            return processed_result
            
        except (MistralAIError, MistralAIAuthenticationError, MistralAIRateLimitError) as e:
            # Re-raise Mistral-specific errors
            raise
        except Exception as e:
            app_logger.error(f"Unexpected error in Mistral OCR URL processing: {str(e)}")
            raise MistralAIError(f"OCR URL processing failed: {str(e)}")
        finally:
            await self._close_session()
    
    def _process_ocr_response(self, api_response: Dict[str, Any], source_identifier: str) -> Dict[str, Any]:
        """
        Process and structure the OCR response from Mistral API.
        
        Args:
            api_response: Raw response from Mistral OCR API
            source_identifier: File name or URL for context
            
        Returns:
            Structured response compatible with the application
        """
        try:
            processed_pages = []
            extracted_images = []
            total_text_length = 0
            
            # Process each page
            for page in api_response.get('pages', []):
                page_data = {
                    'page_number': page.get('index', 0) + 1,  # Convert to 1-based indexing
                    'text': page.get('markdown', ''),
                    'dimensions': page.get('dimensions', {}),
                    'images': []
                }
                
                total_text_length += len(page_data['text'])
                
                # Process images on this page
                for image in page.get('images', []):
                    image_data = {
                        'id': image.get('id'),
                        'coordinates': {
                            'top_left_x': image.get('top_left_x'),
                            'top_left_y': image.get('top_left_y'),
                            'bottom_right_x': image.get('bottom_right_x'),
                            'bottom_right_y': image.get('bottom_right_y')
                        },
                        'base64_data': image.get('image_base64'),
                        'annotation': image.get('image_annotation')
                    }
                    
                    page_data['images'].append(image_data)
                    extracted_images.append(image_data)
                
                processed_pages.append(page_data)
            
            # Extract usage information
            usage_info = api_response.get('usage_info', {})
            
            # Create structured result
            result = {
                'status': 'success',
                'source': source_identifier,
                'model_used': api_response.get('model', self.MODEL_NAME),
                'pages_processed': usage_info.get('pages_processed', len(processed_pages)),
                'document_size_bytes': usage_info.get('doc_size_bytes', 0),
                'total_text_length': total_text_length,
                'total_images_extracted': len(extracted_images),
                'pages': processed_pages,
                'document_annotation': api_response.get('document_annotation'),
                'processing_metadata': {
                    'api_version': 'v1',
                    'service_provider': 'mistral-ai',
                    'extraction_timestamp': time.time(),
                    'features_used': {
                        'text_extraction': True,
                        'image_extraction': len(extracted_images) > 0,
                        'structure_preservation': True,
                        'markdown_formatting': True
                    }
                }
            }
            
            return result
            
        except Exception as e:
            app_logger.error(f"Failed to process OCR response: {str(e)}")
            raise MistralAIError(f"Failed to process API response: {str(e)}")
    
    async def test_api_key(self, api_key: str) -> Dict[str, Any]:
        """
        Test API key validity by making a minimal request.
        
        Args:
            api_key: Mistral AI API key to test
            
        Returns:
            Dictionary with test results
        """
        try:
            if not self._validate_api_key(api_key):
                return {
                    'valid': False,
                    'error': 'Invalid API key format',
                    'details': 'API key does not meet format requirements'
                }
            
            # Create a minimal test payload (small base64 image)
            # This is a 1x1 pixel transparent PNG
            test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAFfqlNNwgAAAABJRU5ErkJggg=="
            
            payload = {
                'model': self.MODEL_NAME,
                'document': {
                    'type': 'document_url',
                    'document_url': f"data:image/png;base64,{test_image_b64}"
                },
                'include_image_base64': False,
                'image_limit': 0
            }
            
            # Make test request
            response = await self._make_api_request(api_key, payload)
            
            return {
                'valid': True,
                'model': response.get('model', self.MODEL_NAME),
                'test_successful': True,
                'details': 'API key is valid and working'
            }
            
        except MistralAIAuthenticationError as e:
            return {
                'valid': False,
                'error': 'Authentication failed',
                'details': str(e)
            }
        except MistralAIRateLimitError as e:
            return {
                'valid': True,  # Key is valid but rate limited
                'error': 'Rate limit exceeded',
                'details': str(e)
            }
        except Exception as e:
            return {
                'valid': False,
                'error': 'API test failed',
                'details': str(e)
            }
        finally:
            await self._close_session()
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the Mistral OCR service capabilities.
        
        Returns:
            Dictionary with service information
        """
        return {
            'service_name': 'Mistral AI OCR',
            'model_name': self.MODEL_NAME,
            'supported_formats': self.SUPPORTED_FORMATS,
            'max_file_size_mb': self.MAX_FILE_SIZE // (1024 * 1024),
            'max_pages': self.MAX_PAGES,
            'features': {
                'text_extraction': True,
                'image_extraction': True,
                'structure_preservation': True,
                'markdown_output': True,
                'multilingual_support': True,
                'mathematical_formulas': True,
                'table_recognition': True,
                'url_processing': True
            },
            'rate_limits': {
                'requests_per_minute': self.MAX_REQUESTS_PER_MINUTE,
                'requests_per_hour': self.MAX_REQUESTS_PER_HOUR
            },
            'pricing': {
                'model': 'per_page',
                'cost_description': 'Approximately $1 per 1,000 pages processed'
            },
            'api_documentation': 'https://docs.mistral.ai/api/#tag/ocr'
        }
