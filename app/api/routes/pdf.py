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

from app.services.pdf_service import PDFService
from app.utils.file_utils import validate_pdf_file, get_file_info, save_temp_file, cleanup_temp_file
from app.models.pdf_models import PageRangeRequest, PDFSplitResponse, PDFMetadataResponse

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

@router.post("/merge", summary="Merge PDFs")  
async def merge_pdfs():
    """Merge multiple PDFs into one - To be implemented."""
    return JSONResponse(
        content={"message": "PDF merge functionality coming soon"},
        status_code=501
    )
