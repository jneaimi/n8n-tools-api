"""
OCR S3 Processing utilities for base64 image detection and S3 upload.

Provides functionality to scan OCR responses for base64 images,
upload them to S3-compatible storage, and replace them with URLs.
"""

import base64
import re
import json
import asyncio
import time
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass
import logging

from app.utils.s3_client import S3Client, S3Config, create_s3_client, S3UploadError
from app.models.ocr_models import OCRImageWithS3
from app.core.logging import app_logger

# Base64 image pattern (data URL format)
BASE64_IMAGE_PATTERN = re.compile(
    r'data:image/([a-zA-Z]+);base64,([A-Za-z0-9+/=]+)',
    re.IGNORECASE
)

# Alternative base64 pattern for plain base64 strings that look like images
PLAIN_BASE64_PATTERN = re.compile(
    r'^([A-Za-z0-9+/]{40,}={0,2})$',  # Minimum 40 chars for reasonable image size
    re.MULTILINE
)

@dataclass
class Base64Image:
    """Container for detected base64 image data."""
    raw_data: str  # Original base64 string or data URL
    format: Optional[str]  # Image format (png, jpeg, etc.)
    base64_content: str  # Pure base64 content (without data URL prefix)
    binary_content: bytes  # Decoded binary content
    size_bytes: int  # Size in bytes
    source_location: str  # Where in the JSON this was found
    image_id: Optional[str] = None  # Associated image ID if available
    page_number: Optional[int] = None  # Page number if available
    sequence_number: Optional[int] = None  # Sequence number if available

class Base64ImageDetector:
    """Utility class for detecting base64 images in OCR responses."""
    
    def __init__(self, min_size_bytes: int = 50, max_size_mb: int = 10):
        """
        Initialize detector with size constraints.
        
        Args:
            min_size_bytes: Minimum image size to consider (filters out tiny images)
            max_size_mb: Maximum image size to process (prevents memory issues)
        """
        self.min_size_bytes = min_size_bytes
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    def detect_images_in_response(self, ocr_response: Dict[str, Any]) -> List[Base64Image]:
        """
        Detect all base64 images in an OCR response.
        
        Args:
            ocr_response: OCR response dictionary to scan
            
        Returns:
            List of detected Base64Image objects
        """
        detected_images = []
        
        # Debug: Log the structure of the response
        app_logger.info(f"Analyzing OCR response structure for base64 images...")
        app_logger.debug(f"Response keys: {list(ocr_response.keys())}")
        
        # Convert response to JSON string for pattern matching
        response_json = json.dumps(ocr_response, ensure_ascii=False)
        
        # Debug: Check if there are any base64-like strings
        import re
        base64_pattern = re.compile(r'[A-Za-z0-9+/]{100,}={0,2}')
        base64_matches = base64_pattern.findall(response_json)
        app_logger.info(f"Found {len(base64_matches)} potential base64 strings of 100+ chars")
        
        # First, look for data URL format images
        data_url_images = self._detect_data_url_images(response_json, ocr_response)
        app_logger.info(f"Detected {len(data_url_images)} data URL format images")
        detected_images.extend(data_url_images)
        
        # Then look for structured image objects with base64 data
        structured_images = self._detect_structured_images(ocr_response)
        app_logger.info(f"Detected {len(structured_images)} structured images")
        detected_images.extend(structured_images)
        
        # Filter by size constraints
        filtered_images = []
        for img in detected_images:
            if self.min_size_bytes <= img.size_bytes <= self.max_size_bytes:
                filtered_images.append(img)
                app_logger.debug(f"Included image: {img.image_id or 'unnamed'} ({img.size_bytes} bytes)")
            else:
                app_logger.debug(
                    f"Filtered out image: {img.image_id or 'unnamed'} - {img.size_bytes} bytes "
                    f"(min: {self.min_size_bytes}, max: {self.max_size_bytes})"
                )
        
        app_logger.info(f"Final result: {len(filtered_images)} base64 images ready for S3 upload")
        return filtered_images
    
    def _detect_data_url_images(self, response_json: str, response_dict: Dict) -> List[Base64Image]:
        """Detect images in data URL format (data:image/png;base64,...)."""
        images = []
        
        # First pass: find all data URL matches and their positions
        data_url_matches = []
        for match in BASE64_IMAGE_PATTERN.finditer(response_json):
            image_format = match.group(1).lower()
            base64_content = match.group(2)
            full_data_url = match.group(0)
            start_pos = match.start()
            
            data_url_matches.append({
                'format': image_format,
                'base64_content': base64_content,
                'full_data_url': full_data_url,
                'start_pos': start_pos
            })
        
        # Second pass: try to find the actual location in the response structure
        for i, match_data in enumerate(data_url_matches):
            try:
                # Decode base64 content
                binary_content = base64.b64decode(match_data['base64_content'])
                
                # Try to find the actual location in the response structure
                source_location = self._find_image_location_in_structure(
                    response_dict, match_data['full_data_url'], i
                )
                
                # Create Base64Image object
                img = Base64Image(
                    raw_data=match_data['full_data_url'],
                    format=match_data['format'],
                    base64_content=match_data['base64_content'],
                    binary_content=binary_content,
                    size_bytes=len(binary_content),
                    source_location=source_location
                )
                
                images.append(img)
                app_logger.debug(f"Data URL image {i}: {len(binary_content)} bytes at {source_location}")
                
            except Exception as e:
                app_logger.warning(f"Failed to decode data URL image {i}: {str(e)}")
                continue
        
        return images
    
    def _find_image_location_in_structure(self, response_dict: Dict, target_data_url: str, fallback_index: int) -> str:
        """Find the actual location of a data URL in the response structure."""
        
        # Check pages array (Mistral format)
        if 'pages' in response_dict and isinstance(response_dict['pages'], list):
            for page_idx, page in enumerate(response_dict['pages']):
                if 'images' in page and isinstance(page['images'], list):
                    for img_idx, img_obj in enumerate(page['images']):
                        if isinstance(img_obj, dict):
                            # Check various possible field names for the data URL
                            for field in ['data', 'base64_data', 'base64', 'content', 'image_data']:
                                if field in img_obj and img_obj[field] == target_data_url:
                                    location = f"pages[{page_idx}].images[{img_idx}]"
                                    app_logger.debug(f"Found data URL at {location}")
                                    return location
        
        # Check root images array
        if 'images' in response_dict and isinstance(response_dict['images'], list):
            for img_idx, img_obj in enumerate(response_dict['images']):
                if isinstance(img_obj, dict):
                    for field in ['data', 'base64_data', 'base64', 'content', 'image_data']:
                        if field in img_obj and img_obj[field] == target_data_url:
                            location = f"root.images[{img_idx}]"
                            app_logger.debug(f"Found data URL at {location}")
                            return location
        
        # Check content array
        if 'content' in response_dict and isinstance(response_dict['content'], list):
            for content_idx, content in enumerate(response_dict['content']):
                if 'images' in content and isinstance(content['images'], list):
                    for img_idx, img_obj in enumerate(content['images']):
                        if isinstance(img_obj, dict):
                            for field in ['data', 'base64_data', 'base64', 'content', 'image_data']:
                                if field in img_obj and img_obj[field] == target_data_url:
                                    location = f"content[{content_idx}].images[{img_idx}]"
                                    app_logger.debug(f"Found data URL at {location}")
                                    return location
        
        # Fallback to generic location
        fallback_location = f"data_url_match_{fallback_index}"
        app_logger.warning(f"Could not find specific location for data URL, using fallback: {fallback_location}")
        return fallback_location
    
    def _detect_structured_images(self, response_dict: Dict) -> List[Base64Image]:
        """Detect images in structured format (in images arrays, etc.)."""
        images = []
        
        # Look for images in various possible structures
        image_sources = []
        
        # Check for images array at root level
        if isinstance(response_dict.get('images'), list):
            for i, img in enumerate(response_dict['images']):
                image_sources.append((img, f"root.images[{i}]"))
                app_logger.debug(f"Found image at root.images[{i}]")
        
        # Check for pages with images
        if isinstance(response_dict.get('pages'), list):
            for page_idx, page in enumerate(response_dict['pages']):
                if isinstance(page.get('images'), list):
                    for img_idx, img in enumerate(page['images']):
                        image_sources.append((img, f"pages[{page_idx}].images[{img_idx}]"))
                        app_logger.debug(f"Found image at pages[{page_idx}].images[{img_idx}]")
        
        # Check for content sections or other nested structures
        if isinstance(response_dict.get('content'), list):
            for content_idx, content in enumerate(response_dict['content']):
                if isinstance(content.get('images'), list):
                    for img_idx, img in enumerate(content['images']):
                        image_sources.append((img, f"content[{content_idx}].images[{img_idx}]"))
                        app_logger.debug(f"Found image at content[{content_idx}].images[{img_idx}]")
        
        # Check for direct image objects in response
        if isinstance(response_dict.get('extracted_images'), list):
            for img_idx, img in enumerate(response_dict['extracted_images']):
                image_sources.append((img, f"extracted_images[{img_idx}]"))
                app_logger.debug(f"Found image at extracted_images[{img_idx}]")
        
        app_logger.info(f"Found {len(image_sources)} potential image objects to process")
        
        # Process each image source
        for img_data, location in image_sources:
            if not isinstance(img_data, dict):
                app_logger.debug(f"Skipping non-dict image data at {location}")
                continue
            
            app_logger.debug(f"Processing image at {location} with keys: {list(img_data.keys())}")
            
            # Look for base64 data in various fields
            base64_fields = [
                'data', 'base64_data', 'base64', 'content', 'image_data', 
                'image_content', 'base64_image', 'encoded_data', 'img_data'
            ]
            base64_content = None
            raw_data = None
            image_format = None
            
            for field in base64_fields:
                if field in img_data and isinstance(img_data[field], str):
                    content = img_data[field]
                    app_logger.debug(f"Checking field '{field}' with content length: {len(content)}")
                    
                    # Check if it's a data URL
                    data_url_match = BASE64_IMAGE_PATTERN.match(content)
                    if data_url_match:
                        image_format = data_url_match.group(1).lower()
                        base64_content = data_url_match.group(2)
                        raw_data = content
                        app_logger.debug(f"Found data URL format image: {image_format}")
                        break
                    
                    # Check if it's plain base64
                    elif self._is_base64_image(content):
                        base64_content = content
                        raw_data = content
                        image_format = self._detect_image_format_from_content(content)
                        app_logger.debug(f"Found plain base64 image: {image_format}")
                        break
                    else:
                        app_logger.debug(f"Field '{field}' doesn't contain valid base64 image data")
            
            if base64_content:
                try:
                    # Decode base64 content
                    binary_content = base64.b64decode(base64_content)
                    
                    # Extract metadata from image object
                    img = Base64Image(
                        raw_data=raw_data,
                        format=image_format or img_data.get('format'),
                        base64_content=base64_content,
                        binary_content=binary_content,
                        size_bytes=len(binary_content),
                        source_location=location,
                        image_id=img_data.get('id'),
                        page_number=img_data.get('page_number'),
                        sequence_number=img_data.get('sequence_number')
                    )
                    
                    images.append(img)
                    app_logger.info(f"Successfully processed image at {location}: {len(binary_content)} bytes")
                    
                except Exception as e:
                    app_logger.warning(f"Failed to decode structured image at {location}: {str(e)}")
                    continue
            else:
                app_logger.debug(f"No valid base64 content found at {location}")
        
        return images
    
    def _is_base64_image(self, content: str) -> bool:
        """Check if a string appears to be base64 encoded image data."""
        # Basic validation
        if len(content) < 100:  # Too small to be a meaningful image
            return False
        
        # Check if it matches base64 pattern
        if not PLAIN_BASE64_PATTERN.match(content):
            return False
        
        try:
            # Try to decode and check for image signatures
            decoded = base64.b64decode(content)
            return self._has_image_signature(decoded)
        except Exception:
            return False
    
    def _has_image_signature(self, data: bytes) -> bool:
        """Check if binary data has image file signatures."""
        if len(data) < 10:
            return False
        
        # Check for common image signatures
        signatures = [
            b'\x89PNG',           # PNG
            b'\xff\xd8\xff',     # JPEG
            b'GIF87a',           # GIF87a
            b'GIF89a',           # GIF89a
            b'RIFF',             # WebP (partial)
            b'\x00\x00\x01\x00', # ICO
            b'BM',               # BMP
        ]
        
        for sig in signatures:
            if data.startswith(sig):
                return True
        
        return False
    
    def _detect_image_format_from_content(self, base64_content: str) -> Optional[str]:
        """Detect image format from base64 content by checking file signatures."""
        try:
            decoded = base64.b64decode(base64_content)
            
            if decoded.startswith(b'\x89PNG'):
                return 'png'
            elif decoded.startswith(b'\xff\xd8\xff'):
                return 'jpeg'
            elif decoded.startswith((b'GIF87a', b'GIF89a')):
                return 'gif'
            elif decoded.startswith(b'RIFF') and b'WEBP' in decoded[:20]:
                return 'webp'
            elif decoded.startswith(b'BM'):
                return 'bmp'
            else:
                return 'unknown'
                
        except Exception:
            return None

class OCRImageUploader:
    """Handles uploading detected images to S3 and URL replacement."""
    
    def __init__(self, s3_client: S3Client, upload_prefix: str = "ocr-images"):
        """
        Initialize uploader with S3 client.
        
        Args:
            s3_client: Configured S3Client instance
            upload_prefix: Prefix for S3 object keys
        """
        self.s3_client = s3_client
        self.upload_prefix = upload_prefix
    
    async def upload_images_concurrently(
        self, 
        images: List[Base64Image],
        max_concurrent: int = 5,
        timeout_seconds: int = 30
    ) -> Tuple[List[OCRImageWithS3], List[Base64Image]]:
        """
        Upload multiple images to S3 concurrently.
        
        Args:
            images: List of Base64Image objects to upload
            max_concurrent: Maximum number of concurrent uploads
            timeout_seconds: Timeout for each upload operation
            
        Returns:
            Tuple of (successful_uploads, failed_uploads)
        """
        if not images:
            return [], []
        
        app_logger.info(f"Starting concurrent upload of {len(images)} images to S3")
        
        # Create semaphore to limit concurrent uploads
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Create upload tasks
        upload_tasks = [
            self._upload_single_image_with_semaphore(img, semaphore, timeout_seconds)
            for img in images
        ]
        
        # Execute uploads with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*upload_tasks, return_exceptions=True),
                timeout=timeout_seconds * 2  # Overall timeout
            )
        except asyncio.TimeoutError:
            app_logger.error("Overall upload operation timed out")
            return [], images  # All failed
        
        # Process results
        successful_uploads = []
        failed_uploads = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                app_logger.warning(f"Upload failed for image {i}: {str(result)}")
                failed_uploads.append(images[i])
            elif result is None:
                # Upload was skipped or failed silently
                failed_uploads.append(images[i])
            else:
                successful_uploads.append(result)
        
        app_logger.info(
            f"Upload completed: {len(successful_uploads)} successful, "
            f"{len(failed_uploads)} failed"
        )
        
        return successful_uploads, failed_uploads
    
    async def _upload_single_image_with_semaphore(
        self, 
        image: Base64Image, 
        semaphore: asyncio.Semaphore,
        timeout_seconds: int
    ) -> Optional[OCRImageWithS3]:
        """Upload single image with semaphore limiting."""
        async with semaphore:
            try:
                return await asyncio.wait_for(
                    self._upload_single_image(image),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                app_logger.warning(f"Upload timeout for image: {image.source_location}")
                return None
            except Exception as e:
                app_logger.warning(f"Upload error for image {image.source_location}: {str(e)}")
                return None
    
    async def _upload_single_image(self, image: Base64Image) -> OCRImageWithS3:
        """Upload a single image to S3."""
        # Generate filename
        filename = self._generate_filename(image)
        
        # Prepare metadata
        metadata = {
            'source_location': image.source_location,
            'original_size_bytes': str(image.size_bytes),
            'image_format': image.format or 'unknown',
            'upload_timestamp': str(time.time())
        }
        
        if image.image_id:
            metadata['original_image_id'] = image.image_id
        if image.page_number is not None:
            metadata['page_number'] = str(image.page_number)
        if image.sequence_number is not None:
            metadata['sequence_number'] = str(image.sequence_number)
        
        # Upload to S3
        try:
            object_key, public_url = await self.s3_client.upload_file(
                content=image.binary_content,
                filename=filename,
                metadata=metadata
            )
            
            # Create OCRImageWithS3 object
            s3_image = OCRImageWithS3(
                id=image.image_id or f"s3_{object_key.split('/')[-1].split('.')[0]}",
                s3_url=public_url,
                s3_object_key=object_key,
                upload_timestamp=time.time(),
                format=image.format,
                file_size_bytes=image.size_bytes,
                content_type=self._get_content_type(image.format),
                page_number=image.page_number,
                sequence_number=image.sequence_number,
                upload_metadata={
                    'source_location': image.source_location,
                    'upload_prefix': self.upload_prefix,
                    'upload_success': True,
                    'original_data_url': image.raw_data  # Store original data URL for replacement
                }
            )
            
            app_logger.debug(f"Successfully uploaded image: {object_key}")
            return s3_image
            
        except Exception as e:
            app_logger.error(f"Failed to upload image {image.source_location}: {str(e)}")
            raise S3UploadError(f"Upload failed: {str(e)}")
    
    def _generate_filename(self, image: Base64Image) -> str:
        """Generate filename for the image."""
        # Use image ID if available
        if image.image_id:
            base_name = f"img_{image.image_id}"
        else:
            # Generate based on content hash
            import hashlib
            content_hash = hashlib.md5(image.binary_content).hexdigest()[:12]
            base_name = f"img_{content_hash}"
        
        # Add format extension
        extension = image.format or 'bin'
        if not extension.startswith('.'):
            extension = f".{extension}"
        
        return f"{base_name}{extension}"
    
    def _get_content_type(self, image_format: Optional[str]) -> str:
        """Get MIME content type for image format."""
        format_map = {
            'png': 'image/png',
            'jpeg': 'image/jpeg',
            'jpg': 'image/jpeg',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'bmp': 'image/bmp'
        }
        return format_map.get(image_format, 'application/octet-stream')

class OCRResponseProcessor:
    """Main processor for OCR responses with S3 image replacement."""
    
    def __init__(self, s3_config: S3Config, upload_prefix: str = "ocr-images"):
        """
        Initialize processor with S3 configuration.
        
        Args:
            s3_config: S3 configuration object
            upload_prefix: Prefix for uploaded object keys
        """
        self.s3_config = s3_config
        self.upload_prefix = upload_prefix
        self.detector = Base64ImageDetector()
        
        # Create S3 client
        self.s3_client = create_s3_client(
            endpoint=s3_config.endpoint,
            access_key=s3_config.access_key,
            secret_key=s3_config.secret_key.get_secret_value(),
            bucket_name=s3_config.bucket_name,
            region=s3_config.region
        )
        
        self.uploader = OCRImageUploader(self.s3_client, upload_prefix)
    
    async def process_ocr_response(
        self, 
        ocr_response: Dict[str, Any],
        fallback_to_base64: bool = True,
        upload_timeout_seconds: int = 30
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Process OCR response by uploading images to S3 and replacing URLs.
        
        Args:
            ocr_response: Original OCR response with base64 images
            fallback_to_base64: Whether to keep original base64 if upload fails
            upload_timeout_seconds: Timeout for upload operations
            
        Returns:
            Tuple of (modified_response, upload_info)
        """
        start_time = time.time()
        
        app_logger.info(f"Starting S3 processing for OCR response...")
        app_logger.debug(f"Input response structure: {list(ocr_response.keys())}")
        
        # Validate S3 connection first
        try:
            connection_result = await self.s3_client.validate_connection()
            app_logger.info(f"S3 connection validated: {connection_result['status']}")
        except Exception as e:
            app_logger.error(f"S3 connection validation failed: {str(e)}")
            if fallback_to_base64:
                return ocr_response, {
                    'upload_attempted': False,
                    'connection_error': str(e),
                    'fallback_used': True
                }
            else:
                raise
        
        # Detect base64 images
        detected_images = self.detector.detect_images_in_response(ocr_response)
        
        if not detected_images:
            app_logger.info("No base64 images detected in OCR response - returning original response")
            return ocr_response, {
                'images_detected': 0,
                'images_uploaded': 0,
                'images_failed': 0,
                'upload_success_rate': 1.0,  # 100% success when no images to process
                'fallback_used': False,
                'processing_time_ms': (time.time() - start_time) * 1000,
                's3_bucket': self.s3_config.bucket_name,
                's3_prefix': self.upload_prefix
            }
        
        app_logger.info(f"Proceeding with S3 upload for {len(detected_images)} detected images")
        
        # Upload images to S3
        successful_uploads, failed_uploads = await self.uploader.upload_images_concurrently(
            detected_images,
            timeout_seconds=upload_timeout_seconds
        )
        
        app_logger.info(f"S3 upload completed: {len(successful_uploads)} successful, {len(failed_uploads)} failed")
        
        # Replace base64 data with S3 URLs in response
        modified_response = self._replace_images_in_response(
            ocr_response, 
            successful_uploads, 
            failed_uploads if fallback_to_base64 else []
        )
        
        # Generate upload info
        upload_info = {
            'images_detected': len(detected_images),
            'images_uploaded': len(successful_uploads),
            'images_failed': len(failed_uploads),
            'upload_success_rate': len(successful_uploads) / len(detected_images) if detected_images else 1.0,
            'fallback_used': fallback_to_base64 and len(failed_uploads) > 0,
            'processing_time_ms': (time.time() - start_time) * 1000,
            's3_bucket': self.s3_config.bucket_name,
            's3_prefix': self.upload_prefix
        }
        
        app_logger.info(
            f"OCR S3 processing completed: {len(successful_uploads)}/{len(detected_images)} "
            f"images uploaded successfully in {upload_info['processing_time_ms']:.2f}ms"
        )
        
        return modified_response, upload_info
    
    def _replace_images_in_response(
        self, 
        response: Dict[str, Any], 
        uploaded_images: List[OCRImageWithS3],
        fallback_images: List[Base64Image]
    ) -> Dict[str, Any]:
        """Replace base64 image data with S3 URLs in the response."""
        # Deep copy the response to avoid modifying the original
        import copy
        modified_response = copy.deepcopy(response)
        
        app_logger.info(f"Starting image replacement: {len(uploaded_images)} uploaded, {len(fallback_images)} fallback")
        
        # Create mapping from source location to replacement data
        replacement_map = {}
        
        # Add successful uploads
        for img in uploaded_images:
            if hasattr(img, 'upload_metadata') and img.upload_metadata:
                source_location = img.upload_metadata.get('source_location')
                if source_location:
                    replacement_map[source_location] = {
                        'type': 's3_url',
                        'url': img.s3_url,
                        'image_object': img.dict()
                    }
                    app_logger.debug(f"Added S3 replacement for {source_location}")
        
        # Add fallback images (keep original base64)
        for img in fallback_images:
            replacement_map[img.source_location] = {
                'type': 'fallback_base64',
                'original_data': img.raw_data
            }
            app_logger.debug(f"Added fallback replacement for {img.source_location}")
        
        app_logger.info(f"Created replacement map with {len(replacement_map)} entries")
        
        # For Mistral format, we need to handle the specific structure
        replaced_count = 0
        
        # Handle pages array structure (Mistral format)
        if 'pages' in modified_response and isinstance(modified_response['pages'], list):
            for page_idx, page in enumerate(modified_response['pages']):
                if 'images' in page and isinstance(page['images'], list):
                    for img_idx, img_obj in enumerate(page['images']):
                        source_location = f"pages[{page_idx}].images[{img_idx}]"
                        if source_location in replacement_map:
                            replacement = replacement_map[source_location]
                            if replacement['type'] == 's3_url':
                                # Replace with S3 image object
                                modified_response['pages'][page_idx]['images'][img_idx] = replacement['image_object']
                                replaced_count += 1
                                app_logger.debug(f"Replaced image at {source_location} with S3 URL")
                            # For fallback, keep original (no change needed)
        
        # Handle root-level images array
        if 'images' in modified_response and isinstance(modified_response['images'], list):
            for img_idx, img_obj in enumerate(modified_response['images']):
                source_location = f"root.images[{img_idx}]"
                if source_location in replacement_map:
                    replacement = replacement_map[source_location]
                    if replacement['type'] == 's3_url':
                        # Replace with S3 image object
                        modified_response['images'][img_idx] = replacement['image_object']
                        replaced_count += 1
                        app_logger.debug(f"Replaced image at {source_location} with S3 URL")
        
        # Handle other possible structures
        if 'content' in modified_response and isinstance(modified_response['content'], list):
            for content_idx, content in enumerate(modified_response['content']):
                if 'images' in content and isinstance(content['images'], list):
                    for img_idx, img_obj in enumerate(content['images']):
                        source_location = f"content[{content_idx}].images[{img_idx}]"
                        if source_location in replacement_map:
                            replacement = replacement_map[source_location]
                            if replacement['type'] == 's3_url':
                                # Replace with S3 image object
                                modified_response['content'][content_idx]['images'][img_idx] = replacement['image_object']
                                replaced_count += 1
                                app_logger.debug(f"Replaced image at {source_location} with S3 URL")
        
        # Fallback: Handle generic data_url_match_X locations with direct JSON replacement
        if replaced_count == 0 and len(uploaded_images) > 0:
            app_logger.info("No structured replacements made, attempting direct JSON replacement for data URL matches")
            
            # Convert response to JSON for string replacement
            response_json = json.dumps(modified_response)
            
            # Replace data URLs directly in the JSON string
            for img in uploaded_images:
                if hasattr(img, 'upload_metadata') and img.upload_metadata:
                    source_location = img.upload_metadata.get('source_location', '')
                    if source_location.startswith('data_url_match_'):
                        # Find the original data URL to replace
                        # We need to extract the original data URL from the uploaded image metadata
                        if 'original_data_url' in img.upload_metadata:
                            original_data_url = img.upload_metadata['original_data_url']
                            # Create S3 image data structure 
                            s3_image_data = {
                                "id": img.id,
                                "s3_url": img.s3_url,
                                "s3_object_key": img.s3_object_key,
                                "upload_timestamp": img.upload_timestamp,
                                "format": img.format,
                                "file_size_bytes": img.file_size_bytes,
                                "content_type": img.content_type
                            }
                            
                            # Replace the data URL with just the S3 URL in the field
                            response_json = response_json.replace(
                                f'"{original_data_url}"', 
                                f'"{img.s3_url}"'
                            )
                            replaced_count += 1
                            app_logger.debug(f"Direct JSON replacement for {source_location}: data URL -> S3 URL")
            
            # Parse back to dict if we made replacements
            if replaced_count > 0:
                try:
                    modified_response = json.loads(response_json)
                    app_logger.info(f"Successfully performed {replaced_count} direct JSON replacements")
                except json.JSONDecodeError as e:
                    app_logger.error(f"Failed to parse JSON after replacement: {str(e)}")
                    # Fall back to original response
                    modified_response = response
        
        app_logger.info(f"Image replacement completed: {replaced_count} images replaced with S3 URLs")
        
        return modified_response
    
    def _recursive_replace_images(self, obj: Any, replacement_map: Dict[str, Any], path: str = "root") -> None:
        """Recursively replace image data in the response object."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}"
                
                # Check if this path has a replacement
                if current_path in replacement_map:
                    replacement = replacement_map[current_path]
                    if replacement['type'] == 's3_url':
                        # Replace with S3 URL or image object
                        obj[key] = replacement['image_object']
                    # For fallback, keep original (no change needed)
                else:
                    # Recursively process nested structures
                    self._recursive_replace_images(value, replacement_map, current_path)
                    
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]"
                self._recursive_replace_images(item, replacement_map, current_path)
