"""
PDF manipulation API routes.

Provides endpoints for PDF split, merge, and metadata operations
designed for n8n workflow automation.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Optional
import logging
import time
import io
import zipfile
import json
import re

from app.services.pdf_service import PDFService
from app.utils.file_utils import validate_pdf_file, get_file_info, save_temp_file, cleanup_temp_file
from app.models.pdf_models import (
    PageRangeRequest, PDFSplitResponse, PDFMetadataResponse,
    MergeOptions, PageSelectionRequest, RangeSelectionRequest, 
    PDFMergeResponse, MergeInfoResponse, BatchSplitOptions,
    BatchSplitInfoRequest, BatchSplitInfoResponse, PDFBatchSplitResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", summary="PDF Service Status")
async def pdf_service_status():
    """Get PDF service status and available operations."""
    return JSONResponse(
        content={
            "service": "PDF Operations",
            "status": "ready",
            "operations": [
                "split - Split PDF by pages or ranges",
                "merge - Combine multiple PDFs",
                "metadata - Extract PDF metadata"
            ],
            "max_file_size": "50MB",
            "supported_formats": ["pdf"]
        }
    )

@router.post("/validate", summary="Validate PDF File")
async def validate_pdf(file: UploadFile = File(...)):
    """Validate uploaded PDF file without processing."""
    try:
        # Validate the uploaded file
        await validate_pdf_file(file)
        
        # Get file information
        file_info = await get_file_info(file)
        
        return JSONResponse(
            content={
                "status": "valid",
                "message": "PDF file is valid and ready for processing",
                "file_info": file_info
            }
        )
    except Exception as e:
        logger.error(f"PDF validation failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"PDF validation failed: {str(e)}"
        )

@router.post("/info", summary="Get PDF File Information")
async def get_pdf_info(file: UploadFile = File(...)):
    """Get detailed information about uploaded PDF file."""
    try:
        # Validate the file first
        await validate_pdf_file(file)
        
        # Get comprehensive file information
        file_info = await get_file_info(file)
        
        return JSONResponse(
            content={
                "status": "success",
                "file_info": file_info,
                "message": "File information retrieved successfully"
            }
        )
    except Exception as e:
        logger.error(f"Failed to get PDF info: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get PDF info: {str(e)}"
        )

@router.post("/metadata", summary="Extract PDF Metadata")
async def extract_pdf_metadata(file: UploadFile = File(...)):
    """Extract comprehensive metadata from PDF file."""
    try:
        start_time = time.time()
        
        # Validate the file
        await validate_pdf_file(file)
        
        # Read file content
        pdf_content = await file.read()
        
        # Extract metadata using PDF service
        metadata = await PDFService.get_metadata(pdf_content)
        
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Metadata extracted successfully",
                "processing_time_ms": round(processing_time, 2),
                **metadata
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to extract PDF metadata: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to extract metadata: {str(e)}"
        )

@router.post("/split/ranges", summary="Split PDF by Page Ranges")
async def split_pdf_by_ranges(
    file: UploadFile = File(...),
    ranges: str = Form(..., description="Comma-separated page ranges (e.g., '1-3,5,7-9')")
):
    """Split PDF by specified page ranges."""
    try:
        start_time = time.time()
        
        # Validate the file
        await validate_pdf_file(file)
        
        # Parse ranges
        range_list = [r.strip() for r in ranges.split(',') if r.strip()]
        if not range_list:
            raise HTTPException(status_code=400, detail="No page ranges specified")
        
        # Read file content
        pdf_content = await file.read()
        
        # Split PDF using service
        split_files = await PDFService.split_by_ranges(pdf_content, range_list)
        
        # Get source metadata
        metadata = await PDFService.get_metadata(pdf_content)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Create ZIP file containing all split PDFs
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, pdf_bytes in split_files.items():
                zip_file.writestr(filename, pdf_bytes)
        
        zip_buffer.seek(0)
        
        # Return ZIP file as streaming response
        return StreamingResponse(
            io.BytesIO(zip_buffer.getvalue()),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=split_pdf_ranges.zip",
                "X-File-Count": str(len(split_files)),
                "X-Processing-Time-Ms": str(round(processing_time, 2)),
                "X-Source-Pages": str(metadata["page_count"])
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to split PDF by ranges: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to split PDF: {str(e)}"
        )

@router.post("/split/pages", summary="Split PDF into Individual Pages")
async def split_pdf_to_pages(file: UploadFile = File(...)):
    """Split PDF into individual pages."""
    try:
        start_time = time.time()
        
        # Validate the file
        await validate_pdf_file(file)
        
        # Read file content
        pdf_content = await file.read()
        
        # Split PDF into individual pages
        split_files = await PDFService.split_to_individual_pages(pdf_content)
        
        # Get source metadata
        metadata = await PDFService.get_metadata(pdf_content)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Create ZIP file containing all pages
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, pdf_bytes in split_files.items():
                zip_file.writestr(filename, pdf_bytes)
        
        zip_buffer.seek(0)
        
        # Return ZIP file as streaming response
        return StreamingResponse(
            io.BytesIO(zip_buffer.getvalue()),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=split_pdf_pages.zip",
                "X-File-Count": str(len(split_files)),
                "X-Processing-Time-Ms": str(round(processing_time, 2)),
                "X-Source-Pages": str(metadata["page_count"])
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to split PDF to pages: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to split PDF: {str(e)}"
        )

# ================== PDF BATCH SPLIT ENDPOINTS ==================

@router.post("/split/batch", 
             summary="Split PDF into Batches", 
             responses={
                 200: {
                     "description": "Successfully split PDF into batches - Returns ZIP file containing batch PDFs",
                     "content": {
                         "application/zip": {
                             "example": "Binary ZIP file containing batch PDFs"
                         }
                     },
                     "headers": {
                         "Content-Disposition": {
                             "description": "Attachment filename for download",
                             "schema": {"type": "string"}
                         },
                         "X-Batch-Count": {
                             "description": "Number of batches created", 
                             "schema": {"type": "string"}
                         },
                         "X-Total-Pages": {
                             "description": "Total pages in original PDF",
                             "schema": {"type": "string"}
                         }
                     }
                 },
                 400: {
                     "description": "Bad request - Invalid file or parameters",
                     "content": {
                         "application/json": {
                             "example": {"detail": "Failed to split PDF into batches: Invalid batch size"}
                         }
                     }
                 }
             })
async def split_pdf_into_batches(
    file: UploadFile = File(..., description="PDF file to split"),
    batch_size: int = Form(..., description="Number of pages per batch", gt=0, le=1000),
    output_prefix: Optional[str] = Form(None, description="Custom filename prefix")
):
    """Split PDF into batches of specified page count.
    
    **For n8n users:** This endpoint returns a ZIP file containing the batch PDFs. 
    In your HTTP Request node, set the response format to "File" to properly 
    handle the binary download.
    
    **Examples:**
    - batch_size=4 and PDF has 10 pages → creates 3 batches:
      - Batch 1: pages 1-4
      - Batch 2: pages 5-8  
      - Batch 3: pages 9-10
    
    **Response:** ZIP file containing individual PDF batches
    **Headers:** Include batch count, total pages, and processing time
    """
    try:
        start_time = time.time()
        
        # Validate the file
        await validate_pdf_file(file)
        
        # Read file content
        pdf_content = await file.read()
        
        # Get original filename for output naming
        original_filename = file.filename or "document.pdf"
        if output_prefix:
            # Use custom prefix if provided
            original_filename = f"{output_prefix}.pdf"
        
        # Split PDF into batches
        batch_files = await PDFService.split_into_batches(
            pdf_content, 
            batch_size, 
            original_filename
        )
        
        # Get source metadata
        metadata = await PDFService.get_metadata(pdf_content)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Create ZIP file containing all batch PDFs
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, pdf_bytes in batch_files.items():
                zip_file.writestr(filename, pdf_bytes)
        
        zip_buffer.seek(0)
        
        # Generate output filename for ZIP
        base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
        zip_filename = f"{base_name}_batches_size_{batch_size}.zip"
        
        # Return ZIP file as streaming response with enhanced headers
        return StreamingResponse(
            io.BytesIO(zip_buffer.getvalue()),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={zip_filename}",
                "X-Batch-Count": str(len(batch_files)),
                "X-Batch-Size": str(batch_size),
                "X-Total-Pages": str(metadata["page_count"]),
                "X-Processing-Time-Ms": str(round(processing_time, 2)),
                "X-File-Size-MB": str(metadata["file_size_mb"]),
                "Cache-Control": "no-cache",
                "Access-Control-Expose-Headers": "Content-Disposition, X-Batch-Count, X-Batch-Size, X-Total-Pages, X-Processing-Time-Ms, X-File-Size-MB"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to split PDF into batches: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to split PDF into batches: {str(e)}"
        )

@router.post("/split/batch/preview", 
             summary="Preview Batch Split (JSON Response)",
             response_model=None,
             responses={
                 200: {
                     "description": "Batch split preview with detailed information",
                     "content": {
                         "application/json": {
                             "example": {
                                 "status": "success",
                                 "message": "PDF would be split into 3 batches",
                                 "batch_info": {
                                     "total_batches": 3,
                                     "batch_size": 10,
                                     "total_pages": 25,
                                     "file_size_mb": 12.34,
                                     "processing_estimate_ms": 2500
                                 },
                                 "batch_details": [
                                     {"batch_number": 1, "pages": "1-10", "page_count": 10},
                                     {"batch_number": 2, "pages": "11-20", "page_count": 10},
                                     {"batch_number": 3, "pages": "21-25", "page_count": 5}
                                 ]
                             }
                         }
                     }
                 }
             })
async def preview_batch_split(
    file: UploadFile = File(..., description="PDF file to analyze"),
    batch_size: int = Form(..., description="Number of pages per batch", gt=0, le=1000),
    output_prefix: Optional[str] = Form(None, description="Custom filename prefix")
):
    """Preview how a PDF would be split into batches without actually creating files.
    
    **For Swagger UI testing:** This endpoint returns JSON instead of binary files,
    making it easier to test and see results in the browser.
    
    **Use this endpoint to:**
    - Test your PDF before actual processing
    - See how many batches would be created
    - Verify page distribution across batches
    - Get processing time estimates
    """
    try:
        start_time = time.time()
        
        # Validate the file
        await validate_pdf_file(file)
        
        # Read file content
        pdf_content = await file.read()
        
        # Get source metadata
        metadata = await PDFService.get_metadata(pdf_content)
        
        # Calculate batch information
        total_pages = metadata["page_count"]
        total_batches = (total_pages + batch_size - 1) // batch_size  # Ceiling division
        
        # Generate batch details
        batch_details = []
        for i in range(total_batches):
            start_page = i * batch_size + 1
            end_page = min((i + 1) * batch_size, total_pages)
            page_count = end_page - start_page + 1
            
            if start_page == end_page:
                pages_str = str(start_page)
            else:
                pages_str = f"{start_page}-{end_page}"
            
            batch_details.append({
                "batch_number": i + 1,
                "pages": pages_str,
                "page_count": page_count,
                "filename": f"batch_{i+1:02d}_pages_{pages_str}.pdf"
            })
        
        processing_time = (time.time() - start_time) * 1000
        
        # Generate output filename for reference
        original_filename = file.filename or "document.pdf"
        if output_prefix:
            original_filename = f"{output_prefix}.pdf"
        
        base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
        zip_filename = f"{base_name}_batches_size_{batch_size}.zip"
        
        return JSONResponse(
            content={
                "status": "success",
                "message": f"PDF would be split into {total_batches} batches (batch_size={batch_size})",
                "batch_info": {
                    "total_batches": total_batches,
                    "batch_size": batch_size,
                    "total_pages": total_pages,
                    "file_size_mb": metadata["file_size_mb"],
                    "processing_time_ms": round(processing_time, 2),
                    "output_zip_filename": zip_filename
                },
                "batch_details": batch_details,
                "next_steps": {
                    "to_download": "Use POST /api/v1/pdf/split/batch with same parameters",
                    "note": "Actual processing may take longer for large files"
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to preview PDF batch split: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to preview PDF batch split: {str(e)}"
        )

@router.post("/split/batch/info", summary="Get Batch Split Information")
async def get_batch_split_info(
    file: UploadFile = File(..., description="PDF file to analyze"),
    batch_size: int = Form(..., description="Number of pages per batch", gt=0, le=1000)
):
    """Get information about how a PDF would be split into batches (preview)."""
    try:
        # Validate the file
        await validate_pdf_file(file)
        
        # Read file content
        pdf_content = await file.read()
        
        # Get batch split information
        batch_info = await PDFService.get_batch_split_info(pdf_content, batch_size)
        
        return JSONResponse(
            content={
                "status": "success",
                "message": f"Batch split preview for {batch_info['total_pages']} pages with batch size {batch_size}",
                **batch_info
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get batch split info: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to analyze file for batch splitting: {str(e)}"
        )

# Legacy placeholder endpoints (will be removed later)
@router.post("/split", summary="Split PDF - Legacy Endpoint")
async def split_pdf():
    """Legacy split endpoint - use /split/ranges or /split/pages instead."""
    return JSONResponse(
        content={
            "message": "Please use /split/ranges or /split/pages endpoints",
            "endpoints": {
                "/split/ranges": "Split by page ranges",
                "/split/pages": "Split into individual pages"
            }
        },
        status_code=200
    )

# ================== PDF MERGE ENDPOINTS ==================

@router.post("/merge", summary="Merge Multiple PDFs")
async def merge_pdfs(
    files: List[UploadFile] = File(..., description="PDF files to merge (minimum 2)"),
    merge_strategy: str = Form("append", description="Merge strategy: 'append' or 'interleave'"),
    preserve_metadata: bool = Form(True, description="Preserve metadata from first PDF"),
    output_filename: Optional[str] = Form(None, description="Custom output filename")
):
    """Merge multiple PDF files into a single document."""
    try:
        start_time = time.time()
        
        # Validate minimum file count
        if len(files) < 2:
            raise HTTPException(
                status_code=400, 
                detail="At least 2 PDF files are required for merging"
            )
        
        if len(files) > 20:  # Reasonable limit
            raise HTTPException(
                status_code=400,
                detail="Maximum 20 files allowed for merging"
            )
        
        # Validate and read all files
        pdf_contents = []
        source_files_info = []
        
        for i, file in enumerate(files):
            try:
                # Validate each file
                await validate_pdf_file(file)
                
                # Read content
                content = await file.read()
                pdf_contents.append(content)
                
                # Get file info for response
                file_info = await get_file_info(file)
                source_files_info.append({
                    "index": i + 1,
                    "filename": file.filename,
                    "size_mb": file_info.get("size_mb", 0),
                    "pages": file_info.get("pages", 0)
                })
                
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file at position {i + 1}: {str(e)}"
                )
        
        # Perform merge
        merged_content = await PDFService.merge_pdfs(
            pdf_contents, 
            preserve_metadata=preserve_metadata,
            merge_strategy=merge_strategy
        )
        
        # Get merged file info
        merged_metadata = await PDFService.get_metadata(merged_content)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Generate output filename
        if not output_filename:
            output_filename = f"merged_{int(time.time())}.pdf"
        elif not output_filename.endswith('.pdf'):
            output_filename += '.pdf'
        
        # Return merged PDF as streaming response
        return StreamingResponse(
            io.BytesIO(merged_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={output_filename}",
                "X-Files-Merged": str(len(files)),
                "X-Total-Pages": str(merged_metadata["page_count"]),
                "X-Processing-Time-Ms": str(round(processing_time, 2)),
                "X-Merge-Strategy": merge_strategy,
                "X-File-Size-MB": str(merged_metadata["file_size_mb"])
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to merge PDFs: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to merge PDFs: {str(e)}"
        )

@router.post("/merge/info", summary="Get PDF Merge Information")
async def get_merge_info(files: List[UploadFile] = File(..., description="PDF files to analyze")):
    """Get information about PDFs before merging (preview)."""
    try:
        if len(files) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 PDF files are required"
            )
        
        # Validate and read all files
        pdf_contents = []
        
        for i, file in enumerate(files):
            try:
                await validate_pdf_file(file)
                content = await file.read()
                pdf_contents.append(content)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file at position {i + 1}: {str(e)}"
                )
        
        # Get merge information
        merge_info = await PDFService.get_merge_info(pdf_contents)
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Merge information retrieved successfully",
                **merge_info
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get merge info: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to analyze files: {str(e)}"
        )

@router.post("/merge/pages", summary="Merge PDFs with Page Selection")
async def merge_pdfs_with_pages(
    files: List[UploadFile] = File(..., description="PDF files to merge"),
    page_selections: str = Form(..., description="JSON string of page selections per file"),
    preserve_metadata: bool = Form(True, description="Preserve metadata from first PDF"),
    output_filename: Optional[str] = Form(None, description="Custom output filename")
):
    """Merge PDFs with specific page selections.
    
    page_selections should be a JSON string like: "[[1,2,3], [1,5,6], [2,4]]"
    This means: pages 1,2,3 from file 1, pages 1,5,6 from file 2, pages 2,4 from file 3.
    """
    try:
        start_time = time.time()
        
        # Parse page selections
        try:
            import json
            page_lists = json.loads(page_selections)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid page_selections JSON format"
            )
        
        if len(files) != len(page_lists):
            raise HTTPException(
                status_code=400,
                detail="Number of files must match number of page selection lists"
            )
        
        # Validate and read files
        pdf_specs = []
        
        for i, (file, pages) in enumerate(zip(files, page_lists)):
            try:
                await validate_pdf_file(file)
                content = await file.read()
                
                # Validate page numbers
                if pages and any(p < 1 for p in pages):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid page numbers for file {i + 1}: pages must be >= 1"
                    )
                
                pdf_specs.append((content, pages))
                
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Error with file {i + 1}: {str(e)}"
                )
        
        # Perform merge with page selection
        merged_content = await PDFService.merge_with_page_selection(
            pdf_specs,
            preserve_metadata=preserve_metadata
        )
        
        processing_time = (time.time() - start_time) * 1000
        merged_metadata = await PDFService.get_metadata(merged_content)
        
        # Generate output filename
        if not output_filename:
            output_filename = f"merged_pages_{int(time.time())}.pdf"
        elif not output_filename.endswith('.pdf'):
            output_filename += '.pdf'
        
        return StreamingResponse(
            io.BytesIO(merged_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={output_filename}",
                "X-Files-Merged": str(len(files)),
                "X-Total-Pages": str(merged_metadata["page_count"]),
                "X-Processing-Time-Ms": str(round(processing_time, 2)),
                "X-Merge-Type": "page-selection",
                "X-File-Size-MB": str(merged_metadata["file_size_mb"])
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to merge PDFs with page selection: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to merge PDFs: {str(e)}"
        )

@router.post("/merge/ranges", summary="Merge PDFs with Range Selection")
async def merge_pdfs_with_ranges(
    files: List[UploadFile] = File(..., description="PDF files to merge"),
    range_selections: str = Form(..., description="JSON string of range selections per file"),
    preserve_metadata: bool = Form(True, description="Preserve metadata from first PDF"),
    output_filename: Optional[str] = Form(None, description="Custom output filename")
):
    """Merge PDFs with specific page range selections.
    
    range_selections should be a JSON string like: "[['1-3', '5'], ['2-4'], ['1', '6-8']]"
    This means: pages 1-3,5 from file 1, pages 2-4 from file 2, pages 1,6-8 from file 3.
    """
    try:
        start_time = time.time()
        
        # Parse range selections
        try:
            import json
            range_lists = json.loads(range_selections)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid range_selections JSON format"
            )
        
        if len(files) != len(range_lists):
            raise HTTPException(
                status_code=400,
                detail="Number of files must match number of range selection lists"
            )
        
        # Validate and read files
        pdf_specs = []
        
        for i, (file, ranges) in enumerate(zip(files, range_lists)):
            try:
                await validate_pdf_file(file)
                content = await file.read()
                
                # Validate range format
                for range_str in ranges:
                    if not re.match(r'^\d+(-\d+)?$', range_str.strip()):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid range format in file {i + 1}: {range_str}"
                        )
                
                pdf_specs.append((content, ranges))
                
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Error with file {i + 1}: {str(e)}"
                )
        
        # Perform merge with range selection
        merged_content = await PDFService.merge_with_ranges(
            pdf_specs,
            preserve_metadata=preserve_metadata
        )
        
        processing_time = (time.time() - start_time) * 1000
        merged_metadata = await PDFService.get_metadata(merged_content)
        
        # Generate output filename
        if not output_filename:
            output_filename = f"merged_ranges_{int(time.time())}.pdf"
        elif not output_filename.endswith('.pdf'):
            output_filename += '.pdf'
        
        return StreamingResponse(
            io.BytesIO(merged_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={output_filename}",
                "X-Files-Merged": str(len(files)),
                "X-Total-Pages": str(merged_metadata["page_count"]),
                "X-Processing-Time-Ms": str(round(processing_time, 2)),
                "X-Merge-Type": "range-selection", 
                "X-File-Size-MB": str(merged_metadata["file_size_mb"])
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to merge PDFs with ranges: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to merge PDFs: {str(e)}"
        )
