"""
PDF Image Extraction Utility - DEPRECATED

⚠️  DEPRECATION WARNING: This module is deprecated as of the migration to Mistral AI's native image extraction.
⚠️  
⚠️  The n8n-tools service now uses Mistral AI's built-in image extraction capabilities which provide:
⚠️  - Better accuracy and quality
⚠️  - Native coordinate information  
⚠️  - Improved performance
⚠️  - Consistent API integration
⚠️
⚠️  This module is kept for backward compatibility and emergency fallback only.
⚠️  It will be removed in a future version.
⚠️
⚠️  For new implementations, use the Mistral OCR service directly via:
⚠️  - app.services.mistral_service.MistralOCRService
⚠️  - The process_mistral_ocr_response() method provides enhanced image extraction
⚠️
⚠️  MIGRATION GUIDE:
⚠️  
⚠️  OLD (deprecated):
⚠️    from app.utils.pdf_image_extractor import PDFImageExtractor
⚠️    extractor = PDFImageExtractor()
⚠️    images = extractor.extract_images_from_pdf(pdf_content)
⚠️  
⚠️  NEW (recommended):
⚠️    from app.services.mistral_service import MistralOCRService
⚠️    service = MistralOCRService()
⚠️    result = await service.process_file_ocr(
⚠️        file_content=pdf_content,
⚠️        filename="document.pdf",
⚠️        api_key="your_mistral_key",
⚠️        options={'include_image_base64': True}
⚠️    )
⚠️    images = result['pages'][page_num]['images']  # Enhanced format
⚠️
⚠️  Benefits of migration:
⚠️  - Native API integration with better accuracy
⚠️  - Enhanced coordinate and position data
⚠️  - Quality assessment and confidence scoring
⚠️  - Better format detection and metadata
⚠️  - Improved performance and reliability

Legacy PDF image extraction utility.
Extracts images directly from PDF files when OCR APIs don't provide them.
"""

import base64
import io
import warnings
from typing import List, Dict, Any, Optional, Tuple
from pypdf import PdfReader
import fitz  # PyMuPDF for better image extraction
from PIL import Image
import re

from app.core.logging import app_logger

# Issue deprecation warning when this module is imported
warnings.warn(
    "PDFImageExtractor is deprecated. Use Mistral AI's native image extraction instead. "
    "This module will be removed in a future version. "
    "See app.services.mistral_service.MistralOCRService for the recommended approach.",
    DeprecationWarning,
    stacklevel=2
)


class PDFImageExtractor:
    """
    DEPRECATED: Extract images directly from PDF files.
    
    ⚠️ WARNING: This class is deprecated and will be removed in a future version.
    ⚠️ Use Mistral AI's native image extraction instead via MistralOCRService.
    ⚠️ 
    ⚠️ Migration path:
    ⚠️ - Replace PDFImageExtractor usage with MistralOCRService
    ⚠️ - Use process_mistral_ocr_response() for enhanced image data
    ⚠️ - Leverage Mistral's native coordinate and quality information
    """
    
    def __init__(self):
        """Initialize the DEPRECATED PDF Image Extractor."""
        warnings.warn(
            "PDFImageExtractor is deprecated. Use MistralOCRService instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.supported_formats = ['jpeg', 'jpg', 'png', 'tiff', 'bmp']
        
        app_logger.warning(
            "DEPRECATED: PDFImageExtractor is being used. "
            "This will be removed in a future version. "
            "Migrate to MistralOCRService for better image extraction."
        )
    
    def extract_images_from_pdf(self, pdf_content: bytes, min_size: int = 50) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Extract images directly from PDF content.
        
        ⚠️ WARNING: This method is deprecated. Use MistralOCRService.process_file_ocr() instead.
        
        Args:
            pdf_content: PDF file content as bytes
            min_size: Minimum image dimension in pixels
            
        Returns:
            List of extracted image objects with base64 data
        """
        warnings.warn(
            "extract_images_from_pdf() is deprecated. Use MistralOCRService.process_file_ocr() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        app_logger.warning(
            "DEPRECATED METHOD CALLED: extract_images_from_pdf(). "
            "This method will be removed. Use MistralOCRService instead."
        )
        try:
            extracted_images = []
            
            # Use PyMuPDF for better image extraction
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            
            image_counter = 1
            
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                image_list = page.get_images()
                
                app_logger.info(f"Page {page_num + 1}: Found {len(image_list)} images")
                
                for img_index, img in enumerate(image_list):
                    try:
                        # Get image data
                        xref = img[0]
                        base_image = pdf_document.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        
                        # Convert to PIL Image for processing
                        pil_image = Image.open(io.BytesIO(image_bytes))
                        
                        # Check minimum size
                        if pil_image.width < min_size or pil_image.height < min_size:
                            app_logger.debug(f"Skipping small image: {pil_image.width}x{pil_image.height}")
                            continue
                        
                        # Convert to base64
                        if image_ext.lower() not in ['jpg', 'jpeg', 'png']:
                            # Convert to PNG for unsupported formats
                            buffer = io.BytesIO()
                            pil_image.save(buffer, format='PNG')
                            image_bytes = buffer.getvalue()
                            image_ext = 'png'
                        
                        base64_data = base64.b64encode(image_bytes).decode('utf-8')
                        
                        # Get image position on page
                        page_dict = page.get_displaylist().get_pixmap().pil_tobytes()
                        
                        # Create image object
                        image_obj = {
                            'id': f'pdf_img_{page_num + 1}_{img_index + 1}',
                            'sequence_number': image_counter,
                            'page_number': page_num + 1,
                            'coordinates': {
                                'normalized': {
                                    'x1': 0.0, 'y1': 0.0, 'x2': 1.0, 'y2': 1.0  # TODO: Get actual coordinates
                                },
                                'absolute': None,
                                'relative_position': 'extracted_from_pdf'
                            },
                            'annotation': f'Extracted image {image_counter}',
                            'extraction_quality': {
                                'confidence': 0.9,  # High confidence for direct extraction
                                'clarity': 'good',
                                'completeness': 'complete'
                            },
                            'format_info': {
                                'detected_format': image_ext,
                                'mime_type': f'image/{image_ext}',
                                'is_vector': False
                            },
                            'base64_data': base64_data,
                            'size_info': {
                                'width': pil_image.width,
                                'height': pil_image.height,
                                'size_bytes': len(image_bytes)
                            },
                            'position_analysis': {
                                'extraction_method': 'direct_pdf_extraction',
                                'pdf_xref': xref
                            }
                        }
                        
                        extracted_images.append(image_obj)
                        image_counter += 1
                        
                        app_logger.info(f"Extracted image {image_counter-1}: {pil_image.width}x{pil_image.height} {image_ext}")
                        
                    except Exception as e:
                        app_logger.warning(f"Failed to extract image {img_index + 1} from page {page_num + 1}: {str(e)}")
                        continue
            
            pdf_document.close()
            app_logger.info(f"Successfully extracted {len(extracted_images)} images from PDF")
            return extracted_images
            
        except Exception as e:
            app_logger.error(f"Failed to extract images from PDF: {str(e)}")
            return []
    
    def fallback_extract_with_pypdf(self, pdf_content: bytes) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Fallback image extraction using PyPDF (less reliable but more compatible).
        
        ⚠️ WARNING: This method is deprecated. Use MistralOCRService.process_file_ocr() instead.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            List of extracted image objects
        """
        warnings.warn(
            "fallback_extract_with_pypdf() is deprecated. Use MistralOCRService.process_file_ocr() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        app_logger.warning(
            "DEPRECATED METHOD CALLED: fallback_extract_with_pypdf(). "
            "This method will be removed. Use MistralOCRService instead."
        )
        try:
            extracted_images = []
            reader = PdfReader(io.BytesIO(pdf_content))
            
            image_counter = 1
            
            for page_num, page in enumerate(reader.pages):
                if hasattr(page, 'images'):
                    for img_name, img_obj in page.images.items():
                        try:
                            # Extract image data
                            image_data = img_obj.data
                            
                            if len(image_data) < 1000:  # Skip very small images
                                continue
                            
                            # Convert to base64
                            base64_data = base64.b64encode(image_data).decode('utf-8')
                            
                            # Try to determine format
                            image_format = 'unknown'
                            if image_data.startswith(b'\xff\xd8'):
                                image_format = 'jpeg'
                            elif image_data.startswith(b'\x89PNG'):
                                image_format = 'png'
                            
                            image_obj = {
                                'id': f'pypdf_img_{page_num + 1}_{image_counter}',
                                'sequence_number': image_counter,
                                'page_number': page_num + 1,
                                'coordinates': {
                                    'normalized': {'x1': 0.0, 'y1': 0.0, 'x2': 1.0, 'y2': 1.0},
                                    'absolute': None,
                                    'relative_position': 'extracted_with_pypdf'
                                },
                                'annotation': f'PyPDF extracted image {image_counter}',
                                'extraction_quality': {
                                    'confidence': 0.7,
                                    'clarity': 'unknown',
                                    'completeness': 'complete'
                                },
                                'format_info': {
                                    'detected_format': image_format,
                                    'mime_type': f'image/{image_format}',
                                    'is_vector': False
                                },
                                'base64_data': base64_data,
                                'size_info': {
                                    'size_bytes': len(image_data)
                                },
                                'position_analysis': {
                                    'extraction_method': 'pypdf_extraction',
                                    'source_name': img_name
                                }
                            }
                            
                            extracted_images.append(image_obj)
                            image_counter += 1
                            
                        except Exception as e:
                            app_logger.warning(f"Failed to extract PyPDF image {img_name}: {str(e)}")
                            continue
            
            return extracted_images
            
        except Exception as e:
            app_logger.error(f"PyPDF fallback extraction failed: {str(e)}")
            return []
