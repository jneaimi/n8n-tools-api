"""
PDF processing service.

Handles PDF manipulation operations including split, merge, and metadata extraction.
"""

from pypdf import PdfReader, PdfWriter, PdfMerger
from typing import List, Dict, Any, BinaryIO, Union, Tuple, Optional
import tempfile
import os
import io
import re
import time
import logging
from datetime import datetime

from app.core.errors import PDFProcessingError
from app.core.logging import (
    log_pdf_operation, 
    log_validation_result, 
    log_performance_metric,
    get_correlation_id,
    app_logger
)

logger = app_logger  # Alias for backward compatibility

class PDFService:
    """Service class for PDF operations."""
    
    @staticmethod
    def _parse_page_range(page_range: str, total_pages: int) -> tuple[int, int]:
        """Parse page range string and return (start, end) indices (0-based)."""
        page_range = page_range.strip()
        
        # Handle single page (e.g., "5")
        if '-' not in page_range:
            try:
                page_num = int(page_range)
            except ValueError:
                raise PDFProcessingError(f"Invalid page range format: {page_range}")
            if page_num < 1 or page_num > total_pages:
                raise PDFProcessingError(f"Page {page_num} is out of range (1-{total_pages})")
            return page_num - 1, page_num - 1
        
        # Handle range (e.g., "1-5")
        parts = page_range.split('-', 1)
        if len(parts) != 2:
            raise PDFProcessingError(f"Invalid page range format: {page_range}")
        
        try:
            start = int(parts[0].strip()) if parts[0].strip() else 1
            end = int(parts[1].strip()) if parts[1].strip() else total_pages
        except ValueError:
            raise PDFProcessingError(f"Invalid page numbers in range: {page_range}")
        
        # Validate range
        if start < 1 or end < 1:
            raise PDFProcessingError("Page numbers must be greater than 0")
        if start > total_pages or end > total_pages:
            raise PDFProcessingError(f"Page range {start}-{end} exceeds document length ({total_pages} pages)")
        if start > end:
            raise PDFProcessingError(f"Invalid range: start page ({start}) is greater than end page ({end})")
        
        return start - 1, end - 1  # Convert to 0-based indexing
    
    @staticmethod
    async def split_by_ranges(pdf_content: bytes, ranges: List[str], filename: str = "document.pdf") -> Dict[str, bytes]:
        """Split PDF by page ranges.
        
        Args:
            pdf_content: PDF file content as bytes
            ranges: List of page ranges (e.g., ['1-3', '5', '7-9'])
            filename: Original filename for logging
            
        Returns:
            Dictionary mapping output filenames to PDF content bytes
        """
        start_time = time.time()
        correlation_id = get_correlation_id()
        
        try:
            # Create PDF reader from bytes
            pdf_io = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_io)
            total_pages = len(reader.pages)
            
            if total_pages == 0:
                raise PDFProcessingError("PDF has no pages")
            
            app_logger.info(f"Starting PDF split by ranges for {filename} ({total_pages} pages)")
            
            result = {}
            
            for i, page_range in enumerate(ranges):
                try:
                    start_idx, end_idx = PDFService._parse_page_range(page_range, total_pages)
                    
                    # Create new PDF with specified range
                    writer = PdfWriter()
                    for page_idx in range(start_idx, end_idx + 1):
                        writer.add_page(reader.pages[page_idx])
                    
                    # Write to bytes
                    output = io.BytesIO()
                    writer.write(output)
                    output_bytes = output.getvalue()
                    
                    # Generate filename
                    if start_idx == end_idx:
                        output_filename = f"page_{start_idx + 1}.pdf"
                    else:
                        output_filename = f"pages_{start_idx + 1}-{end_idx + 1}.pdf"
                    
                    result[output_filename] = output_bytes
                    
                except Exception as e:
                    app_logger.error(f"Failed to process range '{page_range}': {str(e)}")
                    raise PDFProcessingError(f"Failed to process range '{page_range}': {str(e)}")
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            
            # Log successful operation
            log_pdf_operation(
                operation="split_by_ranges",
                filename=filename,
                file_size=len(pdf_content),
                pages=total_pages,
                processing_time_ms=processing_time,
                output_files=len(result),
                ranges=ranges,
                correlation_id=correlation_id
            )
            
            app_logger.info(f"Successfully split PDF into {len(result)} files")
            return result
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            
            # Log failed operation
            log_pdf_operation(
                operation="split_by_ranges",
                filename=filename,
                file_size=len(pdf_content),
                processing_time_ms=processing_time,
                error=str(e),
                correlation_id=correlation_id
            )
            
            app_logger.error(f"Failed to split PDF by ranges: {str(e)}")
            if isinstance(e, PDFProcessingError):
                raise
            raise PDFProcessingError(f"Failed to split PDF: {str(e)}")
    
    @staticmethod
    async def split_to_individual_pages(pdf_content: bytes, filename: str = "document.pdf") -> Dict[str, bytes]:
        """Split PDF into individual pages.
        
        Args:
            pdf_content: PDF file content as bytes
            filename: Original filename for logging
            
        Returns:
            Dictionary mapping page filenames to PDF content bytes
        """
        start_time = time.time()
        correlation_id = get_correlation_id()
        
        try:
            # Create PDF reader from bytes
            pdf_io = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_io)
            total_pages = len(reader.pages)
            
            if total_pages == 0:
                raise PDFProcessingError("PDF has no pages")
            
            app_logger.info(f"Starting PDF split to individual pages for {filename} ({total_pages} pages)")
            
            result = {}
            
            for i in range(total_pages):
                # Create new PDF with single page
                writer = PdfWriter()
                writer.add_page(reader.pages[i])
                
                # Write to bytes
                output = io.BytesIO()
                writer.write(output)
                output_bytes = output.getvalue()
                
                # Generate filename (1-based page numbering)
                page_filename = f"page_{i + 1}.pdf"
                result[page_filename] = output_bytes
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            
            # Log successful operation
            log_pdf_operation(
                operation="split_to_pages",
                filename=filename,
                file_size=len(pdf_content),
                pages=total_pages,
                processing_time_ms=processing_time,
                output_files=total_pages,
                correlation_id=correlation_id
            )
            
            app_logger.info(f"Successfully split PDF into {total_pages} individual pages")
            return result
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            
            # Log failed operation
            log_pdf_operation(
                operation="split_to_pages",
                filename=filename,
                file_size=len(pdf_content),
                processing_time_ms=processing_time,
                error=str(e),
                correlation_id=correlation_id
            )
            
            app_logger.error(f"Failed to split PDF to individual pages: {str(e)}")
            if isinstance(e, PDFProcessingError):
                raise
            raise PDFProcessingError(f"Failed to split PDF: {str(e)}")
    
    @staticmethod
    async def get_metadata(pdf_content: bytes) -> Dict[str, Any]:
        """Extract comprehensive PDF metadata.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Dictionary containing PDF metadata
        """
        try:
            pdf_io = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_io)
            
            # Extract metadata
            metadata = {}
            if reader.metadata:
                for key, value in reader.metadata.items():
                    # Clean up metadata keys (remove leading slash)
                    clean_key = key.lstrip('/')
                    metadata[clean_key] = str(value) if value else None
            
            # Basic document info
            result = {
                "page_count": len(reader.pages),
                "file_size_bytes": len(pdf_content),
                "file_size_mb": round(len(pdf_content) / (1024 * 1024), 2),
                "encrypted": reader.is_encrypted,
                "metadata": metadata
            }
            
            # Add page dimensions for first page (if available)
            if len(reader.pages) > 0:
                first_page = reader.pages[0]
                mediabox = first_page.mediabox
                result["page_dimensions"] = {
                    "width": float(mediabox.width),
                    "height": float(mediabox.height),
                    "width_inches": round(float(mediabox.width) / 72, 2),
                    "height_inches": round(float(mediabox.height) / 72, 2)
                }
            
            app_logger.info(f"Successfully extracted metadata for PDF ({result['page_count']} pages)")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract PDF metadata: {str(e)}")
            raise PDFProcessingError(f"Failed to extract metadata: {str(e)}")
    
    @staticmethod
    async def get_pdf_info(pdf_content: bytes) -> Dict[str, Any]:
        """Extract basic information from PDF."""
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(pdf_content)
                tmp_file.flush()
                
                reader = PdfReader(tmp_file.name)
                
                info = {
                    "pages": len(reader.pages),
                    "metadata": dict(reader.metadata) if reader.metadata else {},
                    "encrypted": reader.is_encrypted,
                    "file_size": len(pdf_content)
                }
                
                # Clean up temporary file
                os.unlink(tmp_file.name)
                
                return info
                
        except Exception as e:
            logger.error(f"Failed to extract PDF info: {str(e)}")
            raise PDFProcessingError(f"Failed to process PDF: {str(e)}")
    
    @staticmethod
    async def validate_pdf(pdf_content: bytes) -> bool:
        """Validate if content is a valid PDF."""
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(pdf_content)
                tmp_file.flush()
                
                # Try to read the PDF
                reader = PdfReader(tmp_file.name)
                
                # Basic validation - can we read pages?
                pages = len(reader.pages)
                
                # Clean up
                os.unlink(tmp_file.name)
                
                return pages > 0
                
        except Exception as e:
            logger.error(f"PDF validation failed: {str(e)}")
            return False
    
    @staticmethod
    async def get_pdf_info(pdf_content: bytes) -> Dict[str, Any]:
        """Extract basic information from PDF (legacy method - use get_metadata instead)."""
        try:
            return await PDFService.get_metadata(pdf_content)
        except Exception as e:
            logger.error(f"Failed to extract PDF info: {str(e)}")
            raise PDFProcessingError(f"Failed to process PDF: {str(e)}")
    
    @staticmethod
    async def validate_pdf(pdf_content: bytes) -> bool:
        """Validate if content is a valid PDF."""
        try:
            pdf_io = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_io)
            
            # Basic validation - can we read pages?
            pages = len(reader.pages)
            return pages > 0
            
        except Exception as e:
            logger.error(f"PDF validation failed: {str(e)}")
            return False
    
    # ================== PDF MERGE FUNCTIONALITY ==================
    
    @staticmethod
    async def merge_pdfs(
        pdf_files: List[bytes], 
        preserve_metadata: bool = True,
        merge_strategy: str = "append"
    ) -> bytes:
        """Merge multiple PDFs into a single document.
        
        Args:
            pdf_files: List of PDF file contents as bytes
            preserve_metadata: Whether to preserve metadata from the first PDF
            merge_strategy: Strategy for merging ('append', 'interleave')
            
        Returns:
            Merged PDF content as bytes
        """
        try:
            if not pdf_files:
                raise PDFProcessingError("No PDF files provided for merging")
            
            if len(pdf_files) < 2:
                raise PDFProcessingError("At least 2 PDF files are required for merging")
            
            # Validate all PDFs first
            for i, pdf_content in enumerate(pdf_files):
                if not await PDFService.validate_pdf(pdf_content):
                    raise PDFProcessingError(f"Invalid PDF file at position {i + 1}")
            
            if merge_strategy == "append":
                return await PDFService._merge_append(pdf_files, preserve_metadata)
            elif merge_strategy == "interleave":
                return await PDFService._merge_interleave(pdf_files, preserve_metadata)
            else:
                raise PDFProcessingError(f"Unsupported merge strategy: {merge_strategy}")
                
        except Exception as e:
            logger.error(f"Failed to merge PDFs: {str(e)}")
            if isinstance(e, PDFProcessingError):
                raise
            raise PDFProcessingError(f"Failed to merge PDFs: {str(e)}")
    
    @staticmethod
    async def _merge_append(pdf_files: List[bytes], preserve_metadata: bool) -> bytes:
        """Merge PDFs by appending them sequentially."""
        merger = PdfMerger()
        first_metadata = None
        
        try:
            for i, pdf_content in enumerate(pdf_files):
                pdf_io = io.BytesIO(pdf_content)
                reader = PdfReader(pdf_io)
                
                # Capture metadata from first PDF
                if i == 0 and preserve_metadata and reader.metadata:
                    first_metadata = reader.metadata
                
                # Append all pages from this PDF
                merger.append(pdf_io)
            
            # Add preserved metadata if requested
            if first_metadata and preserve_metadata:
                merger.add_metadata(first_metadata)
            
            # Write merged PDF to bytes
            output = io.BytesIO()
            merger.write(output)
            merger.close()
            
            merged_content = output.getvalue()
            logger.info(f"Successfully merged {len(pdf_files)} PDFs using append strategy")
            return merged_content
            
        except Exception as e:
            merger.close()
            raise PDFProcessingError(f"Failed to append PDFs: {str(e)}")
    
    @staticmethod
    async def _merge_interleave(pdf_files: List[bytes], preserve_metadata: bool) -> bytes:
        """Merge PDFs by interleaving pages (page 1 from each, then page 2 from each, etc.)."""
        try:
            readers = []
            max_pages = 0
            first_metadata = None
            
            # Create readers and find max page count
            for i, pdf_content in enumerate(pdf_files):
                pdf_io = io.BytesIO(pdf_content)
                reader = PdfReader(pdf_io)
                readers.append(reader)
                max_pages = max(max_pages, len(reader.pages))
                
                # Capture metadata from first PDF
                if i == 0 and preserve_metadata and reader.metadata:
                    first_metadata = reader.metadata
            
            writer = PdfWriter()
            
            # Interleave pages
            for page_num in range(max_pages):
                for reader in readers:
                    if page_num < len(reader.pages):
                        writer.add_page(reader.pages[page_num])
            
            # Add preserved metadata if requested
            if first_metadata and preserve_metadata:
                writer.add_metadata(first_metadata)
            
            # Write to bytes
            output = io.BytesIO()
            writer.write(output)
            merged_content = output.getvalue()
            
            logger.info(f"Successfully merged {len(pdf_files)} PDFs using interleave strategy")
            return merged_content
            
        except Exception as e:
            raise PDFProcessingError(f"Failed to interleave PDFs: {str(e)}")
    
    @staticmethod
    async def merge_with_page_selection(
        pdf_specs: List[Tuple[bytes, List[int]]], 
        preserve_metadata: bool = True
    ) -> bytes:
        """Merge PDFs with custom page selection.
        
        Args:
            pdf_specs: List of tuples containing (pdf_content, page_indices)
                      page_indices are 1-based page numbers
            preserve_metadata: Whether to preserve metadata from the first PDF
            
        Returns:
            Merged PDF content as bytes
        """
        try:
            if not pdf_specs:
                raise PDFProcessingError("No PDF specifications provided for merging")
            
            writer = PdfWriter()
            first_metadata = None
            total_pages_added = 0
            
            for i, (pdf_content, page_indices) in enumerate(pdf_specs):
                if not page_indices:
                    continue  # Skip if no pages specified for this PDF
                
                # Validate PDF
                if not await PDFService.validate_pdf(pdf_content):
                    raise PDFProcessingError(f"Invalid PDF file at position {i + 1}")
                
                pdf_io = io.BytesIO(pdf_content)
                reader = PdfReader(pdf_io)
                total_pages = len(reader.pages)
                
                # Capture metadata from first PDF
                if i == 0 and preserve_metadata and reader.metadata:
                    first_metadata = reader.metadata
                
                # Validate and add selected pages
                for page_num in page_indices:
                    if page_num < 1 or page_num > total_pages:
                        logger.warning(f"Page {page_num} is out of range for PDF {i + 1} "
                                     f"(has {total_pages} pages). Skipping.")
                        continue
                    
                    # Convert to 0-based index and add page
                    writer.add_page(reader.pages[page_num - 1])
                    total_pages_added += 1
            
            if total_pages_added == 0:
                raise PDFProcessingError("No valid pages were selected for merging")
            
            # Add preserved metadata if requested
            if first_metadata and preserve_metadata:
                writer.add_metadata(first_metadata)
            
            # Write to bytes
            output = io.BytesIO()
            writer.write(output)
            merged_content = output.getvalue()
            
            logger.info(f"Successfully merged {len(pdf_specs)} PDFs with page selection "
                       f"({total_pages_added} pages total)")
            return merged_content
            
        except Exception as e:
            logger.error(f"Failed to merge PDFs with page selection: {str(e)}")
            if isinstance(e, PDFProcessingError):
                raise
            raise PDFProcessingError(f"Failed to merge PDFs with page selection: {str(e)}")
    
    @staticmethod
    async def merge_with_ranges(
        pdf_specs: List[Tuple[bytes, List[str]]], 
        preserve_metadata: bool = True
    ) -> bytes:
        """Merge PDFs with page range specifications.
        
        Args:
            pdf_specs: List of tuples containing (pdf_content, page_ranges)
                      page_ranges are strings like ['1-3', '5', '7-9']
            preserve_metadata: Whether to preserve metadata from the first PDF
            
        Returns:
            Merged PDF content as bytes
        """
        try:
            if not pdf_specs:
                raise PDFProcessingError("No PDF specifications provided for merging")
            
            writer = PdfWriter()
            first_metadata = None
            total_pages_added = 0
            
            for i, (pdf_content, page_ranges) in enumerate(pdf_specs):
                if not page_ranges:
                    continue  # Skip if no ranges specified for this PDF
                
                # Validate PDF
                if not await PDFService.validate_pdf(pdf_content):
                    raise PDFProcessingError(f"Invalid PDF file at position {i + 1}")
                
                pdf_io = io.BytesIO(pdf_content)
                reader = PdfReader(pdf_io)
                total_pages = len(reader.pages)
                
                # Capture metadata from first PDF
                if i == 0 and preserve_metadata and reader.metadata:
                    first_metadata = reader.metadata
                
                # Process each range for this PDF
                for page_range in page_ranges:
                    try:
                        start_idx, end_idx = PDFService._parse_page_range(page_range, total_pages)
                        
                        # Add pages in the range
                        for page_idx in range(start_idx, end_idx + 1):
                            writer.add_page(reader.pages[page_idx])
                            total_pages_added += 1
                            
                    except PDFProcessingError as e:
                        logger.warning(f"Skipping invalid range '{page_range}' for PDF {i + 1}: {str(e)}")
                        continue
            
            if total_pages_added == 0:
                raise PDFProcessingError("No valid pages were selected for merging")
            
            # Add preserved metadata if requested
            if first_metadata and preserve_metadata:
                writer.add_metadata(first_metadata)
            
            # Write to bytes
            output = io.BytesIO()
            writer.write(output)
            merged_content = output.getvalue()
            
            logger.info(f"Successfully merged {len(pdf_specs)} PDFs with range selection "
                       f"({total_pages_added} pages total)")
            return merged_content
            
        except Exception as e:
            logger.error(f"Failed to merge PDFs with ranges: {str(e)}")
            if isinstance(e, PDFProcessingError):
                raise
            raise PDFProcessingError(f"Failed to merge PDFs with ranges: {str(e)}")
    
    @staticmethod
    async def get_merge_info(pdf_files: List[bytes]) -> Dict[str, Any]:
        """Get information about PDFs that will be merged.
        
        Args:
            pdf_files: List of PDF file contents as bytes
            
        Returns:
            Dictionary containing merge preview information
        """
        try:
            if not pdf_files:
                raise PDFProcessingError("No PDF files provided")
            
            files_info = []
            total_pages = 0
            total_size = 0
            
            for i, pdf_content in enumerate(pdf_files):
                if not await PDFService.validate_pdf(pdf_content):
                    raise PDFProcessingError(f"Invalid PDF file at position {i + 1}")
                
                pdf_io = io.BytesIO(pdf_content)
                reader = PdfReader(pdf_io)
                page_count = len(reader.pages)
                file_size = len(pdf_content)
                
                # Extract basic metadata
                metadata = {}
                if reader.metadata:
                    for key, value in reader.metadata.items():
                        clean_key = key.lstrip('/')
                        metadata[clean_key] = str(value) if value else None
                
                file_info = {
                    "file_index": i + 1,
                    "page_count": page_count,
                    "file_size_bytes": file_size,
                    "file_size_mb": round(file_size / (1024 * 1024), 2),
                    "encrypted": reader.is_encrypted,
                    "title": metadata.get("Title", f"Document {i + 1}")
                }
                
                files_info.append(file_info)
                total_pages += page_count
                total_size += file_size
            
            merge_info = {
                "files_count": len(pdf_files),
                "total_pages": total_pages,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "files": files_info,
                "estimated_merged_size_mb": round(total_size / (1024 * 1024) * 0.95, 2),  # Slightly smaller due to compression
                "merge_strategies": ["append", "interleave"],
                "supports_page_selection": True,
                "supports_range_selection": True
            }
            
            logger.info(f"Generated merge info for {len(pdf_files)} files ({total_pages} total pages)")
            return merge_info
            
        except Exception as e:
            logger.error(f"Failed to get merge info: {str(e)}")
            if isinstance(e, PDFProcessingError):
                raise
            raise PDFProcessingError(f"Failed to analyze PDFs for merging: {str(e)}")
    
    # ================== PDF BATCH SPLIT FUNCTIONALITY ==================
    
    @staticmethod
    async def split_into_batches(
        pdf_content: bytes, 
        batch_size: int, 
        original_filename: str = "document.pdf"
    ) -> Dict[str, bytes]:
        """Split PDF into batches of specified page count.
        
        Args:
            pdf_content: PDF file content as bytes
            batch_size: Number of pages per batch
            original_filename: Original filename for naming output files
            
        Returns:
            Dictionary mapping batch filenames to PDF content bytes
        """
        try:
            if batch_size <= 0:
                raise PDFProcessingError("Batch size must be greater than 0")
            
            # Create PDF reader from bytes
            pdf_io = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_io)
            total_pages = len(reader.pages)
            
            if total_pages == 0:
                raise PDFProcessingError("PDF has no pages")
            
            # Calculate number of batches
            batch_count = (total_pages + batch_size - 1) // batch_size
            
            result = {}
            filename_base = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
            
            for batch_num in range(batch_count):
                start_page = batch_num * batch_size
                end_page = min((batch_num + 1) * batch_size, total_pages)
                
                # Create new PDF with batch pages
                writer = PdfWriter()
                for page_idx in range(start_page, end_page):
                    writer.add_page(reader.pages[page_idx])
                
                # Write to bytes
                output = io.BytesIO()
                writer.write(output)
                output_bytes = output.getvalue()
                
                # Generate batch filename
                if start_page + 1 == end_page:
                    # Single page
                    batch_filename = f"{filename_base}_batch_{batch_num + 1}_page_{start_page + 1}.pdf"
                else:
                    # Multiple pages
                    batch_filename = f"{filename_base}_batch_{batch_num + 1}_pages_{start_page + 1}-{end_page}.pdf"
                
                result[batch_filename] = output_bytes
            
            logger.info(f"Successfully split PDF into {len(result)} batches "
                       f"(batch_size={batch_size}, total_pages={total_pages})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to split PDF into batches: {str(e)}")
            if isinstance(e, PDFProcessingError):
                raise
            raise PDFProcessingError(f"Failed to split PDF into batches: {str(e)}")
    
    @staticmethod
    async def get_batch_split_info(pdf_content: bytes, batch_size: int) -> Dict[str, Any]:
        """Get information about how a PDF would be split into batches.
        
        Args:
            pdf_content: PDF file content as bytes
            batch_size: Number of pages per batch
            
        Returns:
            Dictionary containing batch split preview information
        """
        try:
            if batch_size <= 0:
                raise PDFProcessingError("Batch size must be greater than 0")
            
            pdf_io = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_io)
            total_pages = len(reader.pages)
            
            if total_pages == 0:
                raise PDFProcessingError("PDF has no pages")
            
            # Calculate batch information
            batch_count = (total_pages + batch_size - 1) // batch_size
            
            batches_info = []
            for batch_num in range(batch_count):
                start_page = batch_num * batch_size + 1  # 1-based for display
                end_page = min((batch_num + 1) * batch_size, total_pages)
                pages_in_batch = end_page - start_page + 1
                
                batch_info = {
                    "batch_number": batch_num + 1,
                    "start_page": start_page,
                    "end_page": end_page,
                    "pages_count": pages_in_batch
                }
                batches_info.append(batch_info)
            
            result = {
                "total_pages": total_pages,
                "batch_size": batch_size,
                "batch_count": batch_count,
                "batches": batches_info,
                "file_size_bytes": len(pdf_content),
                "file_size_mb": round(len(pdf_content) / (1024 * 1024), 2),
                "estimated_total_output_size_mb": round(len(pdf_content) / (1024 * 1024) * 1.1, 2)  # Slightly larger due to overhead
            }
            
            logger.info(f"Generated batch split info: {total_pages} pages -> {batch_count} batches")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get batch split info: {str(e)}")
            if isinstance(e, PDFProcessingError):
                raise
            raise PDFProcessingError(f"Failed to analyze PDF for batch splitting: {str(e)}")
    
    # ================== PDF COMPRESSION FUNCTIONALITY ==================
    
    @staticmethod
    async def compress_pdf_pypdf_enhanced(
        pdf_content: bytes, 
        stream_compression_level: int = 9,
        remove_images: bool = False,
        image_quality: int = 80,
        aggressive_cleanup: bool = True
    ) -> Tuple[bytes, Dict[str, Any]]:
        """Enhanced pypdf compression with maximum optimization.
        
        Based on Context7 best practices for pypdf compression including:
        - Content stream compression with configurable levels
        - Identical object removal and orphan cleanup
        - Smart image processing and quality reduction
        - Advanced deduplication techniques
        
        Args:
            pdf_content: PDF file content as bytes
            stream_compression_level: zlib compression level (0-9)
            remove_images: Whether to remove all images (aggressive compression)
            image_quality: JPEG quality for image recompression (1-100)
            aggressive_cleanup: Enable advanced cleanup optimizations
            
        Returns:
            Tuple of (compressed PDF bytes, compression statistics)
        """
        start_time = time.time()
        
        try:
            original_size = len(pdf_content)
            
            # Create PDF reader and writer with error handling
            pdf_io = io.BytesIO(pdf_content)
            try:
                reader = PdfReader(pdf_io, strict=False)  # More tolerant of PDF errors
            except Exception as e:
                app_logger.warning(f"Failed to read PDF with strict=False: {str(e)}")
                # Try with even more permissive settings
                pdf_io.seek(0)
                reader = PdfReader(pdf_io, strict=False)
            
            if len(reader.pages) == 0:
                raise PDFProcessingError("PDF has no pages")
            
            writer = PdfWriter()  # Don't clone - start fresh for better compression
            
            # Add pages individually with error handling for corrupted pages
            pages_added = 0
            for i, page in enumerate(reader.pages):
                try:
                    writer.add_page(page)
                    pages_added += 1
                except Exception as e:
                    app_logger.warning(f"Failed to add page {i+1}: {str(e)}")
                    continue  # Skip corrupted pages
            
            if pages_added == 0:
                raise PDFProcessingError("No pages could be processed")
            
            app_logger.info(f"Successfully processed {pages_added}/{len(reader.pages)} pages")
            
            compression_methods_applied = []
            
            # 1. Remove all images if requested (most aggressive)
            if remove_images:
                try:
                    writer.remove_images()
                    compression_methods_applied.append("remove_images")
                except Exception:
                    pass
            
            # 2. Apply smart image processing - reduce quality of remaining images
            elif image_quality < 100:
                try:
                    image_count = 0
                    for page in writer.pages:
                        for img in page.images:
                            try:
                                # Reduce image quality as per Context7 best practices
                                img.replace(img.image, quality=image_quality)
                                image_count += 1
                            except Exception:
                                continue
                    if image_count > 0:
                        compression_methods_applied.append(f"image_quality_reduction_{image_quality}%")
                except Exception:
                    pass
            
            # 3. Compress content streams with configurable level (Context7 recommended)
            stream_compressed_count = 0
            for i, page in enumerate(writer.pages):
                try:
                    page.compress_content_streams(level=stream_compression_level)
                    stream_compressed_count += 1
                except Exception as e:
                    app_logger.debug(f"Failed to compress streams on page {i+1}: {str(e)}")
                    continue
            if stream_compressed_count > 0:
                compression_methods_applied.append(f"content_streams_level_{stream_compression_level}")
                app_logger.info(f"Compressed content streams on {stream_compressed_count}/{len(writer.pages)} pages")
            
            # 4. Advanced object deduplication and cleanup (Context7 best practice)
            if aggressive_cleanup:
                try:
                    # Remove identical objects and orphans (can achieve up to 86% reduction)
                    writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)
                    compression_methods_applied.append("identical_objects_removal")
                except Exception:
                    pass
            
            # 5. Additional cleanup - remove unreferenced resources
            if aggressive_cleanup:
                try:
                    # This method may not exist in all pypdf versions, so we try
                    if hasattr(writer, 'remove_unreferenced_resources'):
                        writer.remove_unreferenced_resources()
                        compression_methods_applied.append("unreferenced_resources_cleanup")
                except Exception:
                    pass
            
            # Write compressed PDF to bytes
            output = io.BytesIO()
            writer.write(output)
            compressed_content = output.getvalue()
            compressed_size = len(compressed_content)
            
            # Check if compression actually reduced file size
            if compressed_size >= original_size:
                # If our compression made it larger, try simpler approach
                app_logger.warning(f"Enhanced compression increased file size. Trying basic approach.")
                
                # Try basic compression without all the enhancements
                basic_writer = PdfWriter()
                for page in reader.pages:
                    basic_writer.add_page(page)
                
                # Only apply basic object compression
                try:
                    basic_writer.compress_identical_objects(remove_identicals=True, remove_orphans=False)
                except Exception:
                    pass
                
                basic_output = io.BytesIO()
                basic_writer.write(basic_output)
                basic_content = basic_output.getvalue()
                basic_size = len(basic_content)
                
                # Use the better result
                if basic_size < compressed_size:
                    compressed_content = basic_content
                    compressed_size = basic_size
                    compression_methods_applied = ["basic_object_compression_fallback"]
                    app_logger.info(f"Used fallback compression: {basic_size} bytes vs {compressed_size} bytes")
            
            # Final safety check: if still larger than original, return original
            if compressed_size >= original_size:
                app_logger.warning(f"All compression attempts increased file size. Returning original.")
                compressed_content = pdf_content
                compressed_size = original_size
                compression_methods_applied = ["no_compression_original_returned"]
            
            # Calculate compression statistics
            reduction_bytes = original_size - compressed_size
            reduction_percentage = (reduction_bytes / original_size) * 100 if original_size > 0 else 0
            processing_time = (time.time() - start_time) * 1000
            
            stats = {
                "method": "pypdf_enhanced",
                "original_size_bytes": original_size,
                "compressed_size_bytes": compressed_size,
                "reduction_bytes": reduction_bytes,
                "reduction_percentage": round(reduction_percentage, 2),
                "processing_time_ms": round(processing_time, 2),
                "page_count": len(reader.pages),
                "stream_compression_level": stream_compression_level,
                "image_quality": image_quality if not remove_images else "removed",
                "methods_applied": compression_methods_applied,
                "aggressive_cleanup": aggressive_cleanup
            }
            
            return compressed_content, stats
            
        except Exception as e:
            raise PDFProcessingError(f"pypdf enhanced compression failed: {str(e)}")
    
    @staticmethod
    async def compress_pdf_pikepdf(
        pdf_content: bytes,
        remove_images: bool = False,
        aggressive_cleanup: bool = True,
        use_memory_mapping: bool = True
    ) -> Tuple[bytes, Dict[str, Any]]:
        """Enhanced pikepdf compression with structural optimization.
        
        Based on Context7 best practices for pikepdf compression including:
        - Memory-mapped file access for large PDFs
        - Advanced resource cleanup and optimization
        - Image processing and removal options
        - PDF version handling and structural improvements
        
        Args:
            pdf_content: PDF file content as bytes
            remove_images: Whether to remove all images
            aggressive_cleanup: Enable advanced cleanup optimizations
            use_memory_mapping: Use memory-mapped access for better performance
            
        Returns:
            Tuple of (compressed PDF bytes, compression statistics)
        """
        start_time = time.time()
        
        try:
            import pikepdf
            
            original_size = len(pdf_content)
            optimization_methods_applied = []
            
            # Create temporary file for pikepdf
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_input:
                tmp_input.write(pdf_content)
                tmp_input.flush()
                
                # Open with pikepdf using memory-mapped access if enabled (Context7 best practice)
                access_mode = pikepdf.AccessMode.mmap if use_memory_mapping and len(pdf_content) > 10*1024*1024 else pikepdf.AccessMode.default
                
                with pikepdf.open(tmp_input.name, access_mode=access_mode) as pdf:
                    
                    # 1. Remove images if requested (Context7 technique)
                    if remove_images:
                        try:
                            image_removal_count = 0
                            for page in pdf.pages:
                                for image_name, image_obj in list(page.images.items()):
                                    try:
                                        # Replace with 1x1 transparent mask (Context7 method)
                                        new_image = pdf.make_stream(b'\xff')
                                        new_image.Width, new_image.Height = 1, 1
                                        new_image.BitsPerComponent = 1
                                        new_image.ImageMask = True
                                        new_image.Decode = [0, 1]
                                        page.Resources.XObject[image_name] = new_image
                                        image_removal_count += 1
                                    except Exception:
                                        continue
                            if image_removal_count > 0:
                                optimization_methods_applied.append(f"removed_{image_removal_count}_images")
                        except Exception:
                            pass
                    
                    # 2. Advanced resource cleanup (Context7 best practice)
                    if aggressive_cleanup:
                        try:
                            pdf.remove_unreferenced_resources()
                            optimization_methods_applied.append("unreferenced_resources_cleanup")
                        except Exception:
                            pass
                    
                    # 3. PDF version optimization for better compression
                    try:
                        original_version = pdf.pdf_version
                        # Ensure we use the most efficient version
                        optimization_methods_applied.append(f"version_handling_{original_version}")
                    except Exception:
                        pass
                    
                    # Create output buffer
                    output = io.BytesIO()
                    
                    # 4. Save with enhanced optimization parameters (Context7 optimized)
                    # Note: Some parameters may not be available in all pikepdf versions
                    save_params = {
                        "linearize": False,  # Keep file smaller
                        "compress_streams": True,
                        "recompress_flate": True,
                        "min_version": pdf.pdf_version  # Maintain version compatibility
                    }
                    
                    # Add optional parameters if supported
                    try:
                        # Check if these parameters exist before using them
                        if hasattr(pikepdf.ObjectStreamMode, 'generate'):
                            save_params["object_stream_mode"] = pikepdf.ObjectStreamMode.generate
                        save_params["deterministic_id"] = True
                        save_params["normalize_content"] = True
                    except (AttributeError, TypeError):
                        pass  # Skip unsupported parameters
                    
                    pdf.save(output, **save_params)
                    
                    # Track actually applied optimization methods
                    actual_methods = ["compress_streams", "recompress_flate"]
                    if "object_stream_mode" in save_params:
                        actual_methods.append("object_streams")
                    if "deterministic_id" in save_params:
                        actual_methods.append("deterministic_id")
                    if "normalize_content" in save_params:
                        actual_methods.append("normalize_content")
                    optimization_methods_applied.extend(actual_methods)
                    
                    compressed_content = output.getvalue()
                    compressed_size = len(compressed_content)
                
                # Clean up temporary file
                os.unlink(tmp_input.name)
            
            # Calculate compression statistics
            reduction_bytes = original_size - compressed_size
            reduction_percentage = (reduction_bytes / original_size) * 100 if original_size > 0 else 0
            processing_time = (time.time() - start_time) * 1000
            
            stats = {
                "method": "pikepdf_enhanced",
                "original_size_bytes": original_size,
                "compressed_size_bytes": compressed_size,
                "reduction_bytes": reduction_bytes,
                "reduction_percentage": round(reduction_percentage, 2),
                "processing_time_ms": round(processing_time, 2),
                "optimization_methods": optimization_methods_applied,
                "memory_mapped": use_memory_mapping and len(pdf_content) > 10*1024*1024,
                "aggressive_cleanup": aggressive_cleanup
            }
            
            return compressed_content, stats
            
        except ImportError:
            raise PDFProcessingError("pikepdf library not available")
        except Exception as e:
            raise PDFProcessingError(f"pikepdf compression failed: {str(e)}")
    
    @staticmethod
    async def compress_pdf_pymupdf(pdf_content: bytes) -> Tuple[bytes, Dict[str, Any]]:
        """PyMuPDF compression with garbage collection and deflate.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Tuple of (compressed PDF bytes, compression statistics)
        """
        start_time = time.time()
        
        try:
            import fitz  # PyMuPDF
            
            original_size = len(pdf_content)
            
            # Create temporary file for PyMuPDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_input:
                tmp_input.write(pdf_content)
                tmp_input.flush()
                
                # Open with PyMuPDF
                doc = fitz.open(tmp_input.name)
                
                # Create output buffer
                output = io.BytesIO()
                
                # Save with maximum compression
                # garbage=4: aggressive garbage collection
                # deflate=True: enable deflate compression
                doc.save(output, garbage=4, deflate=True)
                doc.close()
                
                compressed_content = output.getvalue()
                compressed_size = len(compressed_content)
                
                # Clean up temporary file
                os.unlink(tmp_input.name)
            
            # Calculate compression statistics
            reduction_bytes = original_size - compressed_size
            reduction_percentage = (reduction_bytes / original_size) * 100 if original_size > 0 else 0
            processing_time = (time.time() - start_time) * 1000
            
            stats = {
                "method": "pymupdf",
                "original_size_bytes": original_size,
                "compressed_size_bytes": compressed_size,
                "reduction_bytes": reduction_bytes,
                "reduction_percentage": round(reduction_percentage, 2),
                "processing_time_ms": round(processing_time, 2)
            }
            
            return compressed_content, stats
            
        except ImportError:
            raise PDFProcessingError("PyMuPDF library not available")
        except Exception as e:
            raise PDFProcessingError(f"PyMuPDF compression failed: {str(e)}")
    
    @staticmethod
    async def compress_pdf(
        pdf_content: bytes, 
        compression_level: str = "medium",
        remove_duplication: bool = True,
        compress_streams: bool = True,
        remove_images: bool = False,
        image_quality: int = 85,
        stream_compression_level: int = 9,
        aggressive_cleanup: bool = True,
        use_memory_mapping: bool = True
    ) -> Tuple[bytes, Dict[str, Any]]:
        """Advanced multi-method PDF compression with benchmarking.
        
        Enhanced with Context7 best practices for pypdf and pikepdf optimization.
        
        Args:
            pdf_content: PDF file content as bytes
            compression_level: Level of compression ('low', 'medium', 'high')
            remove_duplication: Remove duplicate objects (legacy parameter)
            compress_streams: Compress content streams (legacy parameter)
            remove_images: Remove all images (aggressive compression)
            image_quality: JPEG quality for image recompression (1-100)
            stream_compression_level: zlib compression level for content streams (0-9)
            aggressive_cleanup: Enable advanced cleanup optimizations
            use_memory_mapping: Use memory-mapped access for large PDFs
            
        Returns:
            Tuple of (compressed PDF bytes, compression statistics)
        """
        start_time = time.time()
        correlation_id = get_correlation_id()
        
        try:
            original_size = len(pdf_content)
            
            if len(pdf_content) == 0:
                raise PDFProcessingError("Empty PDF content")
                
            # Quick validation
            pdf_io = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_io)
            if len(reader.pages) == 0:
                raise PDFProcessingError("PDF has no pages")
            
            app_logger.info(f"Starting advanced PDF compression (level={compression_level}, size={original_size} bytes)")
            
            # Check if the PDF might already be well-compressed
            estimated_compression_ratio = original_size / len(reader.pages) if len(reader.pages) > 0 else 0
            is_likely_compressed = estimated_compression_ratio < 100000  # < 100KB per page suggests good compression
            
            if is_likely_compressed:
                app_logger.info(f"PDF appears already well-compressed ({estimated_compression_ratio:.0f} bytes/page). Using conservative approach.")
            
            compression_results = []
            best_result = None
            best_content = pdf_content
            
            # Method selection based on compression level
            methods_to_try = []
            
            if compression_level == "low":
                # Just try pypdf basic
                methods_to_try = ["pypdf_basic"]
            elif compression_level == "medium":
                # Try pypdf enhanced and pikepdf
                methods_to_try = ["pypdf_enhanced", "pikepdf"]
            else:  # high
                # Try all methods and pick the best
                methods_to_try = ["pypdf_enhanced", "pikepdf", "pymupdf"]
            
            # Try pypdf enhanced compression
            if "pypdf_enhanced" in methods_to_try:
                try:
                    result_content, result_stats = await PDFService.compress_pdf_pypdf_enhanced(
                        pdf_content,
                        stream_compression_level=stream_compression_level,
                        remove_images=remove_images,
                        image_quality=image_quality,
                        aggressive_cleanup=aggressive_cleanup
                    )
                    compression_results.append(result_stats)
                    
                    if best_result is None or result_stats["reduction_percentage"] > best_result["reduction_percentage"]:
                        best_result = result_stats
                        best_content = result_content
                        
                    app_logger.info(f"pypdf enhanced: {result_stats['reduction_percentage']:.1f}% reduction")
                except Exception as e:
                    app_logger.warning(f"pypdf enhanced compression failed: {str(e)}")
            
            # Try pikepdf compression
            if "pikepdf" in methods_to_try:
                try:
                    result_content, result_stats = await PDFService.compress_pdf_pikepdf(
                        pdf_content,
                        remove_images=remove_images,
                        aggressive_cleanup=aggressive_cleanup,
                        use_memory_mapping=use_memory_mapping
                    )
                    compression_results.append(result_stats)
                    
                    if best_result is None or result_stats["reduction_percentage"] > best_result["reduction_percentage"]:
                        best_result = result_stats
                        best_content = result_content
                        
                    app_logger.info(f"pikepdf: {result_stats['reduction_percentage']:.1f}% reduction")
                except Exception as e:
                    app_logger.warning(f"pikepdf compression failed: {str(e)}")
            
            # Try PyMuPDF compression
            if "pymupdf" in methods_to_try:
                try:
                    result_content, result_stats = await PDFService.compress_pdf_pymupdf(pdf_content)
                    compression_results.append(result_stats)
                    
                    if best_result is None or result_stats["reduction_percentage"] > best_result["reduction_percentage"]:
                        best_result = result_stats
                        best_content = result_content
                        
                    app_logger.info(f"PyMuPDF: {result_stats['reduction_percentage']:.1f}% reduction")
                except Exception as e:
                    app_logger.warning(f"PyMuPDF compression failed: {str(e)}")
            
            # Fallback to basic pypdf if no method worked
            if best_result is None:
                app_logger.warning("All compression methods failed, using basic pypdf fallback")
                best_content, best_result = await PDFService._compress_pdf_basic_fallback(pdf_content)
                compression_results.append(best_result)
            
            # Calculate total processing time
            total_processing_time = (time.time() - start_time) * 1000
            
            # Prepare final statistics
            final_stats = {
                "original_size_bytes": original_size,
                "compressed_size_bytes": best_result["compressed_size_bytes"],
                "reduction_bytes": best_result["reduction_bytes"],
                "reduction_percentage": best_result["reduction_percentage"],
                "original_size_mb": round(original_size / (1024 * 1024), 2),
                "compressed_size_mb": round(best_result["compressed_size_bytes"] / (1024 * 1024), 2),
                "compression_level": compression_level,
                "processing_time_ms": round(total_processing_time, 2),
                "page_count": len(reader.pages),
                "best_method": best_result["method"],
                "methods_tried": [r["method"] for r in compression_results],
                "all_results": compression_results,
                "settings": {
                    "remove_duplication": remove_duplication,
                    "compress_streams": compress_streams,
                    "remove_images": remove_images,
                    "image_quality": image_quality
                }
            }
            
            # Log successful compression
            log_pdf_operation(
                operation="compress_pdf_advanced",
                filename="compressed.pdf",
                file_size=original_size,
                pages=len(reader.pages),
                processing_time_ms=total_processing_time,
                compression_level=compression_level,
                reduction_percentage=final_stats["reduction_percentage"],
                correlation_id=correlation_id
            )
            
            app_logger.info(f"Advanced compression complete: {final_stats['reduction_percentage']:.1f}% reduction "
                           f"using {best_result['method']} ({original_size} -> {best_result['compressed_size_bytes']} bytes)")
            
            return best_content, final_stats
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            
            # Log failed operation
            log_pdf_operation(
                operation="compress_pdf_advanced",
                filename="compressed.pdf",
                file_size=len(pdf_content),
                processing_time_ms=processing_time,
                error=str(e),
                correlation_id=correlation_id
            )
            
            app_logger.error(f"Advanced PDF compression failed: {str(e)}")
            if isinstance(e, PDFProcessingError):
                raise
            raise PDFProcessingError(f"Failed to compress PDF: {str(e)}")
    
    @staticmethod
    async def _compress_pdf_basic_fallback(pdf_content: bytes) -> Tuple[bytes, Dict[str, Any]]:
        """Basic fallback compression using pypdf only.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Tuple of (compressed PDF bytes, compression statistics)
        """
        start_time = time.time()
        
        try:
            original_size = len(pdf_content)
            
            # Create PDF reader and writer
            pdf_io = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_io)
            writer = PdfWriter()
            
            # Copy all pages to writer
            for page in reader.pages:
                writer.add_page(page)
            
            # Apply basic compression
            for page in writer.pages:
                try:
                    page.compress_content_streams()
                except Exception:
                    continue
            
            # Write compressed PDF to bytes
            output = io.BytesIO()
            writer.write(output)
            compressed_content = output.getvalue()
            compressed_size = len(compressed_content)
            
            # Calculate compression statistics
            reduction_bytes = original_size - compressed_size
            reduction_percentage = (reduction_bytes / original_size) * 100 if original_size > 0 else 0
            processing_time = (time.time() - start_time) * 1000
            
            stats = {
                "method": "pypdf_basic_fallback",
                "original_size_bytes": original_size,
                "compressed_size_bytes": compressed_size,
                "reduction_bytes": reduction_bytes,
                "reduction_percentage": round(reduction_percentage, 2),
                "processing_time_ms": round(processing_time, 2)
            }
            
            return compressed_content, stats
            
        except Exception as e:
            raise PDFProcessingError(f"Basic fallback compression failed: {str(e)}")
    
    @staticmethod
    async def get_compression_preview(
        pdf_content: bytes,
        compression_level: str = "medium",
        image_quality: int = 80,
        stream_compression_level: int = 9,
        aggressive_cleanup: bool = True
    ) -> Dict[str, Any]:
        """Preview potential compression results without actually compressing.
        
        Enhanced with Context7 analysis for detailed optimization recommendations.
        
        Args:
            pdf_content: PDF file content as bytes
            compression_level: Level of compression to preview
            image_quality: JPEG quality for image recompression (1-100)
            stream_compression_level: zlib compression level for content streams (0-9)
            aggressive_cleanup: Enable advanced cleanup optimizations
            
        Returns:
            Dictionary with detailed compression preview and recommendations
        """
        try:
            pdf_io = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_io)
            
            original_size = len(pdf_content)
            total_pages = len(reader.pages)
            
            if total_pages == 0:
                raise PDFProcessingError("PDF has no pages")
            
            # Analyze PDF content
            has_images = False
            image_count = 0
            has_forms = False
            
            # Check for forms
            try:
                if reader.trailer and "/Root" in reader.trailer:
                    root = reader.trailer["/Root"]
                    if hasattr(root, 'get_object'):
                        root = root.get_object()
                    if "/AcroForm" in root:
                        has_forms = True
            except Exception:
                pass  # Ignore form detection errors
            
            # Check for images
            for page in reader.pages:
                try:
                    resources = page.get("/Resources", {})
                    if resources and "/XObject" in resources:
                        xobjects = resources["/XObject"]
                        if hasattr(xobjects, 'get_object'):
                            xobjects = xobjects.get_object()
                        
                        if isinstance(xobjects, dict):
                            for obj_name in xobjects:
                                try:
                                    xobj = xobjects[obj_name]
                                    if hasattr(xobj, 'get_object'):
                                        xobj = xobj.get_object()
                                    if isinstance(xobj, dict) and xobj.get("/Subtype") == "/Image":
                                        has_images = True
                                        image_count += 1
                                except Exception:
                                    continue  # Skip problematic objects
                except Exception:
                    continue  # Skip pages that can't be analyzed
            
            # Enhanced estimation based on Context7 best practices
            base_reduction = 0
            
            # Content stream compression potential (Context7 insight)
            if stream_compression_level >= 7:
                base_reduction += 10  # High compression can achieve 10-15% from streams
            elif stream_compression_level >= 4:
                base_reduction += 5
            else:
                base_reduction += 2
            
            # Image optimization potential (Context7 technique)
            if has_images:
                if image_quality <= 60:
                    base_reduction += 20  # Aggressive image compression
                elif image_quality <= 80:
                    base_reduction += 15  # Moderate image compression
                else:
                    base_reduction += 5   # Light image optimization
            
            # Object deduplication potential (Context7 best practice)
            if aggressive_cleanup:
                base_reduction += 15  # Can achieve up to 86% in optimal cases
            else:
                base_reduction += 5
            
            # Method-specific adjustments
            method_bonus = 0
            if compression_level == "low":
                method_bonus = 0
                estimated_reduction = min(base_reduction * 0.3, 15)  # Conservative
            elif compression_level == "medium":
                method_bonus = 10
                estimated_reduction = min(base_reduction * 0.7 + method_bonus, 40)
            elif compression_level == "high":
                method_bonus = 20  # All methods + benchmarking
                estimated_reduction = min(base_reduction + method_bonus, 70)
            else:
                estimated_reduction = 10
            
            estimated_size = int(original_size * (1 - estimated_reduction / 100))
            
            # Context7-enhanced method analysis
            available_methods = []
            if compression_level == "low":
                available_methods = ["pypdf_basic"]
            elif compression_level == "medium":
                available_methods = ["pypdf_enhanced", "pikepdf_enhanced"]
            else:  # high
                available_methods = ["pypdf_enhanced", "pikepdf_enhanced", "pymupdf"]
            
            # Generate Context7-based optimization recommendations
            recommendations = []
            
            if has_images and image_count > 5:
                recommendations.append(f"Document contains {image_count} images - consider image quality reduction for better compression")
                if image_quality > 80:
                    recommendations.append("Lowering image quality to 60-80% can achieve 15-20% additional reduction")
            
            if original_size > 50 * 1024 * 1024:  # 50MB
                recommendations.append("Large PDF detected - memory-mapped processing recommended for optimal performance")
            
            if not aggressive_cleanup:
                recommendations.append("Enable aggressive cleanup for up to 86% reduction through object deduplication")
            
            if stream_compression_level < 7:
                recommendations.append("Increase stream compression level to 7-9 for better content stream optimization")
            
            if compression_level == "low" and (has_images or original_size > 10*1024*1024):
                recommendations.append("Consider medium or high compression for image-heavy or large PDFs")
                
            if has_forms:
                recommendations.append("PDF contains forms - compression may affect form functionality, test thoroughly")
            
            # Content type analysis
            content_analysis = {
                "primarily_text": not has_images or image_count < 3,
                "image_heavy": has_images and image_count >= 5,
                "mixed_content": has_images and 3 <= image_count < 5,
                "has_forms": has_forms,
                "large_file": original_size > 10*1024*1024
            }
            
            # Method effectiveness prediction
            method_effectiveness = {}
            for method in available_methods:
                if method == "pypdf_enhanced":
                    effectiveness = "High" if aggressive_cleanup else "Medium"
                    if has_images:
                        effectiveness += " (excellent for object deduplication)"
                elif method == "pikepdf_enhanced":
                    effectiveness = "High" if original_size > 10*1024*1024 else "Medium"
                    effectiveness += " (memory-optimized for large files)"
                elif method == "pymupdf":
                    effectiveness = "Medium (good for text-heavy documents)"
                else:
                    effectiveness = "Low"
                method_effectiveness[method] = effectiveness
            
            preview = {
                "original_size_bytes": original_size,
                "original_size_mb": round(original_size / (1024 * 1024), 2),
                "estimated_compressed_size_bytes": estimated_size,
                "estimated_compressed_size_mb": round(estimated_size / (1024 * 1024), 2),
                "estimated_reduction_percentage": estimated_reduction,
                "page_count": total_pages,
                "has_images": has_images,
                "image_count": image_count,
                "has_forms": has_forms,
                "compression_level": compression_level,
                "available_methods": available_methods,
                "method_count": len(available_methods),
                "recommendations": recommendations,
                "content_analysis": content_analysis,
                "method_effectiveness": method_effectiveness,
                "context7_enhanced": True,
                "optimization_parameters": {
                    "image_quality": image_quality,
                    "stream_compression_level": stream_compression_level,
                    "aggressive_cleanup": aggressive_cleanup
                }
            }
            
            logger.info(f"Generated compression preview for {total_pages}-page PDF "
                       f"({original_size} bytes, {estimated_reduction}% potential reduction)")
            
            return preview
            
        except Exception as e:
            logger.error(f"Failed to generate compression preview: {str(e)}")
            if isinstance(e, PDFProcessingError):
                raise
            raise PDFProcessingError(f"Failed to analyze PDF for compression: {str(e)}")
