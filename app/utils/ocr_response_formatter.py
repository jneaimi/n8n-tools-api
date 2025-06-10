"""
Advanced OCR response formatting utilities.

Provides comprehensive parsing and formatting of Mistral AI OCR responses
into standardized structures compatible with n8n workflows and API models.
"""

import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re

from app.models.ocr_models import OCRMetadata, OCRImage, OCRProcessingInfo, OCRSource
from app.core.logging import app_logger


class OCRResponseFormatter:
    """
    Advanced formatter for OCR API responses.
    
    Handles comprehensive parsing and structuring of Mistral AI OCR responses
    into standardized formats with enhanced metadata extraction and validation.
    """
    
    def __init__(self):
        """Initialize the OCR response formatter."""
        self.confidence_patterns = [
            r'confidence[:\s]*([0-9.]+)',
            r'accuracy[:\s]*([0-9.]+)',
            r'certainty[:\s]*([0-9.]+)'
        ]
    
    def format_ocr_response(
        self,
        mistral_response: Dict[str, Any],
        source_type: str,
        source_identifier: str,
        processing_start_time: float,
        include_images: bool = True,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Format complete OCR response from Mistral API data.
        
        Args:
            mistral_response: Raw response from Mistral OCR service
            source_type: Type of source ('file_upload' or 'url')
            source_identifier: Original filename or URL
            processing_start_time: Start time for processing duration calculation
            include_images: Whether to include extracted images
            include_metadata: Whether to include document metadata
            
        Returns:
            Formatted response compatible with OCRResponse model
        """
        try:
            app_logger.info(f"Formatting OCR response for {source_type}: {source_identifier}")
            
            # Extract and combine text from all pages
            extracted_text = self._extract_enhanced_text(mistral_response.get('pages', []))
            
            # Extract and format images if requested
            images = []
            if include_images:
                images = self._format_enhanced_images(mistral_response.get('pages', []))
            
            # Extract metadata if requested
            metadata = None
            if include_metadata:
                metadata = self._extract_enhanced_metadata(
                    mistral_response, 
                    source_identifier, 
                    source_type
                )
            
            # Create comprehensive processing info
            processing_info = self._create_processing_info(
                mistral_response,
                source_type,
                processing_start_time
            )
            
            # Validate response integrity
            validation_result = self._validate_response_integrity(
                extracted_text, images, mistral_response
            )
            
            response = {
                "status": "success",
                "message": f"OCR processing completed for {source_type}",
                "extracted_text": extracted_text,
                "images": images if include_images else [],
                "metadata": metadata if include_metadata else None,
                "processing_info": processing_info,
                "validation": validation_result
            }
            
            app_logger.info(f"OCR response formatted successfully: {len(extracted_text)} chars, {len(images)} images")
            return response
            
        except Exception as e:
            app_logger.error(f"Error formatting OCR response: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to format OCR response: {str(e)}")
    
    def _extract_enhanced_text(self, pages: List[Dict[str, Any]]) -> str:
        """
        Extract and combine text with enhanced formatting and structure preservation.
        
        Args:
            pages: List of page data from Mistral response
            
        Returns:
            Enhanced formatted text with proper structure
        """
        if not pages:
            return ""
        
        text_segments = []
        total_pages = len(pages)
        
        for page in pages:
            page_number = page.get('page_number', page.get('index', 0) + 1)
            page_text = page.get('text', page.get('markdown', ''))
            
            if not page_text.strip():
                continue
            
            # Add page header for multi-page documents
            if total_pages > 1:
                page_header = f"\n{'='*50}\n📄 PAGE {page_number} of {total_pages}\n{'='*50}\n"
                text_segments.append(page_header)
            
            # Clean and format text
            cleaned_text = self._clean_extracted_text(page_text)
            text_segments.append(cleaned_text)
            
            # Add page separator
            if total_pages > 1 and page_number < total_pages:
                text_segments.append("\n" + "-"*30 + " End of Page " + "-"*30 + "\n")
        
        combined_text = '\n'.join(text_segments).strip()
        
        # Apply final formatting improvements
        combined_text = self._apply_text_formatting_enhancements(combined_text)
        
        return combined_text
    
    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text with normalized formatting
        """
        if not text:
            return ""
        
        # Remove excessive whitespace while preserving structure
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Fix common OCR artifacts
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between words
        text = re.sub(r'(\d+)([A-Za-z])', r'\1 \2', text)  # Space between numbers and letters
        
        # Normalize punctuation
        text = re.sub(r'\s+([.!?,:;])', r'\1', text)  # Remove space before punctuation
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)  # Ensure space after sentence end
        
        return text.strip()
    
    def _apply_text_formatting_enhancements(self, text: str) -> str:
        """
        Apply final formatting enhancements to improve readability.
        
        Args:
            text: Text to enhance
            
        Returns:
            Enhanced text with improved formatting
        """
        # Preserve markdown formatting from Mistral
        # Add table of contents for very long documents
        if len(text) > 5000:
            headers = re.findall(r'^#+\s+(.+)$', text, re.MULTILINE)
            if len(headers) > 3:
                toc = "\n📋 **Table of Contents**\n" + "\n".join(f"• {header}" for header in headers[:10])
                if len(headers) > 10:
                    toc += f"\n• ... and {len(headers) - 10} more sections"
                text = toc + "\n\n" + "-"*50 + "\n\n" + text
        
        return text
    
    def _format_enhanced_images(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format extracted images with enhanced coordinate mapping and metadata.
        
        Args:
            pages: List of page data from Mistral response
            
        Returns:
            List of formatted image objects with enhanced data
        """
        formatted_images = []
        image_counter = 1
        
        for page in pages:
            page_number = page.get('page_number', page.get('index', 0) + 1)
            page_dimensions = page.get('dimensions', {})
            
            for image in page.get('images', []):
                try:
                    # Enhanced image formatting
                    formatted_image = {
                        'id': image.get('id', f"img_{page_number}_{image_counter}"),
                        'sequence_number': image_counter,
                        'page_number': page_number,
                        'coordinates': self._normalize_image_coordinates(
                            image.get('coordinates', {}), 
                            page_dimensions
                        ),
                        'annotation': image.get('annotation', ''),
                        'extraction_quality': self._assess_image_quality(image),
                        'format_info': self._detect_image_format(image.get('base64_data', ''))
                    }
                    
                    # Include base64 data if present and valid
                    base64_data = image.get('base64_data', '')
                    if base64_data and self._validate_base64_image(base64_data):
                        formatted_image['base64_data'] = base64_data
                        formatted_image['size_info'] = self._get_image_size_info(base64_data)
                    
                    # Add relative positioning information
                    if formatted_image['coordinates']:
                        formatted_image['position_analysis'] = self._analyze_image_position(
                            formatted_image['coordinates']
                        )
                    
                    formatted_images.append(formatted_image)
                    image_counter += 1
                    
                except Exception as e:
                    app_logger.warning(f"Failed to format image {image_counter} on page {page_number}: {str(e)}")
                    continue
        
        # If no images were found in Mistral response, rely entirely on Mistral's capabilities
        if not formatted_images:
            app_logger.info(f"No images found in Mistral response - relying on Mistral's native extraction capabilities")
            
            # Extract image references from markdown text as informational fallback only
            text_references = self._extract_image_references_from_text(pages)
            if text_references:
                app_logger.info(f"Found {len(text_references)} image references in text content")
                formatted_images = text_references
            else:
                app_logger.info("No image data or references found in document")
        
        app_logger.info(f"Formatted {len(formatted_images)} images using Mistral native extraction")
        
        return formatted_images
    
    def _extract_image_references_from_text(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract image references from markdown text as fallback when no actual image data is available.
        
        Args:
            pages: List of page data from Mistral response
            
        Returns:
            List of placeholder image objects based on text references
        """
        import re
        formatted_images = []
        image_counter = 1
        
        for page in pages:
            page_number = page.get('page_number', page.get('index', 0) + 1)
            page_text = page.get('text', '') or page.get('markdown', '')
            
            # Find image markdown references like ![img-0.jpeg](img-0.jpeg)
            image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
            matches = re.findall(image_pattern, page_text)
            
            for match in matches:
                alt_text, filename = match
                try:
                    formatted_image = {
                        'id': f"ref_{image_counter}",
                        'sequence_number': image_counter,
                        'page_number': page_number,
                        'coordinates': {
                            'normalized': {
                                'x1': 0.0, 'y1': 0.0, 'x2': 1.0, 'y2': 1.0  # Default to full page
                            },
                            'absolute': None,
                            'relative_position': 'unknown'
                        },
                        'annotation': alt_text or f"Text reference to image: {filename}",
                        'extraction_quality': {
                            'confidence': 0.3,  # Lower confidence for text references
                            'clarity': 'text_reference_only',
                            'completeness': 'reference_only',
                            'source': 'markdown_text'
                        },
                        'format_info': {
                            'detected_format': filename.split('.')[-1] if '.' in filename else 'unknown',
                            'mime_type': f"image/{filename.split('.')[-1]}" if '.' in filename else 'image/unknown',
                            'is_vector': False,
                            'is_text_reference': True
                        },
                        'base64_data': None,  # No actual image data - text reference only
                        'size_info': None,
                        'position_analysis': {
                            'text_reference': True,
                            'filename': filename,
                            'extraction_method': 'mistral_text_reference',
                            'note': 'This is a text reference only - no actual image data was extracted by Mistral'
                        }
                    }
                    
                    formatted_images.append(formatted_image)
                    image_counter += 1
                    
                except Exception as e:
                    app_logger.warning(f"Failed to create image reference for {filename}: {str(e)}")
                    continue
        
        return formatted_images
    
    def _normalize_image_coordinates(
        self, 
        coordinates: Dict[str, Any], 
        page_dimensions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Normalize image coordinates with enhanced positioning data.
        
        Args:
            coordinates: Raw coordinate data from Mistral
            page_dimensions: Page dimension information
            
        Returns:
            Normalized coordinate object with additional positioning data
        """
        if not coordinates:
            return {}
        
        normalized = {
            'absolute': {
                'top_left_x': coordinates.get('top_left_x', 0),
                'top_left_y': coordinates.get('top_left_y', 0),
                'bottom_right_x': coordinates.get('bottom_right_x', 0),
                'bottom_right_y': coordinates.get('bottom_right_y', 0)
            }
        }
        
        # Calculate relative positions if page dimensions are available
        if page_dimensions:
            page_width = page_dimensions.get('width', 1)
            page_height = page_dimensions.get('height', 1)
            
            if page_width > 0 and page_height > 0:
                normalized['relative'] = {
                    'top_left_x_percent': (normalized['absolute']['top_left_x'] / page_width) * 100,
                    'top_left_y_percent': (normalized['absolute']['top_left_y'] / page_height) * 100,
                    'bottom_right_x_percent': (normalized['absolute']['bottom_right_x'] / page_width) * 100,
                    'bottom_right_y_percent': (normalized['absolute']['bottom_right_y'] / page_height) * 100
                }
                
                # Calculate dimensions
                normalized['dimensions'] = {
                    'width': normalized['absolute']['bottom_right_x'] - normalized['absolute']['top_left_x'],
                    'height': normalized['absolute']['bottom_right_y'] - normalized['absolute']['top_left_y'],
                    'width_percent': normalized['relative']['bottom_right_x_percent'] - normalized['relative']['top_left_x_percent'],
                    'height_percent': normalized['relative']['bottom_right_y_percent'] - normalized['relative']['top_left_y_percent']
                }
        
        return normalized    
    def _assess_image_quality(self, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the quality and characteristics of extracted image.
        
        Args:
            image_data: Image data from Mistral response
            
        Returns:
            Quality assessment information
        """
        quality_info = {
            'has_annotation': bool(image_data.get('annotation', '').strip()),
            'has_base64_data': bool(image_data.get('base64_data', '').strip()),
            'coordinate_precision': 'unknown'
        }
        
        # Assess coordinate precision
        coordinates = image_data.get('coordinates', {})
        if coordinates:
            # Check if coordinates have decimal precision
            coords_list = [
                coordinates.get('top_left_x', 0),
                coordinates.get('top_left_y', 0),
                coordinates.get('bottom_right_x', 0),
                coordinates.get('bottom_right_y', 0)
            ]
            
            has_decimals = any(isinstance(coord, float) and coord % 1 != 0 for coord in coords_list)
            quality_info['coordinate_precision'] = 'high' if has_decimals else 'standard'
        
        return quality_info
    
    def _detect_image_format(self, base64_data: str) -> Dict[str, Any]:
        """
        Detect image format from base64 data.
        
        Args:
            base64_data: Base64 encoded image data
            
        Returns:
            Format information
        """
        format_info = {
            'detected_format': 'unknown',
            'has_transparency': False,
            'estimated_compression': 'unknown'
        }
        
        if not base64_data:
            return format_info
        
        try:
            # Check image format from base64 header
            if base64_data.startswith('/9j/'):
                format_info['detected_format'] = 'jpeg'
                format_info['estimated_compression'] = 'lossy'
            elif base64_data.startswith('iVBORw0KGgo'):
                format_info['detected_format'] = 'png'
                format_info['has_transparency'] = True
                format_info['estimated_compression'] = 'lossless'
            elif base64_data.startswith('R0lGODlh'):
                format_info['detected_format'] = 'gif'
                format_info['has_transparency'] = True
                format_info['estimated_compression'] = 'lossless'
            elif base64_data.startswith('UklGR'):
                format_info['detected_format'] = 'webp'
                format_info['estimated_compression'] = 'variable'
        except Exception as e:
            app_logger.debug(f"Could not detect image format: {str(e)}")
        
        return format_info
    
    def _validate_base64_image(self, base64_data: str) -> bool:
        """
        Validate base64 image data.
        
        Args:
            base64_data: Base64 encoded image data
            
        Returns:
            True if valid base64 image data
        """
        if not base64_data:
            return False
        
        try:
            # Check if it's valid base64
            import base64
            decoded = base64.b64decode(base64_data)
            
            # Check minimum size (should be more than just a few bytes)
            return len(decoded) > 50
        except Exception:
            return False
    
    def _get_image_size_info(self, base64_data: str) -> Dict[str, Any]:
        """
        Extract size information from base64 image data.
        
        Args:
            base64_data: Base64 encoded image data
            
        Returns:
            Size information
        """
        try:
            import base64
            decoded = base64.b64decode(base64_data)
            
            return {
                'data_size_bytes': len(decoded),
                'data_size_kb': round(len(decoded) / 1024, 2),
                'base64_length': len(base64_data)
            }
        except Exception as e:
            app_logger.debug(f"Could not extract image size info: {str(e)}")
            return {}
    
    def _analyze_image_position(self, coordinates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze image position and provide contextual information.
        
        Args:
            coordinates: Normalized coordinate data
            
        Returns:
            Position analysis information
        """
        analysis = {
            'quadrant': 'unknown',
            'relative_size': 'unknown',
            'position_type': 'unknown'
        }
        
        try:
            if 'relative' in coordinates:
                rel_coords = coordinates['relative']
                center_x = (rel_coords['top_left_x_percent'] + rel_coords['bottom_right_x_percent']) / 2
                center_y = (rel_coords['top_left_y_percent'] + rel_coords['bottom_right_y_percent']) / 2
                
                # Determine quadrant
                if center_x < 50 and center_y < 50:
                    analysis['quadrant'] = 'top-left'
                elif center_x >= 50 and center_y < 50:
                    analysis['quadrant'] = 'top-right'
                elif center_x < 50 and center_y >= 50:
                    analysis['quadrant'] = 'bottom-left'
                else:
                    analysis['quadrant'] = 'bottom-right'
                
                # Determine relative size
                if 'dimensions' in coordinates:
                    width_percent = coordinates['dimensions'].get('width_percent', 0)
                    height_percent = coordinates['dimensions'].get('height_percent', 0)
                    area_percent = width_percent * height_percent / 100
                    
                    if area_percent > 25:
                        analysis['relative_size'] = 'large'
                    elif area_percent > 5:
                        analysis['relative_size'] = 'medium'
                    else:
                        analysis['relative_size'] = 'small'
                
                # Determine position type
                if center_x > 20 and center_x < 80:
                    analysis['position_type'] = 'centered-horizontal'
                elif center_x <= 20:
                    analysis['position_type'] = 'left-aligned'
                else:
                    analysis['position_type'] = 'right-aligned'
                    
        except Exception as e:
            app_logger.debug(f"Could not analyze image position: {str(e)}")
        
        return analysis
    
    def _extract_enhanced_metadata(
        self, 
        mistral_response: Dict[str, Any], 
        source_identifier: str,
        source_type: str
    ) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from Mistral response and document analysis.
        
        Args:
            mistral_response: Complete Mistral API response
            source_identifier: Original filename or URL
            source_type: Type of source processing
            
        Returns:
            Enhanced metadata object
        """
        try:
            metadata = {
                'source_info': {
                    'original_source': source_identifier,
                    'source_type': source_type,
                    'processed_at': datetime.utcnow().isoformat() + 'Z'
                },
                'document_info': {},
                'content_analysis': {},
                'processing_stats': {}
            }
            
            # Extract document annotation if available
            doc_annotation = mistral_response.get('document_annotation', '')
            if doc_annotation:
                metadata['document_info']['annotation'] = doc_annotation
                metadata['document_info']['has_annotation'] = True
            else:
                metadata['document_info']['has_annotation'] = False
            
            # Extract basic document statistics
            pages = mistral_response.get('pages', [])
            metadata['document_info'].update({
                'total_pages': len(pages),
                'pages_processed': mistral_response.get('pages_processed', len(pages))
            })
            
            # Analyze content characteristics
            total_text_length = mistral_response.get('total_text_length', 0)
            total_images = mistral_response.get('total_images_extracted', 0)
            
            metadata['content_analysis'] = {
                'total_characters': total_text_length,
                'estimated_words': total_text_length // 5 if total_text_length > 0 else 0,
                'total_images_extracted': total_images,
                'has_images': total_images > 0,
                'content_density': self._calculate_content_density(pages),
                'language_detection': self._detect_primary_language(pages)
            }
            
            # Extract processing statistics
            metadata['processing_stats'] = {
                'model_used': mistral_response.get('model_used', 'mistral-ocr-latest'),
                'service_provider': 'mistral-ai',
                'document_size_bytes': mistral_response.get('document_size_bytes', 0),
                'api_version': 'v1'
            }
            
            # Add confidence scoring if available
            confidence_score = self._calculate_confidence_score(pages)
            if confidence_score is not None:
                metadata['content_analysis']['confidence_score'] = confidence_score
            
            return metadata
            
        except Exception as e:
            app_logger.error(f"Error extracting enhanced metadata: {str(e)}")
            return {
                'source_info': {
                    'original_source': source_identifier,
                    'source_type': source_type,
                    'processed_at': datetime.utcnow().isoformat() + 'Z'
                },
                'error': f"Metadata extraction failed: {str(e)}"
            }
    
    def _calculate_content_density(self, pages: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate content density metrics for the document.
        
        Args:
            pages: List of page data
            
        Returns:
            Content density information
        """
        try:
            if not pages:
                return {'text_density': 0.0, 'image_density': 0.0}
            
            total_text_chars = sum(len(page.get('text', '')) for page in pages)
            total_images = sum(len(page.get('images', [])) for page in pages)
            total_pages = len(pages)
            
            return {
                'text_density': total_text_chars / total_pages if total_pages > 0 else 0.0,
                'image_density': total_images / total_pages if total_pages > 0 else 0.0,
                'content_ratio': total_text_chars / max(total_images, 1) if total_images > 0 else total_text_chars
            }
        except Exception:
            return {'text_density': 0.0, 'image_density': 0.0}
    
    def _detect_primary_language(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect the primary language of the document content.
        
        Args:
            pages: List of page data
            
        Returns:
            Language detection information
        """
        try:
            # Simple language detection based on character patterns
            all_text = ' '.join(page.get('text', '') for page in pages)
            
            if not all_text.strip():
                return {'detected': 'unknown', 'confidence': 0.0}
            
            # Basic language detection patterns
            language_patterns = {
                'english': r'[a-zA-Z\s]+',
                'spanish': r'[a-zA-ZñÑáéíóúüÁÉÍÓÚÜ\s]+',
                'french': r'[a-zA-ZàâäéèêëïîôöùûüÿñçÀÂÄÉÈÊËÏÎÔÖÙÛÜŸÑÇ\s]+',
                'german': r'[a-zA-ZäöüßÄÖÜ\s]+',
                'chinese': r'[\u4e00-\u9fff]+',
                'arabic': r'[\u0600-\u06ff]+',
                'russian': r'[а-яёА-ЯЁ\s]+'
            }
            
            # Count matches for each language
            language_scores = {}
            for lang, pattern in language_patterns.items():
                matches = re.findall(pattern, all_text)
                score = sum(len(match) for match in matches) / len(all_text) if all_text else 0
                language_scores[lang] = score
            
            # Find the highest scoring language
            best_lang = max(language_scores.items(), key=lambda x: x[1])
            
            return {
                'detected': best_lang[0] if best_lang[1] > 0.5 else 'unknown',
                'confidence': min(best_lang[1], 1.0),
                'scores': language_scores
            }
            
        except Exception as e:
            app_logger.debug(f"Language detection failed: {str(e)}")
            return {'detected': 'unknown', 'confidence': 0.0}
    
    def _calculate_confidence_score(self, pages: List[Dict[str, Any]]) -> Optional[float]:
        """
        Calculate overall confidence score from page data.
        
        Args:
            pages: List of page data
            
        Returns:
            Confidence score or None if unavailable
        """
        try:
            confidence_scores = []
            
            for page in pages:
                page_text = page.get('text', '')
                
                # Look for confidence indicators in text or metadata
                for pattern in self.confidence_patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE)
                    for match in matches:
                        try:
                            score = float(match)
                            if 0 <= score <= 1:
                                confidence_scores.append(score)
                            elif 0 <= score <= 100:
                                confidence_scores.append(score / 100)
                        except ValueError:
                            continue
            
            if confidence_scores:
                return sum(confidence_scores) / len(confidence_scores)
            
            return None
            
        except Exception:
            return None
    
    def _create_processing_info(
        self,
        mistral_response: Dict[str, Any],
        source_type: str,
        processing_start_time: float
    ) -> Dict[str, Any]:
        """
        Create comprehensive processing information.
        
        Args:
            mistral_response: Complete Mistral API response
            source_type: Type of source processing
            processing_start_time: Start time for duration calculation
            
        Returns:
            Detailed processing information
        """
        try:
            processing_time_ms = (time.time() - processing_start_time) * 1000
            
            processing_info = {
                'processing_time_ms': round(processing_time_ms, 2),
                'source_type': source_type,
                'ai_model_used': mistral_response.get('model_used', 'mistral-ocr-latest'),
                'service_provider': 'mistral-ai',
                'pages_processed': mistral_response.get('pages_processed', 0),
                'features_used': mistral_response.get('processing_metadata', {}).get('features_used', {}),
                'performance_metrics': {
                    'characters_per_second': 0,
                    'pages_per_second': 0,
                    'processing_efficiency': 'unknown'
                }
            }
            
            # Calculate performance metrics
            total_chars = mistral_response.get('total_text_length', 0)
            total_pages = mistral_response.get('pages_processed', 0)
            processing_time_seconds = processing_time_ms / 1000
            
            if processing_time_seconds > 0:
                processing_info['performance_metrics']['characters_per_second'] = round(
                    total_chars / processing_time_seconds, 2
                )
                processing_info['performance_metrics']['pages_per_second'] = round(
                    total_pages / processing_time_seconds, 2
                )
                
                # Determine processing efficiency
                if processing_time_ms < 5000:
                    efficiency = 'excellent'
                elif processing_time_ms < 15000:
                    efficiency = 'good'
                elif processing_time_ms < 30000:
                    efficiency = 'average'
                else:
                    efficiency = 'slow'
                
                processing_info['performance_metrics']['processing_efficiency'] = efficiency
            
            return processing_info
            
        except Exception as e:
            app_logger.error(f"Error creating processing info: {str(e)}")
            return {
                'processing_time_ms': (time.time() - processing_start_time) * 1000,
                'source_type': source_type,
                'error': f"Processing info creation failed: {str(e)}"
            }
    
    def _validate_response_integrity(
        self,
        extracted_text: str,
        images: List[Dict[str, Any]],
        mistral_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the integrity and completeness of the formatted response.
        
        Args:
            extracted_text: Formatted text content
            images: Formatted image objects
            mistral_response: Original Mistral response
            
        Returns:
            Validation results
        """
        try:
            validation = {
                'is_valid': True,
                'completeness_score': 1.0,
                'issues': [],
                'warnings': []
            }
            
            # Check text extraction completeness
            original_pages = mistral_response.get('pages', [])
            expected_text_length = sum(len(page.get('text', '')) for page in original_pages)
            
            if len(extracted_text) < expected_text_length * 0.8:
                validation['issues'].append('Text extraction may be incomplete')
                validation['completeness_score'] -= 0.2
            
            # Check image extraction completeness
            expected_images = sum(len(page.get('images', [])) for page in original_pages)
            if len(images) < expected_images:
                validation['warnings'].append(f'Expected {expected_images} images, got {len(images)}')
                validation['completeness_score'] -= 0.1
            
            # Check for empty content
            if not extracted_text.strip() and len(images) == 0:
                validation['issues'].append('No content extracted from document')
                validation['is_valid'] = False
                validation['completeness_score'] = 0.0
            
            # Validate image data integrity
            invalid_images = 0
            for image in images:
                if not image.get('id') or not image.get('coordinates'):
                    invalid_images += 1
            
            if invalid_images > 0:
                validation['warnings'].append(f'{invalid_images} images have incomplete data')
                validation['completeness_score'] -= (invalid_images / max(len(images), 1)) * 0.1
            
            # Final validation status
            if validation['completeness_score'] < 0.7:
                validation['is_valid'] = False
            
            validation['completeness_score'] = max(0.0, validation['completeness_score'])
            
            return validation
            
        except Exception as e:
            app_logger.error(f"Response validation failed: {str(e)}")
            return {
                'is_valid': False,
                'completeness_score': 0.0,
                'issues': [f'Validation error: {str(e)}']
            }
            result = self.formatter.format_ocr_response(
                mistral_response=empty_response,
                source_type="file_upload",
                source_identifier="empty.pdf",
                processing_start_time=time.time(),
                include_images=True,
                include_metadata=True
            )
            
            # Should handle gracefully and return structured response
            assert result['status'] == 'success'
            assert result['extracted_text'] == ''
            assert result['images'] == []
            
        except Exception as e:
            # Should raise ValueError with descriptive message
            assert isinstance(e, ValueError)
            assert 'Failed to format OCR response' in str(e)
    
    def test_malformed_data_handling(self):
        """Test handling of malformed or incomplete data."""
        malformed_response = {
            'pages': [
                {
                    # Missing required fields
                    'incomplete': True
                },
                {
                    'text': 'Valid page content',
                    'images': [
                        {
                            # Missing coordinates and other data
                            'id': 'incomplete_image'
                        }
                    ]
                }
            ]
        }
        
        # Should handle malformed data gracefully
        extracted_text = self.formatter._extract_enhanced_text(malformed_response['pages'])
        assert 'Valid page content' in extracted_text
        
        formatted_images = self.formatter._format_enhanced_images(malformed_response['pages'])
        # Should still format images even with missing data
        assert len(formatted_images) == 1
        assert formatted_images[0]['id'] == 'incomplete_image'
    
    def test_large_document_handling(self):
        """Test handling of large documents with many pages."""
        # Create a large document simulation
        large_response = {
            'pages': [
                {
                    'page_number': i,
                    'text': f'# Page {i} Header\n\nContent for page {i} with substantial text that would be typical in a real document. This includes multiple paragraphs and various formatting elements.',
                    'images': [
                        {
                            'id': f'img_{i}_1',
                            'coordinates': {
                                'top_left_x': 50 + (i * 10),
                                'top_left_y': 100 + (i * 15),
                                'bottom_right_x': 200 + (i * 10),
                                'bottom_right_y': 250 + (i * 15)
                            },
                            'base64_data': 'sample_base64_data',
                            'annotation': f'Image on page {i}'
                        }
                    ]
                }
                for i in range(1, 21)  # 20 pages
            ],
            'pages_processed': 20,
            'total_text_length': 15000,
            'total_images_extracted': 20,
            'model_used': 'mistral-ocr-latest'
        }
        
        # Test text extraction with table of contents generation
        extracted_text = self.formatter._extract_enhanced_text(large_response['pages'])
        
        # Should include table of contents for large documents
        assert '📋 **Table of Contents**' in extracted_text
        assert 'Page 1 Header' in extracted_text
        assert 'Page 20 Header' in extracted_text
        
        # Test image formatting for large number of images
        formatted_images = self.formatter._format_enhanced_images(large_response['pages'])
        assert len(formatted_images) == 20
        
        # Verify sequence numbering
        for i, image in enumerate(formatted_images, 1):
            assert image['sequence_number'] == i
    
    def test_url_source_formatting(self):
        """Test formatting responses from URL sources."""
        start_time = time.time()
        
        result = self.formatter.format_ocr_response(
            mistral_response=self.sample_mistral_response,
            source_type="url",
            source_identifier="https://example.com/document.pdf",
            processing_start_time=start_time,
            include_images=True,
            include_metadata=True
        )
        
        # Validate URL-specific formatting
        assert result['processing_info']['source_type'] == 'url'
        assert result['metadata']['source_info']['source_type'] == 'url'
        assert result['metadata']['source_info']['original_source'] == 'https://example.com/document.pdf'
    
    def test_no_images_scenario(self):
        """Test formatting when no images are requested or available."""
        # Response with no images
        no_images_response = {
            'pages': [
                {
                    'page_number': 1,
                    'text': 'Text-only document content',
                    'images': []
                }
            ],
            'pages_processed': 1,
            'total_text_length': 100,
            'total_images_extracted': 0,
            'model_used': 'mistral-ocr-latest'
        }
        
        result = self.formatter.format_ocr_response(
            mistral_response=no_images_response,
            source_type="file_upload",
            source_identifier="text_only.pdf",
            processing_start_time=time.time(),
            include_images=False,
            include_metadata=True
        )
        
        assert result['images'] == []
        assert result['metadata']['content_analysis']['has_images'] == False
        assert result['metadata']['content_analysis']['total_images_extracted'] == 0
    
    def test_confidence_score_extraction(self):
        """Test confidence score calculation from text content."""
        # Mock pages with confidence indicators
        pages_with_confidence = [
            {'text': 'Document processed with confidence: 0.95'},
            {'text': 'High accuracy: 87% on this section'},
            {'text': 'Recognition certainty: 0.92 for mathematical formulas'}
        ]
        
        confidence = self.formatter._calculate_confidence_score(pages_with_confidence)
        
        # Should extract and average confidence scores
        assert confidence is not None
        assert 0.0 <= confidence <= 1.0
    
    def test_text_cleaning_enhancements(self):
        """Test text cleaning and formatting improvements."""
        raw_text = "BadlyFormattedText    WithExtraSpaces\n\n\n\nAndMultipleNewlines123Numbers"
        
        cleaned = self.formatter._clean_extracted_text(raw_text)
        
        # Should fix formatting issues
        assert 'Badly Formatted Text' in cleaned or 'BadlyFormattedText' in cleaned
        assert cleaned.count('\n\n\n') == 0  # No triple newlines
        assert '   ' not in cleaned  # No excessive spaces
    
    def test_base64_validation(self):
        """Test base64 image data validation."""
        # Valid base64
        valid_b64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAFfqlNNwgAAAABJRU5ErkJggg=='
        assert self.formatter._validate_base64_image(valid_b64) == True
        
        # Invalid base64
        invalid_b64 = 'not_valid_base64_data'
        assert self.formatter._validate_base64_image(invalid_b64) == False
        
        # Empty string
        assert self.formatter._validate_base64_image('') == False
    
    def test_image_size_info_extraction(self):
        """Test image size information extraction."""
        valid_b64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAFfqlNNwgAAAABJRU5ErkJggg=='
        
        size_info = self.formatter._get_image_size_info(valid_b64)
        
        assert 'data_size_bytes' in size_info
        assert 'data_size_kb' in size_info
        assert 'base64_length' in size_info
        assert size_info['data_size_bytes'] > 0
        assert size_info['base64_length'] == len(valid_b64)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
