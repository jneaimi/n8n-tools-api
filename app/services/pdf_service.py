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
from datetime import datetime

from app.core.errors import PDFProcessingError
from app.core.logging import (
    log_pdf_operation, 
    log_validation_result, 
    log_performance_metric,
    get_correlation_id,
    app_logger
)

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
            
            logger.info(f"Successfully extracted metadata for PDF ({result['page_count']} pages)")
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
