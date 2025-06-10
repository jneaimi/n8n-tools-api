"""
Mistral AI OCR service.

Handles communication with Mistral AI's OCR API for document understanding.
"""

import aiohttp
import asyncio
import base64
import logging
import math
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
            
            # Debug: Log successful base64 encoding
            app_logger.debug(f"File {filename} encoded to base64: {mime_type}, size: {len(base64_content)} chars")
            
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
            
            # Debug: Log base64 preparation (first 100 chars to verify encoding)
            app_logger.debug(f"Base64 data URL prepared: {data_url[:100]}... (length: {len(data_url)})")
            
            # Set optimized default options for native image extraction
            default_options = {
                'include_image_base64': True,
                'image_limit': 50,  # Increased limit for better extraction
                'image_min_size': 30,  # Lower minimum size to capture more images
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
            # Use official Mistral API format for better compatibility
            processed_result = self._process_ocr_response_official_format(api_response, filename)
            
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
            
            # Set optimized default options for native image extraction
            default_options = {
                'include_image_base64': True,
                'image_limit': 50,  # Increased limit for better extraction
                'image_min_size': 30,  # Lower minimum size to capture more images
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
            # Use official Mistral API format for better compatibility
            processed_result = self._process_ocr_response_official_format(api_response, document_url)
            
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
        return self.process_mistral_ocr_response(api_response, source_identifier)
    
    def process_mistral_ocr_response(self, api_response: Dict[str, Any], source_identifier: str) -> Dict[str, Any]:
        """
        Enhanced processing of Mistral AI OCR response with native image extraction.
        
        This function processes the OCR response from Mistral AI, extracting and handling images
        that are directly provided in the response. It replaces custom PDF image extraction logic
        with Mistral's built-in capability.
        
        Args:
            api_response: The JSON response from Mistral AI's OCR API
            source_identifier: File name or URL for context
            
        Returns:
            Processed OCR result with properly handled images and enhanced metadata
        """
        try:
            app_logger.info(f"Processing Mistral OCR response for {source_identifier}")
            
            processed_pages = []
            extracted_images = []
            total_text_length = 0
            image_counter = 1
            
            # Validate API response structure
            if not isinstance(api_response, dict):
                raise ValueError("Invalid API response: expected dictionary")
            
            pages = api_response.get('pages', [])
            if not isinstance(pages, list):
                app_logger.warning("Invalid pages structure in API response")
                pages = []
            
            # Process each page with enhanced image handling
            for page_index, page in enumerate(pages):
                if not isinstance(page, dict):
                    app_logger.warning(f"Skipping invalid page data at index {page_index}")
                    continue
                
                page_number = page.get('index', page_index) + 1  # Convert to 1-based indexing
                page_text = page.get('markdown', '') or page.get('text', '')
                page_dimensions = page.get('dimensions', {})
                
                page_data = {
                    'page_number': page_number,
                    'text': page_text,
                    'dimensions': page_dimensions,
                    'images': []
                }
                
                total_text_length += len(page_text)
                
                # Enhanced image processing from Mistral's native extraction
                page_images = page.get('images', [])
                if not isinstance(page_images, list):
                    app_logger.warning(f"Invalid images structure on page {page_number}")
                    page_images = []
                
                for image_index, image in enumerate(page_images):
                    try:
                        # Enhanced image data extraction
                        image_data = self._extract_enhanced_image_data(
                            image, page_number, image_counter, page_dimensions
                        )
                        
                        if image_data:
                            page_data['images'].append(image_data)
                            extracted_images.append(image_data)
                            image_counter += 1
                            
                    except Exception as e:
                        app_logger.warning(f"Failed to process image {image_index + 1} on page {page_number}: {str(e)}")
                        continue
                
                processed_pages.append(page_data)
                app_logger.debug(f"Processed page {page_number}: {len(page_text)} chars, {len(page_data['images'])} images")
            
            # Extract enhanced usage information
            usage_info = api_response.get('usage_info', {})
            
            # Create structured result with enhanced metadata
            result = {
                'status': 'success',
                'source': source_identifier,
                'model_used': api_response.get('model', self.MODEL_NAME),
                'pages_processed': usage_info.get('pages_processed', len(processed_pages)),
                'document_size_bytes': usage_info.get('doc_size_bytes', 0),
                'total_text_length': total_text_length,
                'total_images_extracted': len(extracted_images),
                'pages': processed_pages,
                'document_annotation': api_response.get('document_annotation', ''),
                'processing_metadata': {
                    'api_version': 'v1',
                    'service_provider': 'mistral-ai',
                    'extraction_timestamp': time.time(),
                    'extraction_method': 'mistral_native',
                    'features_used': {
                        'text_extraction': True,
                        'image_extraction': len(extracted_images) > 0,
                        'structure_preservation': True,
                        'markdown_formatting': True,
                        'native_coordinates': True
                    },
                    'image_extraction_stats': {
                        'total_images': len(extracted_images),
                        'images_with_base64': sum(1 for img in extracted_images if img.get('base64_data')),
                        'images_with_coordinates': sum(1 for img in extracted_images if img.get('coordinates')),
                        'average_images_per_page': len(extracted_images) / max(len(processed_pages), 1),
                        'extraction_quality_score': self._calculate_extraction_quality_score(extracted_images),
                        'extraction_warnings': self._get_extraction_warnings(extracted_images, processed_pages)
                    }
                }
            }
            
            app_logger.info(f"Successfully processed Mistral OCR response: {total_text_length} chars, {len(extracted_images)} images")
            return result
            
        except Exception as e:
            app_logger.error(f"Failed to process Mistral OCR response: {str(e)}")
            raise MistralAIError(f"Failed to process API response: {str(e)}")
    
    def _extract_enhanced_image_data(
        self, 
        image: Dict[str, Any], 
        page_number: int, 
        sequence_number: int,
        page_dimensions: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract and enhance image data from Mistral's native response.
        
        Args:
            image: Raw image data from Mistral API
            page_number: Current page number (1-based)
            sequence_number: Global image sequence number
            page_dimensions: Page dimension information
            
        Returns:
            Enhanced image data object or None if invalid
        """
        try:
            if not isinstance(image, dict):
                app_logger.warning("Invalid image data structure")
                return None
            
            # Extract basic image information
            image_id = image.get('id', f"mistral_img_{page_number}_{sequence_number}")
            annotation = image.get('image_annotation', '') or image.get('annotation', '')
            
            # Extract and validate base64 data
            base64_data = image.get('image_base64', '') or image.get('base64_data', '')
            if base64_data and not self._validate_base64_data(base64_data):
                app_logger.warning(f"Invalid base64 data for image {image_id}")
                base64_data = None
            
            # Extract and normalize coordinates
            coordinates = self._extract_image_coordinates(image, page_dimensions)
            
            # Determine image quality and characteristics
            quality_info = self._assess_mistral_image_quality(image, base64_data)
            
            # Create enhanced image data object with backward compatibility
            enhanced_image = {
                # Enhanced Mistral native fields
                'id': image_id,
                'sequence_number': sequence_number,
                'page_number': page_number,
                'coordinates': coordinates,
                'annotation': annotation,
                'base64_data': base64_data,
                'extraction_quality': quality_info,
                'format_info': self._detect_image_format_from_base64(base64_data) if base64_data else {},
                'size_info': self._calculate_image_size_info(base64_data) if base64_data else {},
                'extraction_metadata': {
                    'source': 'mistral_native',
                    'extraction_method': 'api_response',
                    'has_coordinates': bool(coordinates),
                    'has_annotation': bool(annotation.strip()),
                    'has_image_data': bool(base64_data)
                },
                
                # Backward compatibility fields for existing code
                'data': base64_data,  # Legacy field name for base64_data
                'format': self._detect_image_format_from_base64(base64_data).get('detected_format', 'unknown') if base64_data else 'unknown',
                'size': self._extract_legacy_size_info(base64_data, coordinates),
                'position': self._extract_legacy_position_info(coordinates)
            }
            
            return enhanced_image
            
        except Exception as e:
            app_logger.warning(f"Failed to extract enhanced image data: {str(e)}")
            return None
    
    def _extract_image_coordinates(self, image: Dict[str, Any], page_dimensions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and normalize image coordinates from Mistral response.
        
        Args:
            image: Raw image data from Mistral
            page_dimensions: Page dimension information
            
        Returns:
            Normalized coordinate information
        """
        coordinates = {}
        
        # Extract raw coordinates with multiple possible field names
        raw_coords = {
            'top_left_x': image.get('top_left_x') or image.get('x1') or image.get('left'),
            'top_left_y': image.get('top_left_y') or image.get('y1') or image.get('top'),
            'bottom_right_x': image.get('bottom_right_x') or image.get('x2') or image.get('right'),
            'bottom_right_y': image.get('bottom_right_y') or image.get('y2') or image.get('bottom')
        }
        
        # Check if we have valid coordinate data
        if all(coord is not None for coord in raw_coords.values()):
            coordinates['absolute'] = raw_coords
            
            # Calculate relative coordinates if page dimensions are available
            if page_dimensions and 'width' in page_dimensions and 'height' in page_dimensions:
                page_width = float(page_dimensions['width'])
                page_height = float(page_dimensions['height'])
                
                if page_width > 0 and page_height > 0:
                    try:
                        x1_percent = (float(raw_coords['top_left_x']) / page_width) * 100
                        y1_percent = (float(raw_coords['top_left_y']) / page_height) * 100
                        x2_percent = (float(raw_coords['bottom_right_x']) / page_width) * 100
                        y2_percent = (float(raw_coords['bottom_right_y']) / page_height) * 100
                        
                        # Ensure values are finite and valid
                        if all(isinstance(x, (int, float)) and not (math.isnan(x) or math.isinf(x)) 
                               for x in [x1_percent, y1_percent, x2_percent, y2_percent]):
                            
                            coordinates['relative'] = {
                                'x1_percent': x1_percent,
                                'y1_percent': y1_percent,
                                'x2_percent': x2_percent,
                                'y2_percent': y2_percent
                            }
                            
                            # Calculate dimensions with validation
                            width = float(raw_coords['bottom_right_x']) - float(raw_coords['top_left_x'])
                            height = float(raw_coords['bottom_right_y']) - float(raw_coords['top_left_y'])
                            area_percent = max(0, (x2_percent - x1_percent) * (y2_percent - y1_percent) / 100)
                            
                            coordinates['dimensions'] = {
                                'width': max(0, width),
                                'height': max(0, height),
                                'area_percent': min(100, area_percent)  # Cap at 100%
                            }
                    except (ValueError, ZeroDivisionError, TypeError) as e:
                        app_logger.warning(f"Failed to calculate relative coordinates: {str(e)}")
                        # Continue without relative coordinates
        
        return coordinates
    
    def _validate_base64_data(self, base64_data: str) -> bool:
        """
        Validate base64 image data from Mistral response.
        
        Args:
            base64_data: Base64 encoded image data
            
        Returns:
            True if valid base64 image data
        """
        if not base64_data or not isinstance(base64_data, str):
            return False
        
        try:
            import base64
            # Remove any data URL prefix if present
            if base64_data.startswith('data:'):
                base64_data = base64_data.split(',', 1)[-1]
            
            decoded = base64.b64decode(base64_data, validate=True)
            
            # Check minimum size (should be more than just a few bytes)
            if len(decoded) < 100:
                return False
            
            # Basic image format validation
            image_signatures = [
                b'\xff\xd8\xff',  # JPEG
                b'\x89PNG\r\n\x1a\n',  # PNG
                b'GIF8',  # GIF
                b'RIFF',  # WebP (starts with RIFF)
                b'BM',  # BMP
            ]
            
            return any(decoded.startswith(sig) for sig in image_signatures)
            
        except Exception:
            return False
    
    def _assess_mistral_image_quality(self, image: Dict[str, Any], base64_data: Optional[str]) -> Dict[str, Any]:
        """
        Assess the quality of image data from Mistral response.
        
        Args:
            image: Raw image data from Mistral
            base64_data: Base64 image data (if available)
            
        Returns:
            Quality assessment information
        """
        quality = {
            'confidence': 0.9,  # High confidence for Mistral native extraction
            'completeness': 'complete',
            'clarity': 'excellent',
            'source_quality': 'native_api'
        }
        
        # Adjust confidence based on available data
        if not base64_data:
            quality['confidence'] = 0.7
            quality['completeness'] = 'coordinates_only'
        
        if not image.get('image_annotation', '').strip():
            quality['confidence'] -= 0.1
        
        # Coordinate precision assessment
        coords = image.get('top_left_x'), image.get('top_left_y'), image.get('bottom_right_x'), image.get('bottom_right_y')
        if all(coord is not None for coord in coords):
            if all(isinstance(coord, (int, float)) for coord in coords):
                quality['coordinate_precision'] = 'high' if any(isinstance(c, float) for c in coords) else 'standard'
            else:
                quality['coordinate_precision'] = 'low'
                quality['confidence'] -= 0.2
        else:
            quality['coordinate_precision'] = 'none'
            quality['confidence'] -= 0.3
        
        quality['confidence'] = max(0.0, min(1.0, quality['confidence']))
        return quality
    
    def _detect_image_format_from_base64(self, base64_data: str) -> Dict[str, Any]:
        """
        Detect image format from base64 data.
        
        Args:
            base64_data: Base64 encoded image data
            
        Returns:
            Format detection information
        """
        format_info = {
            'detected_format': 'unknown',
            'mime_type': 'image/unknown',
            'has_transparency': False,
            'compression': 'unknown'
        }
        
        if not base64_data:
            return format_info
        
        try:
            # Remove data URL prefix if present
            if base64_data.startswith('data:'):
                base64_data = base64_data.split(',', 1)[-1]
            
            # Check format by base64 signature patterns
            if base64_data.startswith('/9j/'):
                format_info.update({
                    'detected_format': 'jpeg',
                    'mime_type': 'image/jpeg',
                    'compression': 'lossy'
                })
            elif base64_data.startswith('iVBORw0KGgo'):
                format_info.update({
                    'detected_format': 'png',
                    'mime_type': 'image/png',
                    'has_transparency': True,
                    'compression': 'lossless'
                })
            elif base64_data.startswith('R0lGODlh') or base64_data.startswith('R0lGODdh'):
                format_info.update({
                    'detected_format': 'gif',
                    'mime_type': 'image/gif',
                    'has_transparency': True,
                    'compression': 'lossless'
                })
            elif base64_data.startswith('UklGR'):
                format_info.update({
                    'detected_format': 'webp',
                    'mime_type': 'image/webp',
                    'compression': 'variable'
                })
            elif base64_data.startswith('Qk'):
                format_info.update({
                    'detected_format': 'bmp',
                    'mime_type': 'image/bmp',
                    'compression': 'none'
                })
            
        except Exception as e:
            app_logger.debug(f"Could not detect image format: {str(e)}")
        
        return format_info
    
    def _calculate_image_size_info(self, base64_data: str) -> Dict[str, Any]:
        """
        Calculate size information from base64 image data.
        
        Args:
            base64_data: Base64 encoded image data
            
        Returns:
            Size information dictionary
        """
        try:
            import base64
            
            # Remove data URL prefix if present
            if base64_data.startswith('data:'):
                base64_data = base64_data.split(',', 1)[-1]
            
            decoded = base64.b64decode(base64_data)
            
            return {
                'base64_length': len(base64_data),
                'data_size_bytes': len(decoded),
                'data_size_kb': round(len(decoded) / 1024, 2),
                'data_size_mb': round(len(decoded) / (1024 * 1024), 3),
                'compression_ratio': round(len(decoded) / len(base64_data), 2)
            }
            
        except Exception as e:
            app_logger.debug(f"Could not calculate image size info: {str(e)}")
            return {}
    
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
    
    def _calculate_extraction_quality_score(self, extracted_images: List[Dict[str, Any]]) -> float:
        """
        Calculate overall extraction quality score based on image data completeness.
        
        Args:
            extracted_images: List of extracted image objects
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        if not extracted_images:
            return 0.0
        
        total_score = 0.0
        for image in extracted_images:
            image_score = 0.0
            
            # Base64 data availability (40% weight)
            if image.get('base64_data'):
                image_score += 0.4
            
            # Coordinates availability (30% weight)
            if image.get('coordinates'):
                image_score += 0.3
            
            # Annotation availability (20% weight)
            if image.get('annotation', '').strip():
                image_score += 0.2
            
            # Extraction quality confidence (10% weight)
            quality = image.get('extraction_quality', {})
            confidence = quality.get('confidence', 0.0)
            image_score += confidence * 0.1
            
            total_score += image_score
        
        return total_score / len(extracted_images)
    
    def _get_extraction_warnings(self, extracted_images: List[Dict[str, Any]], processed_pages: List[Dict[str, Any]]) -> List[str]:
        """
        Generate warnings about potential image extraction issues.
        
        Args:
            extracted_images: List of extracted image objects
            processed_pages: List of processed page objects
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Check if no images were extracted
        if not extracted_images:
            warnings.append("No images were extracted from the document by Mistral OCR")
        
        # Check for images without base64 data
        images_without_data = sum(1 for img in extracted_images if not img.get('base64_data'))
        if images_without_data > 0:
            warnings.append(f"{images_without_data} images found but without base64 data")
        
        # Check for images without coordinates
        images_without_coords = sum(1 for img in extracted_images if not img.get('coordinates'))
        if images_without_coords > 0:
            warnings.append(f"{images_without_coords} images found but without coordinate information")
        
        # Check for very low quality images
        low_quality_images = sum(1 for img in extracted_images 
                               if img.get('extraction_quality', {}).get('confidence', 1.0) < 0.3)
        if low_quality_images > 0:
            warnings.append(f"{low_quality_images} images have low extraction confidence")
        
        # Check for pages with text but no images (might indicate missed images)
        pages_with_text_no_images = sum(1 for page in processed_pages 
                                      if len(page.get('text', '').strip()) > 100 and len(page.get('images', [])) == 0)
        if pages_with_text_no_images > 0:
            warnings.append(f"{pages_with_text_no_images} pages have substantial text but no extracted images")
        
        return warnings
    
    def _extract_legacy_size_info(self, base64_data: Optional[str], coordinates: Dict[str, Any]) -> Dict[str, int]:
        """
        Extract size information in legacy format for backward compatibility.
        
        Args:
            base64_data: Base64 image data
            coordinates: Coordinate information
            
        Returns:
            Legacy size format (width, height)
        """
        # Try to get dimensions from coordinates first
        if coordinates and 'dimensions' in coordinates:
            dims = coordinates['dimensions']
            return {
                'width': int(dims.get('width', 0)),
                'height': int(dims.get('height', 0))
            }
        
        # Try to get from size_info if available
        size_info = self._calculate_image_size_info(base64_data) if base64_data else {}
        if 'width' in size_info and 'height' in size_info:
            return {
                'width': size_info['width'],
                'height': size_info['height']
            }
        
        # Default fallback
        return {'width': 0, 'height': 0}
    
    def _extract_legacy_position_info(self, coordinates: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Extract position information in legacy format for backward compatibility.
        
        Args:
            coordinates: Enhanced coordinate information
            
        Returns:
            Legacy position format (x, y, width, height as percentages) or None
        """
        if not coordinates or 'relative' not in coordinates:
            return None
        
        rel_coords = coordinates['relative']
        
        # Convert to legacy format (x, y, width, height as percentages 0-100)
        return {
            'x': rel_coords.get('x1_percent', 0.0),
            'y': rel_coords.get('y1_percent', 0.0),
            'width': rel_coords.get('x2_percent', 0.0) - rel_coords.get('x1_percent', 0.0),
            'height': rel_coords.get('y2_percent', 0.0) - rel_coords.get('y1_percent', 0.0)
        }
    
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
    def _process_ocr_response_official_format(
        self, 
        api_response: Dict[str, Any], 
        source_identifier: str
    ) -> Dict[str, Any]:
        """
        Process Mistral AI OCR response preserving the official API format.
        
        This function processes the OCR response from Mistral AI while preserving
        the exact structure defined in the official API specification.
        
        Args:
            api_response: The JSON response from Mistral AI's OCR API
            source_identifier: File name or URL for context
            
        Returns:
            OCR result in official Mistral API format
        """
        try:
            app_logger.info(f"Processing Mistral OCR response (official format) for {source_identifier}")
            
            # Validate API response structure
            if not isinstance(api_response, dict):
                raise ValueError("Invalid API response: expected dictionary")
            
            # Preserve the original structure while ensuring all required fields exist
            official_response = {
                "pages": [],
                "model": api_response.get('model', self.MODEL_NAME),
                "usage_info": {}
            }
            
            # Process pages with official structure
            pages = api_response.get('pages', [])
            if isinstance(pages, list):
                for page in pages:
                    if isinstance(page, dict):
                        # Preserve official page structure
                        official_page = {
                            "index": page.get('index', 0),
                            "markdown": page.get('markdown', ''),
                            "images": [],
                            "dimensions": page.get('dimensions', {})
                        }
                        
                        # Process images with official structure
                        page_images = page.get('images', [])
                        if isinstance(page_images, list):
                            for image in page_images:
                                if isinstance(image, dict):
                                    # Preserve official image structure
                                    official_image = {
                                        "id": image.get('id', ''),
                                        "top_left_x": image.get('top_left_x', 0),
                                        "top_left_y": image.get('top_left_y', 0), 
                                        "bottom_right_x": image.get('bottom_right_x', 0),
                                        "bottom_right_y": image.get('bottom_right_y', 0),
                                        "image_base64": image.get('image_base64', '')
                                    }
                                    
                                    # Add optional annotation if present
                                    if 'image_annotation' in image:
                                        official_image['image_annotation'] = image['image_annotation']
                                    
                                    official_page['images'].append(official_image)
                        
                        official_response['pages'].append(official_page)
            
            # Add usage information
            usage_info = api_response.get('usage_info', {})
            official_response['usage_info'] = {
                "pages_processed": usage_info.get('pages_processed', len(official_response['pages'])),
                "doc_size_bytes": usage_info.get('doc_size_bytes', 0)
            }
            
            # Add document annotation if present
            if 'document_annotation' in api_response:
                official_response['document_annotation'] = api_response['document_annotation']
            
            total_images = sum(len(page.get('images', [])) for page in official_response['pages'])
            app_logger.info(f"Successfully processed Mistral OCR response in official format: "
                          f"{len(official_response['pages'])} pages, {total_images} images")
            
            return official_response
            
        except Exception as e:
            app_logger.error(f"Failed to process Mistral OCR response in official format: {str(e)}")
            raise MistralAIError(f"Failed to process API response: {str(e)}")
