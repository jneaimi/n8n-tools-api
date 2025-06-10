"""
OCR-specific file handling utilities.

Provides validation and manipulation functions for OCR-supported files.
"""

from fastapi import UploadFile, HTTPException
import os
import tempfile
import re
import uuid
import time
import aiohttp
import asyncio
import logging
from typing import List, Optional, Dict, Tuple
from urllib.parse import urlparse

from app.core.config import settings
from app.core.errors import FileSizeError, FileFormatError
from app.core.logging import (
    log_file_upload, 
    log_validation_result, 
    app_logger, 
    get_correlation_id
)
from app.utils.file_utils import cleanup_temp_file

# Magic bytes for supported file formats
MAGIC_BYTES = {
    'pdf': [b'%PDF'],
    'png': [b'\x89PNG\r\n\x1a\n'],
    'jpg': [b'\xff\xd8\xff'],
    'jpeg': [b'\xff\xd8\xff'],
    'tiff': [b'II*\x00', b'MM\x00*']  # Little-endian and big-endian TIFF
}

# Supported file extensions for OCR
OCR_ALLOWED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff']

# Content types mapping
CONTENT_TYPES = {
    '.pdf': 'application/pdf',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.tiff': 'image/tiff'
}

def sanitize_ocr_filename(filename: str, default_ext: str = '.pdf') -> str:
    """Sanitize filename for OCR operations to prevent path traversal."""
    if not filename:
        return f"upload_{uuid.uuid4().hex[:8]}{default_ext}"
    
    # Remove directory path components
    filename = os.path.basename(filename)
    
    # Remove or replace dangerous characters
    # Keep only alphanumeric, dots, hyphens, underscores
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Ensure it has a proper extension
    if not any(sanitized.lower().endswith(ext) for ext in OCR_ALLOWED_EXTENSIONS):
        sanitized = f"{sanitized}{default_ext}"
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = f"{name[:250]}{ext}"
    
    # Ensure it's not empty after sanitization
    if not sanitized or sanitized in OCR_ALLOWED_EXTENSIONS:
        sanitized = f"upload_{uuid.uuid4().hex[:8]}{default_ext}"
    
    app_logger.debug(f"Sanitized OCR filename: '{filename}' -> '{sanitized}'")
    return sanitized

def get_file_type_from_extension(filename: str) -> str:
    """Get file type from extension."""
    if not filename:
        return 'unknown'
    
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.jpg':
        return 'jpeg'
    elif ext == '.jpeg':
        return 'jpeg'
    elif ext == '.png':
        return 'png'
    elif ext == '.tiff':
        return 'tiff'
    elif ext == '.pdf':
        return 'pdf'
    else:
        return 'unknown'

def validate_magic_bytes(content: bytes, file_type: str) -> bool:
    """Validate file content using magic bytes."""
    if file_type not in MAGIC_BYTES:
        return False
    
    magic_signatures = MAGIC_BYTES[file_type]
    return any(content.startswith(signature) for signature in magic_signatures)

async def validate_ocr_file(file: UploadFile) -> Tuple[bool, str]:
    """
    Validate uploaded file for OCR processing with comprehensive checks.
    
    Returns:
        Tuple[bool, str]: (is_valid, file_type)
    """
    start_time = time.time()
    correlation_id = get_correlation_id()
    filename = file.filename or "unknown"
    
    try:
        # Check file extension
        if not file.filename:
            raise FileFormatError("No filename provided")
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in OCR_ALLOWED_EXTENSIONS:
            raise FileFormatError(f"Invalid file format. Allowed: {OCR_ALLOWED_EXTENSIONS}")
        
        # Get file type
        file_type = get_file_type_from_extension(file.filename)
        
        # Check expected content type (note: this can be spoofed)
        expected_content_type = CONTENT_TYPES.get(file_ext)
        if file.content_type and expected_content_type:
            if not file.content_type.startswith(expected_content_type.split('/')[0]):
                app_logger.warning(f"Content type mismatch: expected {expected_content_type}, got {file.content_type}")
        
        # Read file content for size and magic byte validation
        content = await file.read()
        
        # Log file upload
        log_file_upload(
            filename=filename,
            file_size=len(content),
            content_type=file.content_type or expected_content_type,
            correlation_id=correlation_id
        )
        
        # Check file size (50MB limit)
        if len(content) > settings.MAX_FILE_SIZE:
            raise FileSizeError(f"File too large. Max size: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB")
        
        # Check for empty file
        if len(content) == 0:
            raise FileFormatError("Empty file uploaded")
        
        # Verify file format using magic bytes
        if not validate_magic_bytes(content, file_type):
            raise FileFormatError(f"Invalid {file_type.upper()} file format - incorrect file signature")
        
        # Additional format-specific validation
        if file_type == 'pdf':
            # PDF files should have %%EOF marker
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
        
        app_logger.info(f"Successfully validated {file_type.upper()} file: {filename} ({len(content)} bytes)")
        return True, file_type
        
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
        
        app_logger.warning(f"OCR file validation failed for {filename}: {str(e)}")
        raise

async def save_temp_ocr_file(file: UploadFile, prefix: str = "n8n_ocr_") -> Tuple[str, str]:
    """
    Save uploaded file to temporary location for OCR processing.
    
    Returns:
        Tuple[str, str]: (temp_path, file_type)
    """
    correlation_id = get_correlation_id()
    filename = file.filename or "unknown"
    
    try:
        # Validate file first
        is_valid, file_type = await validate_ocr_file(file)
        
        # Ensure temp directory exists
        os.makedirs(settings.TEMP_DIR, exist_ok=True)
        
        # Read file content
        content = await file.read()
        
        # Sanitize the original filename for the temp file suffix
        safe_filename = sanitize_ocr_filename(filename)
        original_ext = os.path.splitext(safe_filename)[1]
        
        # Create temporary file with secure permissions
        with tempfile.NamedTemporaryFile(
            prefix=prefix,
            suffix=original_ext,
            dir=settings.TEMP_DIR,
            delete=False,
            mode='wb'
        ) as tmp_file:
            tmp_file.write(content)
            temp_path = tmp_file.name
            
        # Set restrictive permissions (readable/writable by owner only)
        os.chmod(temp_path, 0o600)
        
        app_logger.info(
            f"Saved temporary OCR file: {safe_filename} -> {temp_path} ({len(content)} bytes)",
            extra={
                "extra_fields": {
                    "correlation_id": correlation_id,
                    "type": "temp_ocr_file_save",
                    "original_filename": filename,
                    "temp_path": temp_path,
                    "file_size_bytes": len(content),
                    "file_type": file_type
                }
            }
        )
        
        return temp_path, file_type
            
    except Exception as e:
        app_logger.error(f"Failed to save temporary OCR file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")
    finally:
        # Reset file pointer for any subsequent operations
        await file.seek(0)

async def validate_and_download_url(url: str, session_timeout: int = 30) -> Tuple[bytes, str, str]:
    """
    Download and validate file from URL for OCR processing.
    
    Args:
        url: URL to download
        session_timeout: Timeout in seconds for the download
        
    Returns:
        Tuple[bytes, str, str]: (content, filename, file_type)
    """
    correlation_id = get_correlation_id()
    
    try:
        # Parse URL to extract filename
        parsed_url = urlparse(url)
        url_filename = os.path.basename(parsed_url.path) or "remote_document"
        
        # Add extension if missing
        if not any(url_filename.lower().endswith(ext) for ext in OCR_ALLOWED_EXTENSIONS):
            url_filename = f"{url_filename}.pdf"  # Default to PDF
        
        app_logger.info(f"Downloading file from URL: {url}")
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=session_timeout)
        ) as session:
            async with session.get(url) as response:
                # Check HTTP status
                if response.status != 200:
                    raise HTTPException(
                        status_code=404 if response.status == 404 else 400,
                        detail=f"Failed to download file: HTTP {response.status}"
                    )
                
                # Check content length
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > settings.MAX_FILE_SIZE:
                    raise FileSizeError(f"Remote file too large. Max size: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB")
                
                # Download content
                content = await response.read()
                
                # Check actual size
                if len(content) > settings.MAX_FILE_SIZE:
                    raise FileSizeError(f"Remote file too large. Max size: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB")
                
                # Check for empty content
                if len(content) == 0:
                    raise FileFormatError("Empty file downloaded from URL")
                
                # Get content type from response
                content_type = response.headers.get('content-type', '').lower()
                
                # Determine file type from content and URL
                file_type = get_file_type_from_extension(url_filename)
                
                # If we can't determine from filename, try content type
                if file_type == 'unknown':
                    if 'pdf' in content_type:
                        file_type = 'pdf'
                        url_filename = f"{url_filename}.pdf"
                    elif 'png' in content_type:
                        file_type = 'png'
                        url_filename = f"{url_filename}.png"
                    elif 'jpeg' in content_type or 'jpg' in content_type:
                        file_type = 'jpeg'
                        url_filename = f"{url_filename}.jpg"
                    elif 'tiff' in content_type:
                        file_type = 'tiff'
                        url_filename = f"{url_filename}.tiff"
                    else:
                        # Try to detect from magic bytes
                        for fmt, signatures in MAGIC_BYTES.items():
                            if any(content.startswith(sig) for sig in signatures):
                                file_type = fmt
                                url_filename = f"{url_filename}.{fmt}"
                                break
                
                # Validate magic bytes
                if file_type != 'unknown' and not validate_magic_bytes(content, file_type):
                    raise FileFormatError(f"Invalid {file_type.upper()} file format - incorrect file signature")
                
                # Final check - if still unknown, reject
                if file_type == 'unknown':
                    raise FileFormatError("Unable to determine file type from URL")
                
                app_logger.info(
                    f"Successfully downloaded and validated file from URL: {url} -> {url_filename} ({len(content)} bytes)",
                    extra={
                        "extra_fields": {
                            "correlation_id": correlation_id,
                            "type": "url_download",
                            "url": url,
                            "filename": url_filename,
                            "file_size_bytes": len(content),
                            "file_type": file_type,
                            "content_type": content_type
                        }
                    }
                )
                
                return content, url_filename, file_type
                
    except aiohttp.ClientError as e:
        app_logger.error(f"Network error downloading file from URL {url}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Network error: {str(e)}")
    except asyncio.TimeoutError:
        app_logger.error(f"Timeout downloading file from URL {url}")
        raise HTTPException(status_code=400, detail="Download timeout")
    except (FileFormatError, FileSizeError):
        raise
    except Exception as e:
        app_logger.error(f"Unexpected error downloading file from URL {url}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download file from URL")

async def save_temp_file_from_content(content: bytes, filename: str, file_type: str, prefix: str = "n8n_ocr_url_") -> str:
    """
    Save downloaded content to temporary file.
    
    Args:
        content: File content bytes
        filename: Original filename
        file_type: Detected file type
        prefix: Prefix for temp file
        
    Returns:
        str: Path to temporary file
    """
    correlation_id = get_correlation_id()
    
    try:
        # Ensure temp directory exists
        os.makedirs(settings.TEMP_DIR, exist_ok=True)
        
        # Sanitize filename
        safe_filename = sanitize_ocr_filename(filename)
        original_ext = os.path.splitext(safe_filename)[1]
        
        # Create temporary file with secure permissions
        with tempfile.NamedTemporaryFile(
            prefix=prefix,
            suffix=original_ext,
            dir=settings.TEMP_DIR,
            delete=False,
            mode='wb'
        ) as tmp_file:
            tmp_file.write(content)
            temp_path = tmp_file.name
            
        # Set restrictive permissions
        os.chmod(temp_path, 0o600)
        
        app_logger.info(
            f"Saved temporary file from URL content: {safe_filename} -> {temp_path} ({len(content)} bytes)",
            extra={
                "extra_fields": {
                    "correlation_id": correlation_id,
                    "type": "temp_url_file_save",
                    "original_filename": filename,
                    "temp_path": temp_path,
                    "file_size_bytes": len(content),
                    "file_type": file_type
                }
            }
        )
        
        return temp_path
        
    except Exception as e:
        app_logger.error(f"Failed to save temporary file from URL content: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save downloaded file")

async def get_ocr_file_info(file: UploadFile) -> Dict:
    """Get comprehensive file information for OCR files."""
    content = await file.read()
    await file.seek(0)  # Reset for subsequent operations
    
    file_type = get_file_type_from_extension(file.filename or "")
    
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "size_mb": round(len(content) / (1024 * 1024), 2),
        "file_type": file_type,
        "sanitized_filename": sanitize_ocr_filename(file.filename or "unknown"),
        "is_valid_format": file_type in ['pdf', 'png', 'jpeg', 'tiff']
    }
