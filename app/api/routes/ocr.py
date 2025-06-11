"""
OCR API routes.

Provides endpoints for AI-powered OCR processing using Mistral AI
designed for n8n workflow automation with comprehensive error handling.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends, Header, Request
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import time
import asyncio

from app.models.ocr_models import (
    OCRUrlRequest, OCROptions, OCRResponse, OCRErrorResponse, 
    OCRServiceStatus, SupportedFileType, OCRWithS3Request, 
    OCRUrlWithS3Request, OCRWithS3Response, S3Config
)
from app.utils.ocr_utils import (
    validate_ocr_file, save_temp_ocr_file, validate_and_download_url,
    save_temp_file_from_content, get_ocr_file_info
)
from app.utils.file_utils import cleanup_temp_file
from app.utils.ocr_response_formatter import OCRResponseFormatter
from app.utils.ocr_s3_processor import OCRResponseProcessor
from app.utils.s3_client import S3ConfigurationError, S3ConnectionError, S3UploadError
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
from app.core.logging import app_logger

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
        app_logger.error(f"Error getting service status: {str(e)}")
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
        app_logger.error(f"Error getting health metrics: {str(e)}")
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
        
        app_logger.info(f"Processing {file_type.upper()} file for OCR: {file_info['filename']} ({file_info['size_mb']} MB) - Auth: {auth_info['key_hash']}")
        
        # Read file content for processing
        with open(temp_file_path, 'rb') as f:
            file_content = f.read()
        
        # Initialize Mistral OCR service with circuit breaker protection
        mistral_service = MistralOCRService()
        
        # Prepare processing options for Mistral's native image extraction
        processing_options = {
            'include_image_base64': extract_images,
            'image_limit': 50 if extract_images else 0,  # Increased limit for native extraction
            'image_min_size': 50,
            'pages': None  # Process all pages
        }
        
        # Process with Mistral OCR using native image extraction
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
            
            # Option to return raw Mistral format or formatted response
            # For now, let's add a simple check - you can make this configurable via request params later
            return_raw_mistral_format = True  # Set to True to get official Mistral format
            
            if return_raw_mistral_format:
                # Return the response in official Mistral API format
                response_data = ocr_result
                
                # Add minimal processing info for debugging
                response_data['n8n_processing_info'] = {
                    'source_type': 'file_upload',
                    'source_identifier': file_info['filename'],
                    'processing_time_ms': (time.time() - start_time) * 1000,
                    'api_format': 'mistral_official'
                }
            else:
                # Use enhanced response formatter optimized for Mistral's native image extraction
                formatter = OCRResponseFormatter()
                
                # Format response using Mistral's native image extraction results
                response_data = formatter.format_ocr_response(
                    mistral_response=ocr_result,
                    source_type="file_upload",
                    source_identifier=file_info['filename'],
                    processing_start_time=start_time,
                    include_images=extract_images,
                    include_metadata=include_metadata
                )
                
                # Add processing information about native extraction
                if 'processing_info' in response_data:
                    response_data['processing_info']['image_extraction_method'] = 'mistral_native'
                    response_data['processing_info']['custom_extraction_used'] = False
            
            # Record success metrics
            processing_time = (time.time() - start_time) * 1000
            record_success_metric(operation, processing_time, file_info['size_mb'])
            
            # Log success with appropriate format-specific details
            if return_raw_mistral_format:
                total_pages = len(response_data.get('pages', []))
                total_images = sum(len(page.get('images', [])) for page in response_data.get('pages', []))
                total_text = sum(len(page.get('markdown', '')) for page in response_data.get('pages', []))
                app_logger.info(f"OCR processing completed using official Mistral format: "
                              f"{total_pages} pages, {total_text} chars, {total_images} images")
            else:
                app_logger.info(f"OCR processing completed using Mistral native extraction: "
                              f"{len(response_data.get('extracted_text', ''))} chars, "
                              f"{len(response_data.get('images', []))} images")
            
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
        app_logger.error(f"Unexpected error in OCR processing: {str(e)}", exc_info=True)
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
        
        app_logger.info(f"Processing {file_type.upper()} file from URL for OCR: {request.url} -> {filename} ({len(content) / (1024*1024):.2f} MB) - Auth: {auth_info['key_hash']}")
        
        # Initialize Mistral OCR service
        mistral_service = MistralOCRService()
        
        # Prepare processing options for Mistral's native image extraction
        processing_options = {
            'include_image_base64': extract_images,
            'image_limit': 50 if extract_images else 0,  # Increased limit for native extraction
            'image_min_size': 50,
            'pages': None  # Process all pages
        }
        
        # Process with Mistral OCR using URL directly with native image extraction
        try:
            ocr_result = await mistral_service.process_url_ocr(
                document_url=str(request.url),
                api_key=api_key,
                options=processing_options
            )
            
            # Option to return raw Mistral format or formatted response
            return_raw_mistral_format = True  # Set to True to get official Mistral format
            
            if return_raw_mistral_format:
                # Return the response in official Mistral API format
                response_data = ocr_result
                
                # Add minimal processing info for debugging
                response_data['n8n_processing_info'] = {
                    'source_type': 'url',
                    'source_identifier': str(request.url),
                    'processing_time_ms': (time.time() - start_time) * 1000,
                    'api_format': 'mistral_official'
                }
            else:
                # Use enhanced response formatter optimized for Mistral's native image extraction
                formatter = OCRResponseFormatter()
                
                # Format response using Mistral's native image extraction results
                response_data = formatter.format_ocr_response(
                    mistral_response=ocr_result,
                    source_type="url",
                    source_identifier=str(request.url),
                    processing_start_time=start_time,
                    include_images=extract_images,
                    include_metadata=include_metadata
                )
                
                # Add processing information about native extraction
                if 'processing_info' in response_data:
                    response_data['processing_info']['image_extraction_method'] = 'mistral_native'
                    response_data['processing_info']['custom_extraction_used'] = False
            
            # Log success with appropriate format-specific details  
            if return_raw_mistral_format:
                total_pages = len(response_data.get('pages', []))
                total_images = sum(len(page.get('images', [])) for page in response_data.get('pages', []))
                total_text = sum(len(page.get('markdown', '')) for page in response_data.get('pages', []))
                app_logger.info(f"URL OCR processing completed using official Mistral format: "
                              f"{total_pages} pages, {total_text} chars, {total_images} images")
            else:
                app_logger.info(f"URL OCR processing completed using Mistral native extraction: "
                              f"{len(response_data.get('extracted_text', ''))} chars, "
                              f"{len(response_data.get('images', []))} images")
            
            return JSONResponse(status_code=200, content=response_data)
            
        except MistralAIAuthenticationError as e:
            app_logger.error(f"Mistral API authentication failed: {str(e)}")
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
            app_logger.error(f"Mistral API rate limit exceeded: {str(e)}")
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
            app_logger.error(f"Mistral API error: {str(e)}")
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
        app_logger.error(f"Unexpected error in URL OCR processing: {str(e)}", exc_info=True)
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

@retry_on_error(max_attempts=2, strategy=RetryStrategy.EXPONENTIAL_BACKOFF, circuit_breaker="mistral_api")
@router.post("/process-file-s3",
            summary="Process File for OCR with S3 Image Upload",
            response_model=OCRWithS3Response,
            responses={
                200: {"description": "OCR processing completed successfully with S3 image upload"},
                400: {"description": "Invalid file or S3 configuration", "model": OCRErrorResponse},
                401: {"description": "Authentication required", "model": OCRErrorResponse},
                413: {"description": "File too large", "model": OCRErrorResponse},
                422: {"description": "Invalid file format", "model": OCRErrorResponse},
                429: {"description": "Rate limit exceeded", "model": OCRErrorResponse},
                500: {"description": "Internal server error", "model": OCRErrorResponse}
            })
async def process_file_ocr_with_s3(
    file: UploadFile = File(..., description="PDF or image file to process"),
    # S3 Configuration Fields
    s3_access_key: str = Form(..., description="S3 access key ID", example="AKIAIOSFODNN7EXAMPLE"),
    s3_secret_key: str = Form(..., description="S3 secret access key", example="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
    s3_bucket_name: str = Form(..., description="S3 bucket name for storing images", example="my-ocr-images"),
    s3_region: str = Form("us-east-1", description="S3 region", example="us-west-2"),
    s3_endpoint: Optional[str] = Form(None, description="S3-compatible endpoint URL (optional for AWS S3)", example="https://minio.example.com:9000"),
    # OCR Options
    extract_images: bool = Form(True, description="Whether to extract images from document"),
    include_metadata: bool = Form(True, description="Whether to include document metadata"),
    language_hint: Optional[str] = Form(None, description="Language hint for better OCR accuracy", example="en"),
    # S3 Upload Options
    image_upload_prefix: str = Form("ocr-images", description="S3 object key prefix for uploaded images"),
    fallback_to_base64: bool = Form(True, description="Whether to fallback to base64 if S3 upload fails"),
    upload_timeout_seconds: int = Form(30, description="Timeout for S3 upload operations in seconds", ge=5, le=300),
    # Authentication
    api_key: str = Depends(require_api_key)
):
    """
    Process uploaded file using AI-powered OCR with S3 image upload and URL replacement.
    
    This endpoint extends the standard OCR functionality by uploading extracted base64 images
    to S3-compatible storage and replacing them with public URLs in the response.
    
    **S3 Configuration Parameters:**
    - s3_access_key: S3 access key ID (required)
    - s3_secret_key: S3 secret access key (required)
    - s3_bucket_name: S3 bucket name (required)
    - s3_region: S3 region, defaults to us-east-1 (optional)
    - s3_endpoint: S3-compatible endpoint URL (optional for AWS S3)
    
    **OCR Options:**
    - extract_images: Whether to extract images from document (default: true)
    - include_metadata: Whether to include document metadata (default: true)  
    - language_hint: Language hint for better OCR accuracy (optional)
    
    **S3 Upload Options:**
    - image_upload_prefix: Object key prefix for uploaded images (default: "ocr-images")
    - fallback_to_base64: Whether to fallback to base64 if S3 upload fails (default: true)
    - upload_timeout_seconds: Timeout for S3 uploads in seconds (default: 30)
    
    **Features:**
    - Maintains compatibility with existing process-file endpoint
    - Uploads base64 images from OCR response to S3 storage
    - Replaces base64 data with public S3 URLs
    - Supports fallback to base64 if S3 upload fails
    - Comprehensive error handling and logging
    - Concurrent S3 uploads for better performance
    
    **Example Usage:**
    1. Upload a PDF file
    2. Fill in S3 credentials and bucket information
    3. Configure OCR and upload options as needed
    4. Execute the request to get OCR results with S3 image URLs
    """
    start_time = time.time()
    temp_file_path = None
    operation = "file_ocr_s3_processing"
    
    # Initialize error context
    error_context = OCRErrorContext(operation=operation)
    
    try:
        # Create S3 config from form parameters
        try:
            s3_config = S3Config(
                endpoint=s3_endpoint,
                access_key=s3_access_key,
                secret_key=s3_secret_key,
                bucket_name=s3_bucket_name,
                region=s3_region
            )
        except Exception as e:
            app_logger.error(f"Invalid S3 configuration: {str(e)}")
            safe_response = create_safe_error_response(
                f"Invalid S3 configuration: {str(e)}",
                "INVALID_S3_CONFIGURATION",
                ErrorSanitizationLevel.PRODUCTION
            )
            return JSONResponse(status_code=400, content=safe_response)
        
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
        
        app_logger.info(
            f"Processing {file_type.upper()} file for OCR with S3 upload: "
            f"{file_info['filename']} ({file_info['size_mb']} MB) - "
            f"Auth: {auth_info['key_hash']}, Bucket: {s3_config.bucket_name}"
        )
        
        # Read file content for processing
        with open(temp_file_path, 'rb') as f:
            file_content = f.read()
        
        # Initialize Mistral OCR service
        mistral_service = MistralOCRService()
        
        # Prepare processing options
        processing_options = {
            'include_image_base64': extract_images,
            'image_limit': 50 if extract_images else 0,
            'image_min_size': 50,
            'pages': None
        }
        
        # Process with Mistral OCR
        try:
            error_context.add_api_context("mistral_ocr_api")
            
            ocr_result = await asyncio.wait_for(
                mistral_service.process_file_ocr(
                    file_content=file_content,
                    filename=file_info['filename'],
                    api_key=api_key,
                    options=processing_options
                ),
                timeout=120.0
            )
            
            # Process with S3 image upload and URL replacement
            if extract_images:
                try:
                    processor = OCRResponseProcessor(
                        s3_config=s3_config,
                        upload_prefix=image_upload_prefix or "ocr-images"
                    )
                    
                    modified_response, upload_info = await processor.process_ocr_response(
                        ocr_result,
                        fallback_to_base64=fallback_to_base64,
                        upload_timeout_seconds=upload_timeout_seconds or 30
                    )
                    
                    # Add S3 upload info to response
                    modified_response['s3_upload_info'] = upload_info
                    
                    # Add processing info
                    modified_response['n8n_processing_info'] = {
                        'source_type': 'file_upload_s3',
                        'source_identifier': file_info['filename'],
                        'processing_time_ms': (time.time() - start_time) * 1000,
                        'api_format': 'mistral_with_s3',
                        's3_images_uploaded': upload_info.get('images_uploaded', 0),
                        's3_upload_success_rate': upload_info.get('upload_success_rate', 1.0)
                    }
                    
                    response_data = modified_response
                    
                except (S3ConfigurationError, S3ConnectionError) as e:
                    app_logger.error(f"S3 configuration/connection error: {str(e)}")
                    
                    if fallback_to_base64:
                        # Fallback to original response without S3 processing
                        app_logger.info("Falling back to base64 images due to S3 error")
                        response_data = ocr_result
                        response_data['s3_upload_info'] = {
                            'upload_attempted': True,
                            's3_error': str(e),
                            'fallback_used': True,
                            'images_uploaded': 0
                        }
                    else:
                        safe_response = create_safe_error_response(
                            "S3 configuration or connection error",
                            "S3_CONFIGURATION_ERROR",
                            ErrorSanitizationLevel.PRODUCTION
                        )
                        return JSONResponse(status_code=400, content=safe_response)
                
                except S3UploadError as e:
                    app_logger.error(f"S3 upload error: {str(e)}")
                    
                    if fallback_to_base64:
                        # Fallback to original response
                        app_logger.info("Falling back to base64 images due to S3 upload error")
                        response_data = ocr_result
                        response_data['s3_upload_info'] = {
                            'upload_attempted': True,
                            'upload_error': str(e),
                            'fallback_used': True,
                            'images_uploaded': 0
                        }
                    else:
                        safe_response = create_safe_error_response(
                            "S3 upload failed",
                            "S3_UPLOAD_ERROR",
                            ErrorSanitizationLevel.PRODUCTION
                        )
                        return JSONResponse(status_code=500, content=safe_response)
            else:
                # No image extraction requested
                response_data = ocr_result
                response_data['s3_upload_info'] = {
                    'upload_attempted': False,
                    'reason': 'image_extraction_disabled'
                }
            
            # Record success metrics
            processing_time = (time.time() - start_time) * 1000
            record_success_metric(operation, processing_time, file_info['size_mb'])
            
            # Log success
            images_info = response_data.get('s3_upload_info', {})
            app_logger.info(
                f"OCR S3 processing completed: {images_info.get('images_uploaded', 0)} "
                f"images uploaded to S3, processing time: {processing_time:.2f}ms"
            )
            
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
        app_logger.error(f"Unexpected error in OCR S3 processing: {str(e)}", exc_info=True)
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

@router.post("/process-url-s3",
            summary="Process URL for OCR with S3 Image Upload", 
            response_model=OCRWithS3Response,
            responses={
                200: {"description": "OCR processing completed successfully with S3 image upload"},
                400: {"description": "Invalid URL or S3 configuration", "model": OCRErrorResponse},
                401: {"description": "Authentication required", "model": OCRErrorResponse},
                404: {"description": "Document not found at URL", "model": OCRErrorResponse},
                422: {"description": "Invalid file format at URL", "model": OCRErrorResponse},
                500: {"description": "Internal server error", "model": OCRErrorResponse}
            })
async def process_url_ocr_with_s3(
    request: OCRUrlWithS3Request,
    api_key: str = Depends(require_api_key)
):
    """
    Process document from URL using AI-powered OCR with S3 image upload and URL replacement.
    
    This endpoint extends the standard URL OCR functionality by uploading extracted base64 images
    to S3-compatible storage and replacing them with public URLs in the response.
    
    **Request Body (JSON):**
    ```json
    {
        "url": "https://example.com/document.pdf",
        "s3_config": {
            "access_key": "AKIAIOSFODNN7EXAMPLE",
            "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "bucket_name": "my-ocr-images",
            "region": "us-west-2"
        },
        "extract_images": true,
        "include_metadata": true,
        "fallback_to_base64": true
    }
    ```
    
    **Features:**
    - Downloads and processes documents from URLs
    - Uploads base64 images from OCR response to S3 storage  
    - Replaces base64 data with public S3 URLs
    - Supports fallback to base64 if S3 upload fails
    - Maintains compatibility with existing process-url endpoint
    - Comprehensive error handling for URL and S3 operations
    
    **Supported URL formats:** Direct links to PDF, PNG, JPG, JPEG, TIFF files
    **Remote file size limit:** 50MB
    """
    start_time = time.time()
    temp_file_path = None
    operation = "url_ocr_s3_processing"
    
    # Initialize error context
    error_context = OCRErrorContext(operation=operation)
    
    try:
        # Download and validate file from URL
        content, filename, file_type = await validate_and_download_url(str(request.url))
        
        # Save to temporary file
        temp_file_path = await save_temp_file_from_content(content, filename, file_type)
        
        # Get authentication info
        auth_info = get_auth_info(api_key)
        
        app_logger.info(
            f"Processing {file_type.upper()} file from URL for OCR with S3 upload: "
            f"{request.url} -> {filename} ({len(content) / (1024*1024):.2f} MB) - "
            f"Auth: {auth_info['key_hash']}, Bucket: {request.s3_config.bucket_name}"
        )
        
        # Initialize Mistral OCR service
        mistral_service = MistralOCRService()
        
        # Prepare processing options
        processing_options = {
            'include_image_base64': request.extract_images,
            'image_limit': 50 if request.extract_images else 0,
            'image_min_size': 50,
            'pages': None
        }
        
        # Process with Mistral OCR using URL directly
        try:
            ocr_result = await mistral_service.process_url_ocr(
                document_url=str(request.url),
                api_key=api_key,
                options=processing_options
            )
            
            # Process with S3 image upload and URL replacement
            if request.extract_images:
                try:
                    processor = OCRResponseProcessor(
                        s3_config=request.s3_config,
                        upload_prefix=request.image_upload_prefix or "ocr-images"
                    )
                    
                    modified_response, upload_info = await processor.process_ocr_response(
                        ocr_result,
                        fallback_to_base64=request.fallback_to_base64,
                        upload_timeout_seconds=request.upload_timeout_seconds or 30
                    )
                    
                    # Add S3 upload info to response
                    modified_response['s3_upload_info'] = upload_info
                    
                    # Add processing info
                    modified_response['n8n_processing_info'] = {
                        'source_type': 'url_s3',
                        'source_identifier': str(request.url),
                        'processing_time_ms': (time.time() - start_time) * 1000,
                        'api_format': 'mistral_with_s3',
                        's3_images_uploaded': upload_info.get('images_uploaded', 0),
                        's3_upload_success_rate': upload_info.get('upload_success_rate', 1.0)
                    }
                    
                    response_data = modified_response
                    
                except (S3ConfigurationError, S3ConnectionError) as e:
                    app_logger.error(f"S3 configuration/connection error: {str(e)}")
                    
                    if request.fallback_to_base64:
                        # Fallback to original response without S3 processing
                        app_logger.info("Falling back to base64 images due to S3 error")
                        response_data = ocr_result
                        response_data['s3_upload_info'] = {
                            'upload_attempted': True,
                            's3_error': str(e),
                            'fallback_used': True,
                            'images_uploaded': 0
                        }
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail={
                                "status": "error",
                                "error_code": "S3_CONFIGURATION_ERROR",
                                "message": "S3 configuration or connection error",
                                "details": {"error": str(e), "url": str(request.url)}
                            }
                        )
                
                except S3UploadError as e:
                    app_logger.error(f"S3 upload error: {str(e)}")
                    
                    if request.fallback_to_base64:
                        # Fallback to original response
                        app_logger.info("Falling back to base64 images due to S3 upload error")
                        response_data = ocr_result
                        response_data['s3_upload_info'] = {
                            'upload_attempted': True,
                            'upload_error': str(e),
                            'fallback_used': True,
                            'images_uploaded': 0
                        }
                    else:
                        raise HTTPException(
                            status_code=500,
                            detail={
                                "status": "error",
                                "error_code": "S3_UPLOAD_ERROR",
                                "message": "S3 upload failed",
                                "details": {"error": str(e), "url": str(request.url)}
                            }
                        )
            else:
                # No image extraction requested
                response_data = ocr_result
                response_data['s3_upload_info'] = {
                    'upload_attempted': False,
                    'reason': 'image_extraction_disabled'
                }
            
            # Log success
            images_info = response_data.get('s3_upload_info', {})
            app_logger.info(
                f"URL OCR S3 processing completed: {images_info.get('images_uploaded', 0)} "
                f"images uploaded to S3, processing time: {(time.time() - start_time) * 1000:.2f}ms"
            )
            
            return JSONResponse(status_code=200, content=response_data)
            
        except MistralAIAuthenticationError as e:
            app_logger.error(f"Mistral API authentication failed: {str(e)}")
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
            app_logger.error(f"Mistral API rate limit exceeded: {str(e)}")
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
            app_logger.error(f"Mistral API error: {str(e)}")
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
        app_logger.error(f"Unexpected error in URL OCR S3 processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error_code": "INTERNAL_ERROR", 
                "message": "Internal server error during URL OCR S3 processing",
                "details": {"error": str(e), "url": str(request.url)}
            }
        )
    finally:
        # Clean up temporary file
        if temp_file_path:
            cleanup_temp_file(temp_file_path)

