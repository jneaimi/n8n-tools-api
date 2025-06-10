"""
OCR API routes.

Provides endpoints for AI-powered OCR processing using Mistral AI
designed for n8n workflow automation with comprehensive error handling.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends, Header
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import time
import asyncio

from app.models.ocr_models import (
    OCRUrlRequest, OCROptions, OCRResponse, OCRErrorResponse, 
    OCRServiceStatus, SupportedFileType
)
from app.utils.ocr_utils import (
    validate_ocr_file, save_temp_ocr_file, validate_and_download_url,
    save_temp_file_from_content, get_ocr_file_info
)
from app.utils.file_utils import cleanup_temp_file
from app.utils.ocr_response_formatter import OCRResponseFormatter
from app.core.auth import require_api_key, get_auth_info
from app.services.mistral_service import (
    MistralOCRService, 
    MistralAIError, 
    MistralAIAuthenticationError, 
    MistralAIRateLimitError
)

# Enhanced error handling imports
from app.core.ocr_errors import (
    OCRError, OCRErrorCode, OCRFileValidationError, OCRFileSizeError,
    OCRURLError, OCRAPIError, OCRProcessingError, OCRTimeoutError,
    OCRErrorContext, ocr_error_handler
)
from app.core.errors import FileSizeError, FileFormatError
from app.utils.error_sanitizer import ErrorSanitizationLevel, create_safe_error_response
from app.utils.error_recovery import (
    retry_on_error, with_circuit_breaker, recovery_manager, RetryStrategy
)
from app.utils.error_metrics import (
    record_error_metric, record_success_metric, get_health_score
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/auth/test",
            summary="Test API Key Authentication",
            responses={
                200: {"description": "Authentication successful"},
                401: {"description": "Authentication failed", "model": OCRErrorResponse},
                429: {"description": "Rate limit exceeded", "model": OCRErrorResponse}
            })
async def test_auth(api_key: str = Depends(require_api_key)):
    """
    Test API key authentication without processing any files.
    
    Use this endpoint to verify your API key is valid and working
    before making actual OCR requests.
    
    **Authentication methods:**
    - X-API-Key: <your_api_key>
    - Authorization: Bearer <your_api_key>
    
    **n8n Integration:**
    - Use HTTP Request node with POST method
    - Include API key in headers
    - Expect 200 status for valid keys
    """
    auth_info = get_auth_info(api_key)
    
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": "API key authentication successful",
            "auth_info": {
                "authenticated": auth_info["authenticated"],
                "auth_method": auth_info["auth_method"],
                "rate_limit_remaining": auth_info["rate_limit_remaining"]
            },
            "timestamp": time.time()
        }
    )

@router.post("/validate",
            summary="Validate File for OCR",
            responses={
                200: {"description": "File validation successful"},
                400: {"description": "Invalid file", "model": OCRErrorResponse},
                413: {"description": "File too large", "model": OCRErrorResponse},
                422: {"description": "Invalid file format", "model": OCRErrorResponse}
            })
async def validate_ocr_file_endpoint(
    file: UploadFile = File(..., description="PDF or image file to validate")
):
    """
    Validate file for OCR processing without performing actual OCR.
    
    Enhanced with comprehensive error handling, metrics collection, and sanitization.
    """
    start_time = time.time()
    operation = "file_validation"
    error_context = OCRErrorContext(operation=operation)
    
    try:
        # Add file context
        file_content = await file.read()
        await file.seek(0)  # Reset for validation
        error_context.add_file_context(
            filename=file.filename or "unknown",
            file_size=len(file_content),
            file_type="unknown"
        )
        
        # Validate file with enhanced error handling
        try:
            is_valid, file_type = await validate_ocr_file(file)
        except (FileSizeError, FileFormatError) as e:
            # Convert validation errors to OCR errors
            ocr_error = ocr_error_handler.handle_validation_error(e, file.filename)
            ocr_error.context = error_context
            
            # Record error metric
            processing_time = (time.time() - start_time) * 1000
            record_error_metric(ocr_error, operation, processing_time, len(file_content) / (1024*1024))
            
            # Return sanitized error response
            safe_response = create_safe_error_response(
                str(e),
                ocr_error.error_code.value,
                ErrorSanitizationLevel.PRODUCTION
            )
            
            return JSONResponse(
                status_code=400 if isinstance(e, FileFormatError) else 413,
                content=safe_response
            )
        
        # Get file info
        file_info = await get_ocr_file_info(file)
        
        validation_time = (time.time() - start_time) * 1000
        
        # Record success metric
        record_success_metric(operation, validation_time, file_info['size_mb'])
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "valid",
                "message": f"File is valid for OCR processing",
                "file_info": {
                    "filename": file_info['filename'],
                    "file_type": file_type,
                    "size_mb": file_info['size_mb'],
                    "content_type": file_info['content_type']
                },
                "validation_time_ms": validation_time
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Handle unexpected errors
        validation_time = (time.time() - start_time) * 1000
        ocr_error = ocr_error_handler.handle_unknown_error(e, operation)
        ocr_error.context = error_context
        
        # Record error metric
        record_error_metric(ocr_error, operation, validation_time)
        
        # Return sanitized error response
        safe_response = create_safe_error_response(
            str(e),
            ocr_error.error_code.value,
            ErrorSanitizationLevel.PRODUCTION
        )
        
        return JSONResponse(
            status_code=500,
            content=safe_response
        )

@router.get("/", 
           summary="OCR Service Status",
           response_model=OCRServiceStatus,
           responses={
               200: {"description": "Service status information"},
               503: {"description": "Service unavailable"}
           })
async def ocr_service_status():
    """
    Get OCR service status and capabilities.
    
    Enhanced with health metrics and circuit breaker status.
    """
    try:
        # Get service info from Mistral OCR service
        mistral_service = MistralOCRService()
        service_info = mistral_service.get_service_info()
        
        # Get health score and metrics
        health_data = get_health_score()
        
        # Get circuit breaker status
        circuit_status = recovery_manager.get_circuit_status()
        
        return JSONResponse(
            status_code=200,
            content={
                "service": service_info["service_name"],
                "status": "ready",
                "health": {
                    "score": health_data["health_score"],
                    "status": health_data["status"],
                    "recommendations": health_data["recommendations"][:3]  # Limit recommendations
                },
                "ai_model_available": True,
                "ai_model": service_info["model_name"],
                "supported_formats": service_info["supported_formats"],
                "max_file_size_mb": service_info["max_file_size_mb"],
                "rate_limits": service_info["rate_limits"],
                "circuit_breakers": {
                    name: {
                        "state": status["state"],
                        "success_rate": status["success_rate"]
                    }
                    for name, status in circuit_status.items()
                },
                "features": [
                    "Text extraction from PDFs and images",
                    "Image extraction from documents", 
                    "Metadata extraction",
                    "Multiple language support",
                    "URL-based document processing",
                    "Mathematical formula recognition",
                    "Table structure preservation",
                    "Markdown formatted output",
                    "Comprehensive error handling",
                    "Health monitoring and metrics",
                    "Circuit breaker protection"
                ],
                "pricing_info": service_info["pricing"]
            }
        )
    except Exception as e:
        logger.error(f"Error getting service status: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "service": "OCR Service",
                "status": "unavailable",
                "error": "Service status check failed",
                "timestamp": time.time()
            }
        )

@router.get("/health",
           summary="OCR Service Health Metrics",
           responses={
               200: {"description": "Detailed health metrics"},
               500: {"description": "Health check failed"}
           })
async def ocr_health_metrics():
    """
    Get detailed health metrics for OCR service monitoring.
    
    Provides comprehensive health data including error rates, performance metrics,
    and operational recommendations for monitoring and alerting systems.
    """
    try:
        # Get comprehensive health data
        health_data = get_health_score()
        
        # Get circuit breaker status
        circuit_status = recovery_manager.get_circuit_status()
        
        # Get recent metrics summary
        from app.utils.error_metrics import get_metrics_summary
        metrics_summary = get_metrics_summary(3600)  # Last hour
        
        return JSONResponse(
            status_code=200,
            content={
                "timestamp": time.time(),
                "health_score": health_data["health_score"],
                "status": health_data["status"],
                "components": health_data["components"],
                "recommendations": health_data["recommendations"],
                "metrics": {
                    "total_requests": metrics_summary.total_requests,
                    "total_errors": metrics_summary.total_errors,
                    "error_rate": round(metrics_summary.error_rate, 4),
                    "success_rate": round(metrics_summary.success_rate, 4),
                    "avg_processing_time_ms": round(metrics_summary.avg_processing_time_ms, 2),
                    "top_errors": dict(metrics_summary.errors_by_code),
                    "errors_by_operation": dict(metrics_summary.errors_by_operation)
                },
                "circuit_breakers": circuit_status,
                "service_health": {
                    "mistral_api": circuit_status.get("mistral_api", {}).get("state") == "closed",
                    "url_download": circuit_status.get("url_download", {}).get("state") == "closed",
                    "overall_operational": all(
                        status.get("state") != "open" 
                        for status in circuit_status.values()
                    )
                }
            }
        )
    except Exception as e:
        logger.error(f"Error getting health metrics: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "timestamp": time.time(),
                "status": "error",
                "message": "Health check failed",
                "error": str(e)
            }
        )

@retry_on_error(max_attempts=2, strategy=RetryStrategy.EXPONENTIAL_BACKOFF, circuit_breaker="mistral_api")
@router.post("/process-file",
            summary="Process File for OCR",
            response_model=OCRResponse,
            responses={
                200: {"description": "OCR processing completed successfully"},
                400: {"description": "Invalid file or parameters", "model": OCRErrorResponse},
                401: {"description": "Authentication required", "model": OCRErrorResponse},
                413: {"description": "File too large", "model": OCRErrorResponse},
                422: {"description": "Invalid file format", "model": OCRErrorResponse},
                429: {"description": "Rate limit exceeded", "model": OCRErrorResponse},
                500: {"description": "Internal server error", "model": OCRErrorResponse}
            })
async def process_file_ocr(
    file: UploadFile = File(..., description="PDF or image file to process"),
    extract_images: bool = Form(True, description="Extract images from document"),
    include_metadata: bool = Form(True, description="Include document metadata"),
    language_hint: Optional[str] = Form(None, description="Language hint (e.g., 'en', 'es')"),
    api_key: str = Depends(require_api_key)
):
    """
    Process uploaded file using AI-powered OCR with comprehensive error handling.
    
    Enhanced with retry logic, circuit breaker protection, error metrics,
    and production-safe error responses.
    """
    start_time = time.time()
    temp_file_path = None
    operation = "file_ocr_processing"
    
    # Initialize error context
    error_context = OCRErrorContext(operation=operation)
    
    try:
        # Validate and save file with timeout protection
        try:
            temp_file_path, file_type = await asyncio.wait_for(
                save_temp_ocr_file(file), 
                timeout=30.0
            )
        except asyncio.TimeoutError:
            timeout_error = OCRTimeoutError(
                "File upload and validation timed out",
                timeout_duration=30.0,
                operation="file_upload"
            )
            timeout_error.context = error_context
            record_error_metric(timeout_error, operation, (time.time() - start_time) * 1000)
            
            safe_response = create_safe_error_response(
                "File upload timed out",
                timeout_error.error_code.value,
                ErrorSanitizationLevel.PRODUCTION
            )
            return JSONResponse(status_code=408, content=safe_response)
        
        except (FileSizeError, FileFormatError) as e:
            # Convert validation errors to OCR errors
            ocr_error = ocr_error_handler.handle_validation_error(e, file.filename)
            ocr_error.context = error_context
            
            processing_time = (time.time() - start_time) * 1000
            record_error_metric(ocr_error, operation, processing_time)
            
            safe_response = create_safe_error_response(
                str(e),
                ocr_error.error_code.value,
                ErrorSanitizationLevel.PRODUCTION
            )
            
            status_code = 413 if isinstance(e, FileSizeError) else 400
            return JSONResponse(status_code=status_code, content=safe_response)
        
        # Get file info for logging and context
        file_info = await get_ocr_file_info(file)
        error_context.add_file_context(
            filename=file_info['filename'],
            file_size=file_info['size_bytes'],
            file_type=file_type
        )
        
        # Get authentication info
        auth_info = get_auth_info(api_key)
        
        logger.info(f"Processing {file_type.upper()} file for OCR: {file_info['filename']} ({file_info['size_mb']} MB) - Auth: {auth_info['key_hash']}")
        
        # Read file content for processing
        with open(temp_file_path, 'rb') as f:
            file_content = f.read()
        
        # Initialize Mistral OCR service with circuit breaker protection
        mistral_service = MistralOCRService()
        
        # Prepare processing options
        processing_options = {
            'include_image_base64': extract_images,
            'image_limit': 10 if extract_images else 0,
            'image_min_size': 50,
            'pages': None  # Process all pages
        }
        
        # Process with Mistral OCR with comprehensive error handling
        try:
            error_context.add_api_context("mistral_ocr_api")
            
            ocr_result = await asyncio.wait_for(
                mistral_service.process_file_ocr(
                    file_content=file_content,
                    filename=file_info['filename'],
                    api_key=api_key,
                    options=processing_options
                ),
                timeout=120.0  # 2 minute timeout for processing
            )
            
            # Initialize response formatter with PDF content for image extraction
            formatter = OCRResponseFormatter()
            formatter._pdf_content = file_content  # Store for potential image extraction
            
            # Format response using enhanced formatter
            response_data = formatter.format_ocr_response(
                mistral_response=ocr_result,
                source_type="file_upload",
                source_identifier=file_info['filename'],
                processing_start_time=start_time,
                include_images=extract_images,
                include_metadata=include_metadata
            )
            
            # Record success metrics
            processing_time = (time.time() - start_time) * 1000
            record_success_metric(operation, processing_time, file_info['size_mb'])
            
            return JSONResponse(status_code=200, content=response_data)
            
        except asyncio.TimeoutError:
            timeout_error = OCRTimeoutError(
                "OCR processing timed out - document may be too complex",
                timeout_duration=120.0,
                operation="ocr_processing"
            )
            timeout_error.context = error_context
            
            processing_time = (time.time() - start_time) * 1000
            record_error_metric(timeout_error, operation, processing_time, file_info['size_mb'])
            
            safe_response = create_safe_error_response(
                "Processing timed out",
                timeout_error.error_code.value,
                ErrorSanitizationLevel.PRODUCTION
            )
            return JSONResponse(status_code=408, content=safe_response)
            
        except MistralAIAuthenticationError as e:
            api_error = OCRAPIError(
                "Authentication failed with OCR service",
                api_response_code=401,
                api_response_text=str(e)
            )
            api_error.context = error_context
            
            processing_time = (time.time() - start_time) * 1000
            record_error_metric(api_error, operation, processing_time, file_info['size_mb'])
            
            safe_response = create_safe_error_response(
                "Invalid API key",
                api_error.error_code.value,
                ErrorSanitizationLevel.PRODUCTION
            )
            return JSONResponse(status_code=401, content=safe_response)
            
        except MistralAIRateLimitError as e:
            rate_limit_error = OCRAPIError(
                "Rate limit exceeded for OCR service",
                api_response_code=429,
                api_response_text=str(e)
            )
            rate_limit_error.context = error_context
            
            processing_time = (time.time() - start_time) * 1000
            record_error_metric(rate_limit_error, operation, processing_time, file_info['size_mb'])
            
            safe_response = create_safe_error_response(
                "Too many requests - please wait before retrying",
                rate_limit_error.error_code.value,
                ErrorSanitizationLevel.PRODUCTION
            )
            return JSONResponse(status_code=429, content=safe_response)
            
        except MistralAIError as e:
            processing_error = OCRProcessingError(
                "OCR processing failed",
                processing_stage="mistral_api_call"
            )
            processing_error.context = error_context
            processing_error.details.update({
                "original_error": str(e),
                "api_error": True
            })
            
            processing_time = (time.time() - start_time) * 1000
            record_error_metric(processing_error, operation, processing_time, file_info['size_mb'])
            
            safe_response = create_safe_error_response(
                "OCR processing failed",
                processing_error.error_code.value,
                ErrorSanitizationLevel.PRODUCTION
            )
            return JSONResponse(status_code=500, content=safe_response)
        
    except HTTPException:
        raise
    except Exception as e:
        # Handle unexpected errors
        unknown_error = ocr_error_handler.handle_unknown_error(e, operation)
        unknown_error.context = error_context
        
        processing_time = (time.time() - start_time) * 1000
        record_error_metric(unknown_error, operation, processing_time)
        
        safe_response = create_safe_error_response(
            "An unexpected error occurred",
            unknown_error.error_code.value,
            ErrorSanitizationLevel.PRODUCTION
        )
        return JSONResponse(status_code=500, content=safe_response)
        
    finally:
        # Clean up temporary file
        if temp_file_path:
            cleanup_temp_file(temp_file_path)

@router.post("/process-url",
            summary="Process URL for OCR", 
            response_model=OCRResponse,
            responses={
                200: {"description": "OCR processing completed successfully"},
                400: {"description": "Invalid URL or parameters", "model": OCRErrorResponse},
                401: {"description": "Authentication required", "model": OCRErrorResponse},
                404: {"description": "Document not found at URL", "model": OCRErrorResponse},
                422: {"description": "Invalid file format at URL", "model": OCRErrorResponse},
                500: {"description": "Internal server error", "model": OCRErrorResponse}
            })
async def process_url_ocr(
    request: OCRUrlRequest,
    extract_images: bool = Form(True, description="Extract images from document"),
    include_metadata: bool = Form(True, description="Include document metadata"),
    language_hint: Optional[str] = Form(None, description="Language hint (e.g., 'en', 'es')"),
    api_key: str = Depends(require_api_key)
):
    """
    Process document from URL using AI-powered OCR.
    
    Downloads and processes documents from URLs:
    - Supports direct links to PDF and image files
    - Extracts text, images, and metadata
    - Handles remote document validation
    
    **Supported URL formats:** Direct links to PDF, PNG, JPG, JPEG, TIFF files
    **Authentication:** Required via API key in header
    **Remote file size limit:** 50MB
    
    **n8n Integration:**
    - Use HTTP Request node with JSON body
    - Include document URL in request body
    - Set response format to JSON
    - Include API key in X-API-Key header or Authorization: Bearer header
    - Handle network errors and invalid URLs
    """
    start_time = time.time()
    temp_file_path = None
    
    try:
        # Download and validate file from URL
        content, filename, file_type = await validate_and_download_url(str(request.url))
        
        # Save to temporary file
        temp_file_path = await save_temp_file_from_content(content, filename, file_type)
        
        # Get authentication info
        auth_info = get_auth_info(api_key)
        
        logger.info(f"Processing {file_type.upper()} file from URL for OCR: {request.url} -> {filename} ({len(content) / (1024*1024):.2f} MB) - Auth: {auth_info['key_hash']}")
        
        # Initialize Mistral OCR service
        mistral_service = MistralOCRService()
        
        # Prepare processing options
        processing_options = {
            'include_image_base64': extract_images,
            'image_limit': 10 if extract_images else 0,
            'image_min_size': 50,
            'pages': None  # Process all pages
        }
        
        # Process with Mistral OCR using URL directly
        try:
            ocr_result = await mistral_service.process_url_ocr(
                document_url=str(request.url),
                api_key=api_key,
                options=processing_options
            )
            
            # Initialize response formatter with PDF content for image extraction
            formatter = OCRResponseFormatter()
            formatter._pdf_content = file_content  # Store for potential image extraction
            
            # Format response using enhanced formatter
            response_data = formatter.format_ocr_response(
                mistral_response=ocr_result,
                source_type="url",
                source_identifier=str(request.url),
                processing_start_time=start_time,
                include_images=extract_images,
                include_metadata=include_metadata
            )
            
            return JSONResponse(status_code=200, content=response_data)
            
        except MistralAIAuthenticationError as e:
            logger.error(f"Mistral API authentication failed: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail={
                    "status": "error",
                    "error_code": "AUTHENTICATION_FAILED",
                    "message": "Invalid or expired Mistral API key",
                    "details": {"error": str(e), "url": str(request.url)}
                }
            )
        except MistralAIRateLimitError as e:
            logger.error(f"Mistral API rate limit exceeded: {str(e)}")
            raise HTTPException(
                status_code=429,
                detail={
                    "status": "error",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": "Mistral API rate limit exceeded",
                    "details": {"error": str(e), "url": str(request.url)}
                }
            )
        except MistralAIError as e:
            logger.error(f"Mistral API error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "error_code": "OCR_PROCESSING_ERROR",
                    "message": "OCR processing failed",
                    "details": {"error": str(e), "url": str(request.url)}
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in URL OCR processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error_code": "INTERNAL_ERROR", 
                "message": "Internal server error during URL OCR processing",
                "details": {"error": str(e), "url": str(request.url)}
            }
        )
    finally:
        # Clean up temporary file
        if temp_file_path:
            cleanup_temp_file(temp_file_path)

