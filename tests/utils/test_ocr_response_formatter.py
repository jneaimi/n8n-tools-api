"""
Test suite for enhanced OCR response formatting.

Tests the comprehensive OCR response formatting utilities to ensure
proper parsing, structuring, and validation of Mistral AI OCR responses.
"""

import pytest
import json
import time
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.utils.ocr_response_formatter import OCRResponseFormatter


class TestOCRResponseFormatter:
    """Test cases for OCR response formatting functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = OCRResponseFormatter()
        self.sample_mistral_response = {
            'status': 'success',
            'model_used': 'mistral-ocr-latest',
            'pages_processed': 2,
            'document_size_bytes': 1024000,
            'total_text_length': 1500,
            'total_images_extracted': 3,
            'pages': [
                {
                    'page_number': 1,
                    'text': 'This is the first page content.\n\n# Header 1\n\nSome paragraph text with **bold** formatting.',
                    'markdown': 'This is the first page content.\n\n# Header 1\n\nSome paragraph text with **bold** formatting.',
                    'dimensions': {'width': 612, 'height': 792},
                    'images': [
                        {
                            'id': 'img_1_1',
                            'coordinates': {
                                'top_left_x': 100,
                                'top_left_y': 200,
                                'bottom_right_x': 300,
                                'bottom_right_y': 400
                            },
                            'base64_data': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAFfqlNNwgAAAABJRU5ErkJggg==',
                            'annotation': 'Sample image description'
                        }
                    ]
                },
                {
                    'page_number': 2,
                    'text': 'Second page content here.\n\n## Subsection\n\nMore content with different formatting.',
                    'markdown': 'Second page content here.\n\n## Subsection\n\nMore content with different formatting.',
                    'dimensions': {'width': 612, 'height': 792},
                    'images': [
                        {
                            'id': 'img_2_1',
                            'coordinates': {
                                'top_left_x': 50,
                                'top_left_y': 100,
                                'bottom_right_x': 200,
                                'bottom_right_y': 250
                            },
                            'base64_data': '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwA/AA==',
                            'annotation': 'Chart or diagram'
                        },
                        {
                            'id': 'img_2_2',
                            'coordinates': {
                                'top_left_x': 400,
                                'top_left_y': 500,
                                'bottom_right_x': 550,
                                'bottom_right_y': 650
                            },
                            'base64_data': 'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7',
                            'annotation': 'Logo or icon'
                        }
                    ]
                }
            ],
            'document_annotation': 'Test document with mixed content including headers, text, and images.',
            'processing_metadata': {
                'api_version': 'v1',
                'service_provider': 'mistral-ai',
                'extraction_timestamp': time.time(),
                'features_used': {
                    'text_extraction': True,
                    'image_extraction': True,
                    'structure_preservation': True,
                    'markdown_formatting': True
                }
            }
        }
    
    def test_format_complete_ocr_response(self):
        """Test formatting a complete OCR response with all features."""
        start_time = time.time()
        
        result = self.formatter.format_ocr_response(
            mistral_response=self.sample_mistral_response,
            source_type="file_upload",
            source_identifier="test_document.pdf",
            processing_start_time=start_time,
            include_images=True,
            include_metadata=True
        )
        
        # Validate response structure
        assert result['status'] == 'success'
        assert 'extracted_text' in result
        assert 'images' in result
        assert 'metadata' in result
        assert 'processing_info' in result
        assert 'validation' in result
        
        # Validate text extraction
        assert 'first page content' in result['extracted_text']
        assert 'Second page content' in result['extracted_text']
        assert 'PAGE 1 of 2' in result['extracted_text']
        assert 'PAGE 2 of 2' in result['extracted_text']
        
        # Validate images
        assert len(result['images']) == 3
        for image in result['images']:
            assert 'id' in image
            assert 'page_number' in image
            assert 'coordinates' in image
            assert 'sequence_number' in image
            assert 'extraction_quality' in image
        
        # Validate metadata
        metadata = result['metadata']
        assert metadata['source_info']['source_type'] == 'file_upload'
        assert metadata['document_info']['total_pages'] == 2
        assert metadata['content_analysis']['total_images_extracted'] == 3
        assert metadata['processing_stats']['model_used'] == 'mistral-ocr-latest'
        
        # Validate processing info
        processing_info = result['processing_info']
        assert processing_info['source_type'] == 'file_upload'
        assert processing_info['pages_processed'] == 2
        assert 'performance_metrics' in processing_info
    
    def test_enhanced_text_extraction(self):
        """Test enhanced text extraction with formatting improvements."""
        pages = self.sample_mistral_response['pages']
        
        extracted_text = self.formatter._extract_enhanced_text(pages)
        
        # Check for page headers
        assert 'PAGE 1 of 2' in extracted_text
        assert 'PAGE 2 of 2' in extracted_text
        
        # Check for page separators
        assert 'End of Page' in extracted_text
        
        # Check text cleaning
        assert extracted_text.strip()  # No leading/trailing whitespace
        assert '# Header 1' in extracted_text  # Markdown preserved
        assert '## Subsection' in extracted_text
    
    def test_enhanced_image_formatting(self):
        """Test enhanced image formatting with coordinate normalization."""
        pages = self.sample_mistral_response['pages']
        
        formatted_images = self.formatter._format_enhanced_images(pages)
        
        assert len(formatted_images) == 3
        
        # Test first image
        img1 = formatted_images[0]
        assert img1['id'] == 'img_1_1'
        assert img1['page_number'] == 1
        assert img1['sequence_number'] == 1
        assert 'coordinates' in img1
        assert 'absolute' in img1['coordinates']
        assert 'relative' in img1['coordinates']
        assert 'dimensions' in img1['coordinates']
        assert 'extraction_quality' in img1
        assert 'format_info' in img1
        assert 'position_analysis' in img1
        
        # Test coordinate normalization
        coords = img1['coordinates']
        assert coords['absolute']['top_left_x'] == 100
        assert coords['relative']['top_left_x_percent'] > 0
        assert coords['dimensions']['width'] == 200  # 300 - 100
        assert coords['dimensions']['height'] == 200  # 400 - 200
    
    def test_metadata_extraction(self):
        """Test comprehensive metadata extraction."""
        metadata = self.formatter._extract_enhanced_metadata(
            self.sample_mistral_response,
            "test_document.pdf",
            "file_upload"
        )
        
        # Check source info
        assert metadata['source_info']['original_source'] == "test_document.pdf"
        assert metadata['source_info']['source_type'] == "file_upload"
        assert 'processed_at' in metadata['source_info']
        
        # Check document info
        assert metadata['document_info']['total_pages'] == 2
        assert metadata['document_info']['has_annotation'] == True
        assert metadata['document_info']['annotation'] == self.sample_mistral_response['document_annotation']
        
        # Check content analysis
        content_analysis = metadata['content_analysis']
        assert content_analysis['total_characters'] == 1500
        assert content_analysis['total_images_extracted'] == 3
        assert content_analysis['has_images'] == True
        assert 'content_density' in content_analysis
        assert 'language_detection' in content_analysis
        
        # Check processing stats
        proc_stats = metadata['processing_stats']
        assert proc_stats['model_used'] == 'mistral-ocr-latest'
        assert proc_stats['service_provider'] == 'mistral-ai'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
