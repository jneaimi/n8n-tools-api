"""
File handling utilities.

Provides validation and manipulation functions for uploaded files.
"""

from fastapi import UploadFile, HTTPException
import os
import tempfile
import re
import uuid
import time
from typing import List, Optional

from app.core.config import settings
from app.core.errors import FileSizeError, FileFormatError
from app.core.logging import (
    log_file_upload, 
    log_validation_result, 
    app_logger, 
    get_correlation_id
)

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and other security issues."""
    if not filename:
        return f"upload_{uuid.uuid4().hex[:8]}.pdf"
    
    # Remove directory path components
    filename = os.path.basename(filename)
    
    # Remove or replace dangerous characters
    # Keep only alphanumeric, dots, hyphens, underscores
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Ensure it ends with .pdf
    if not sanitized.lower().endswith('.pdf'):
        sanitized = f"{sanitized}.pdf"
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = f"{name[:250]}{ext}"
    
    # Ensure it's not empty after sanitization
    if not sanitized or sanitized == '.pdf':
        sanitized = f"upload_{uuid.uuid4().hex[:8]}.pdf"
    
    logger.debug(f"Sanitized filename: '{filename}' -> '{sanitized}'")
    return sanitized

async def validate_pdf_file(file: UploadFile) -> bool:
    """Validate uploaded PDF file with comprehensive checks."""
    start_time = time.time()
    correlation_id = get_correlation_id()
    filename = file.filename or "unknown.pdf"
    
    try:
        # Check file extension
        if not file.filename:
            raise FileFormatError("No filename provided")
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise FileFormatError(f"Invalid file format. Allowed: {settings.ALLOWED_EXTENSIONS}")
        
        # Check content type (note: this can be spoofed, so we also check magic bytes)
        if file.content_type and file.content_type != "application/pdf":
            raise FileFormatError("Invalid content type. Expected: application/pdf")
        
        # Read file content for size and magic byte validation
        content = await file.read()
        
        # Log file upload
        log_file_upload(
            filename=filename,
            file_size=len(content),
            content_type=file.content_type or "application/pdf",
            correlation_id=correlation_id
        )
        
        # Check file size (50MB limit)
        if len(content) > settings.MAX_FILE_SIZE:
            raise FileSizeError(f"File too large. Max size: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB")
        
        # Check for empty file
        if len(content) == 0:
            raise FileFormatError("Empty file uploaded")
        
        # Verify PDF magic bytes (PDF files start with %PDF)
        if not content.startswith(b'%PDF'):
            raise FileFormatError("Invalid PDF file format - missing PDF header")
        
        # Additional PDF structure validation - check for basic PDF structure
        if b'%%EOF' not in content:
            raise FileFormatError("Invalid PDF file format - missing EOF marker")
        
        # Reset file pointer for subsequent operations
        await file.seek(0)
        
        # Calculate validation time
        validation_time = (time.time() - start_time) * 1000
        
        # Log successful validation
        log_validation_result(
            filename=filename,
            is_valid=True,
            validation_time_ms=validation_time,
            correlation_id=correlation_id
        )
        
        app_logger.info(f"Successfully validated PDF file: {filename} ({len(content)} bytes)")
        return True
        
    except (FileFormatError, FileSizeError) as e:
        # Calculate validation time
        validation_time = (time.time() - start_time) * 1000
        
        # Log failed validation
        log_validation_result(
            filename=filename,
            is_valid=False,
            error_message=str(e),
            validation_time_ms=validation_time,
            correlation_id=correlation_id
        )
        
        app_logger.warning(f"PDF validation failed for {filename}: {str(e)}")
        raise

async def save_temp_file(file: UploadFile, prefix: str = "n8n_pdf_") -> str:
    """Save uploaded file to temporary location with enhanced security."""
    correlation_id = get_correlation_id()
    filename = file.filename or "unknown.pdf"
    
    try:
        # Ensure temp directory exists
        os.makedirs(settings.TEMP_DIR, exist_ok=True)
        
        # Read file content
        content = await file.read()
        
        # Sanitize the original filename for logging purposes
        safe_filename = sanitize_filename(filename)
        
        # Create temporary file with secure permissions
        with tempfile.NamedTemporaryFile(
            prefix=prefix,
            suffix=".pdf",
            dir=settings.TEMP_DIR,
            delete=False,
            mode='wb'
        ) as tmp_file:
            tmp_file.write(content)
            temp_path = tmp_file.name
            
        # Set restrictive permissions (readable/writable by owner only)
        os.chmod(temp_path, 0o600)
        
        app_logger.info(
            f"Saved temporary file: {safe_filename} -> {temp_path} ({len(content)} bytes)",
            extra={
                "extra_fields": {
                    "correlation_id": correlation_id,
                    "type": "temp_file_save",
                    "original_filename": filename,
                    "temp_path": temp_path,
                    "file_size_bytes": len(content)
                }
            }
        )
        
        return temp_path
            
    except Exception as e:
        logger.error(f"Failed to save temporary file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")
    finally:
        # Reset file pointer for any subsequent operations
        await file.seek(0)

def cleanup_temp_file(file_path: str) -> None:
    """Clean up temporary file securely."""
    try:
        if os.path.exists(file_path):
            # Verify the file is in our temp directory for security
            if not file_path.startswith(settings.TEMP_DIR):
                logger.warning(f"Attempted to cleanup file outside temp directory: {file_path}")
                return
                
            os.unlink(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {file_path}: {str(e)}")

def cleanup_temp_files(file_paths: List[str]) -> None:
    """Clean up multiple temporary files."""
    for file_path in file_paths:
        cleanup_temp_file(file_path)

async def get_file_info(file: UploadFile) -> dict:
    """Get comprehensive file information."""
    content = await file.read()
    await file.seek(0)  # Reset for subsequent operations
    
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "size_mb": round(len(content) / (1024 * 1024), 2),
        "sanitized_filename": sanitize_filename(file.filename or "unknown.pdf")
    }
