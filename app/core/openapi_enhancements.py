"""
Enhanced OpenAPI specification for OCR API endpoints.

This module provides additional OpenAPI documentation and examples
beyond the auto-generated FastAPI documentation.
"""

from typing import Dict, Any

def get_enhanced_openapi_examples() -> Dict[str, Any]:
    """
    Get enhanced OpenAPI examples for OCR endpoints.
    
    Returns comprehensive examples for n8n integration and API testing.
    """
    return {
        "ocr_file_processing_examples": {
            "simple_pdf_processing": {
                "summary": "Process PDF with basic options",
                "description": "Example for n8n: Basic PDF OCR processing",
                "value": {
                    "file": "(Upload PDF file here)",
                    "extract_images": True,
                    "include_metadata": True,
                    "language_hint": "en"
                }
            },
            "image_ocr_with_spanish": {
                "summary": "Process image with Spanish language hint",
                "description": "Example for n8n: Image OCR with language optimization",
                "value": {
                    "file": "(Upload image file here)",
                    "extract_images": False,
                    "include_metadata": True,
                    "language_hint": "es"
                }
            },
            "complex_document_processing": {
                "summary": "Process complex document with all features",
                "description": "Example for n8n: Full feature OCR processing",
                "value": {
                    "file": "(Upload document here)",
                    "extract_images": True,
                    "include_metadata": True,
                    "language_hint": "en"
                }
            }
        },
        "ocr_url_processing_examples": {
            "simple_url_processing": {
                "summary": "Process document from URL",
                "description": "Example for n8n: Basic URL-based OCR processing",
                "value": {
                    "url": "https://example.com/sample-document.pdf"
                }
            },
            "image_url_processing": {
                "summary": "Process image from URL",
                "description": "Example for n8n: Image URL OCR processing",
                "value": {
                    "url": "https://example.com/document-scan.png"
                }
            },
            "academic_paper_processing": {
                "summary": "Process academic paper from URL",
                "description": "Example for n8n: Academic document processing",
                "value": {
                    "url": "https://arxiv.org/pdf/2301.12345.pdf"
                }
            }
        },
        "response_examples": {
            "successful_pdf_processing": {
                "summary": "Successful PDF processing response",
                "description": "Complete response from PDF OCR processing",
                "value": {
                    "status": "success",
                    "message": "OCR processing completed successfully",
                    "extracted_text": "# Research Paper Title\n\n## Abstract\n\nThis paper presents a comprehensive analysis of...\n\n## Introduction\n\nOptical Character Recognition (OCR) has become increasingly important...",
                    "images": [
                        {
                            "id": "img_001_page_1",
                            "format": "png",
                            "size": {"width": 1200, "height": 800},
                            "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                            "page_number": 1,
                            "position": {
                                "x": 15.5,
                                "y": 25.3,
                                "width": 65.0,
                                "height": 45.2
                            }
                        },
                        {
                            "id": "img_002_page_2", 
                            "format": "jpeg",
                            "size": {"width": 800, "height": 600},
                            "data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k=",
                            "page_number": 2,
                            "position": {
                                "x": 20.1,
                                "y": 35.7,
                                "width": 55.5,
                                "height": 40.8
                            }
                        }
                    ],
                    "metadata": {
                        "title": "Research Paper on OCR Technology",
                        "author": "Dr. Jane Smith, Dr. John Doe",
                        "subject": "Computer Vision and Machine Learning",
                        "creator": "LaTeX with hyperref package",
                        "producer": "pdfTeX-1.40.25",
                        "creation_date": "2024-01-15T14:30:22Z",
                        "modification_date": "2024-01-15T14:35:18Z",
                        "page_count": 15,
                        "file_size": 2458624,
                        "language": "en"
                    },
                    "processing_info": {
                        "processing_time_ms": 3456.78,
                        "source_type": "file_upload",
                        "ai_model_used": "mistral-ocr-latest",
                        "confidence_score": 0.94,
                        "pages_processed": 15
                    }
                }
            },
            "successful_image_processing": {
                "summary": "Successful image processing response", 
                "description": "Complete response from image OCR processing",
                "value": {
                    "status": "success",
                    "message": "OCR processing completed successfully",
                    "extracted_text": "INVOICE\n\nDate: March 15, 2024\nInvoice #: INV-2024-001\n\nBill To:\nAcme Corporation\n123 Business St\nNew York, NY 10001\n\nDescription: Professional Services\nAmount: $1,250.00\nTax: $125.00\nTotal: $1,375.00",
                    "images": [],
                    "metadata": {
                        "page_count": 1,
                        "file_size": 156789,
                        "language": "en"
                    },
                    "processing_info": {
                        "processing_time_ms": 1234.56,
                        "source_type": "file_upload",
                        "ai_model_used": "mistral-ocr-latest",
                        "confidence_score": 0.98,
                        "pages_processed": 1
                    }
                }
            },
            "url_processing_response": {
                "summary": "Successful URL processing response",
                "description": "Complete response from URL-based OCR processing",
                "value": {
                    "status": "success",
                    "message": "OCR processing completed successfully",
                    "extracted_text": "CERTIFICATE OF ACHIEVEMENT\n\nThis is to certify that\n\nJOHN SMITH\n\nhas successfully completed the course\n\nAdvanced Data Analysis\n\nAwarded on December 10, 2023\n\nCertificate ID: CERT-2023-DA-4567",
                    "images": [
                        {
                            "id": "logo_header",
                            "format": "png",
                            "size": {"width": 300, "height": 150},
                            "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                            "page_number": 1,
                            "position": {
                                "x": 35.0,
                                "y": 10.0,
                                "width": 30.0,
                                "height": 15.0
                            }
                        }
                    ],
                    "metadata": {
                        "page_count": 1,
                        "file_size": 567890,
                        "language": "en"
                    },
                    "processing_info": {
                        "processing_time_ms": 2789.34,
                        "source_type": "url",
                        "ai_model_used": "mistral-ocr-latest",
                        "confidence_score": 0.96,
                        "pages_processed": 1
                    }
                }
            }
        },
        "error_examples": {
            "authentication_error": {
                "summary": "Authentication failure",
                "description": "Invalid or missing API key",
                "value": {
                    "status": "error",
                    "error_code": "OCR_API_AUTH_FAILED",
                    "message": "Invalid or expired API key",
                    "details": {
                        "auth_method": "X-API-Key",
                        "correlation_id": "req_67890abc",
                        "timestamp": "2024-01-15T10:30:45Z"
                    }
                }
            },
            "file_too_large_error": {
                "summary": "File size exceeded",
                "description": "File exceeds maximum size limit",
                "value": {
                    "status": "error",
                    "error_code": "OCR_FILE_TOO_LARGE",
                    "message": "File size exceeds maximum limit of 50MB",
                    "details": {
                        "file_size_mb": 67.8,
                        "max_size_mb": 50,
                        "filename": "large_document.pdf",
                        "correlation_id": "req_12345def"
                    }
                }
            },
            "invalid_file_format_error": {
                "summary": "Unsupported file format",
                "description": "File format not supported for OCR",
                "value": {
                    "status": "error",
                    "error_code": "OCR_INVALID_FILE_FORMAT",
                    "message": "File format not supported for OCR processing",
                    "details": {
                        "detected_format": "docx",
                        "supported_formats": ["pdf", "png", "jpg", "jpeg", "tiff"],
                        "filename": "document.docx",
                        "correlation_id": "req_abc12345"
                    }
                }
            },
            "rate_limit_error": {
                "summary": "Rate limit exceeded",
                "description": "Too many requests in time window",
                "value": {
                    "status": "error",
                    "error_code": "OCR_API_RATE_LIMIT",
                    "message": "Rate limit exceeded. Please wait before making more requests",
                    "details": {
                        "limit_type": "per_minute",
                        "limit_value": 60,
                        "reset_time": "2024-01-15T10:31:00Z",
                        "retry_after_seconds": 45,
                        "correlation_id": "req_rate123"
                    }
                }
            },
            "url_unreachable_error": {
                "summary": "URL not accessible",
                "description": "Cannot access the provided URL",
                "value": {
                    "status": "error",
                    "error_code": "OCR_URL_UNREACHABLE",
                    "message": "Cannot access the provided URL",
                    "details": {
                        "url": "https://example.com/missing-document.pdf",
                        "http_status": 404,
                        "error_reason": "Not Found",
                        "correlation_id": "req_url404"
                    }
                }
            },
            "processing_timeout_error": {
                "summary": "Processing timeout",
                "description": "OCR processing exceeded time limit",
                "value": {
                    "status": "error",
                    "error_code": "OCR_TIMEOUT_ERROR",
                    "message": "OCR processing timed out - document may be too complex",
                    "details": {
                        "timeout_seconds": 120,
                        "pages_processed": 8,
                        "total_pages": 15,
                        "suggestions": [
                            "Try splitting the document into smaller sections",
                            "Reduce image extraction if enabled",
                            "Retry with a simpler document format"
                        ],
                        "correlation_id": "req_timeout789"
                    }
                }
            },
            "service_unavailable_error": {
                "summary": "Service temporarily unavailable",
                "description": "OCR service is temporarily unavailable",
                "value": {
                    "status": "error",
                    "error_code": "OCR_API_SERVICE_UNAVAILABLE",
                    "message": "OCR service is temporarily unavailable",
                    "details": {
                        "service": "mistral-ocr-latest",
                        "estimated_restoration": "2024-01-15T11:00:00Z",
                        "alternative_actions": [
                            "Retry the request in a few minutes",
                            "Check service status at /health endpoint"
                        ],
                        "correlation_id": "req_service503"
                    }
                }
            }
        },
        "health_response_examples": {
            "healthy_service": {
                "summary": "Healthy service status",
                "description": "Service is operating normally",
                "value": {
                    "timestamp": 1705316445.123,
                    "health_score": 0.96,
                    "status": "healthy",
                    "components": {
                        "mistral_api": {"status": "healthy", "response_time_ms": 145},
                        "file_storage": {"status": "healthy", "available_space_gb": 250},
                        "error_rate": {"status": "healthy", "rate_percent": 1.2}
                    },
                    "recommendations": [
                        "Service is operating optimally",
                        "All systems are functioning normally"
                    ],
                    "metrics": {
                        "total_requests": 5432,
                        "total_errors": 68,
                        "error_rate": 0.0125,
                        "success_rate": 0.9875,
                        "avg_processing_time_ms": 2145.67,
                        "top_errors": {
                            "OCR_FILE_TOO_LARGE": 23,
                            "OCR_INVALID_FILE_FORMAT": 18,
                            "OCR_API_RATE_LIMIT": 15
                        }
                    },
                    "circuit_breakers": {
                        "mistral_api": {
                            "state": "closed",
                            "success_rate": 0.987
                        },
                        "url_download": {
                            "state": "closed", 
                            "success_rate": 0.945
                        }
                    },
                    "service_health": {
                        "mistral_api": True,
                        "url_download": True,
                        "overall_operational": True
                    }
                }
            },
            "degraded_service": {
                "summary": "Degraded service status",
                "description": "Service is experiencing issues",
                "value": {
                    "timestamp": 1705316445.123,
                    "health_score": 0.72,
                    "status": "degraded",
                    "components": {
                        "mistral_api": {"status": "degraded", "response_time_ms": 4567},
                        "file_storage": {"status": "healthy", "available_space_gb": 250},
                        "error_rate": {"status": "warning", "rate_percent": 8.5}
                    },
                    "recommendations": [
                        "Mistral API response times are elevated",
                        "Consider implementing request retry logic",
                        "Monitor for service improvements"
                    ],
                    "circuit_breakers": {
                        "mistral_api": {
                            "state": "half-open",
                            "success_rate": 0.743
                        }
                    }
                }
            }
        },
        "n8n_integration_examples": {
            "workflow_setup": {
                "summary": "n8n HTTP Request Node Configuration",
                "description": "Complete setup example for n8n workflows",
                "value": {
                    "node_configuration": {
                        "method": "POST",
                        "url": "{{$parameter['api_base_url']}}/api/v1/ocr/process-file",
                        "authentication": "none",
                        "sendHeaders": True,
                        "headerParameters": {
                            "X-API-Key": "={{$parameter['mistral_api_key']}}"
                        },
                        "sendBody": True,
                        "bodyContentType": "multipart-form-data",
                        "bodyParameters": {
                            "file": "={{$binary.data}}",
                            "extract_images": "={{$parameter['extract_images'] || true}}",
                            "include_metadata": "={{$parameter['include_metadata'] || true}}",
                            "language_hint": "={{$parameter['language_hint'] || 'en'}}"
                        },
                        "options": {
                            "timeout": 300000,
                            "retry": {
                                "enabled": True,
                                "maxAttempts": 3,
                                "waitBetweenAttempts": 5000
                            }
                        }
                    },
                    "workflow_variables": {
                        "api_base_url": "https://your-api-domain.com",
                        "mistral_api_key": "your_mistral_api_key_here",
                        "extract_images": True,
                        "include_metadata": True,
                        "language_hint": "en"
                    }
                }
            },
            "error_handling_workflow": {
                "summary": "n8n Error Handling Example",
                "description": "How to handle errors in n8n workflows",
                "value": {
                    "if_node_conditions": [
                        {
                            "condition": "={{$json.status === 'error'}}",
                            "actions": {
                                "rate_limit": "={{$json.error_code === 'OCR_API_RATE_LIMIT' ? 'wait_and_retry' : 'log_error'}}",
                                "auth_error": "={{$json.error_code === 'OCR_API_AUTH_FAILED' ? 'check_api_key' : 'continue'}}",
                                "file_error": "={{$json.error_code.startsWith('OCR_FILE_') ? 'validate_file' : 'continue'}}"
                            }
                        }
                    ],
                    "retry_logic": {
                        "wait_node": {
                            "duration": "={{$json.details?.retry_after_seconds || 60}}",
                            "unit": "seconds"
                        },
                        "loop_back_to": "OCR_Request_Node"
                    }
                }
            }
        }
    }

def get_enhanced_openapi_schemas() -> Dict[str, Any]:
    """
    Get enhanced OpenAPI schemas for OCR data models.
    
    Returns detailed schemas with validation rules and examples.
    """
    return {
        "OCRFileRequest": {
            "type": "object",
            "required": ["file"],
            "properties": {
                "file": {
                    "type": "string",
                    "format": "binary",
                    "description": "PDF or image file to process",
                    "example": "(binary file data)"
                },
                "extract_images": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to extract images from the document"
                },
                "include_metadata": {
                    "type": "boolean", 
                    "default": True,
                    "description": "Whether to include document metadata in response"
                },
                "language_hint": {
                    "type": "string",
                    "maxLength": 10,
                    "pattern": "^[a-z]{2,5}$",
                    "description": "Language hint for better OCR accuracy (ISO 639 codes)",
                    "examples": ["en", "es", "fr", "de", "zh", "ja", "ar"]
                }
            }
        },
        "OCRUrlRequest": {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {
                    "type": "string",
                    "format": "uri",
                    "pattern": "^https?://",
                    "description": "URL to the document to process (PDF or image)",
                    "examples": [
                        "https://example.com/document.pdf",
                        "https://domain.com/scan.png",
                        "https://arxiv.org/pdf/2301.12345.pdf"
                    ]
                }
            }
        },
        "OCRImage": {
            "type": "object",
            "required": ["id", "format", "size", "data"],
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Unique identifier for the image",
                    "pattern": "^img_[a-zA-Z0-9_]+$",
                    "examples": ["img_001", "img_header_page_1", "img_chart_002"]
                },
                "format": {
                    "type": "string",
                    "enum": ["png", "jpeg", "jpg", "gif", "webp"],
                    "description": "Image format detected from the image data"
                },
                "size": {
                    "type": "object",
                    "required": ["width", "height"],
                    "properties": {
                        "width": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Image width in pixels"
                        },
                        "height": {
                            "type": "integer", 
                            "minimum": 1,
                            "description": "Image height in pixels"
                        }
                    }
                },
                "data": {
                    "type": "string",
                    "pattern": "^data:image/[a-zA-Z]+;base64,",
                    "description": "Base64 encoded image data with data URL prefix"
                },
                "page_number": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Page number where image was found (1-indexed)"
                },
                "position": {
                    "type": "object",
                    "description": "Relative position on page (percentages from top-left)",
                    "properties": {
                        "x": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "X position as percentage from left edge"
                        },
                        "y": {
                            "type": "number",
                            "minimum": 0, 
                            "maximum": 100,
                            "description": "Y position as percentage from top edge"
                        },
                        "width": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "Width as percentage of page width"
                        },
                        "height": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "Height as percentage of page height"
                        }
                    }
                }
            }
        },
        "OCRMetadata": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Document title extracted from metadata"
                },
                "author": {
                    "type": "string", 
                    "description": "Document author(s) extracted from metadata"
                },
                "subject": {
                    "type": "string",
                    "description": "Document subject extracted from metadata"
                },
                "creator": {
                    "type": "string",
                    "description": "Software used to create the document"
                },
                "producer": {
                    "type": "string",
                    "description": "Software used to produce the PDF"
                },
                "creation_date": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Document creation date in ISO 8601 format"
                },
                "modification_date": {
                    "type": "string",
                    "format": "date-time", 
                    "description": "Document modification date in ISO 8601 format"
                },
                "page_count": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Total number of pages in the document"
                },
                "file_size": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "File size in bytes"
                },
                "language": {
                    "type": "string",
                    "pattern": "^[a-z]{2,5}$",
                    "description": "Detected or specified document language (ISO 639 code)"
                }
            }
        },
        "OCRProcessingInfo": {
            "type": "object",
            "required": ["processing_time_ms", "source_type", "ai_model_used", "pages_processed"],
            "properties": {
                "processing_time_ms": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Total processing time in milliseconds"
                },
                "source_type": {
                    "type": "string",
                    "enum": ["file_upload", "url"],
                    "description": "Source type of the processed document"
                },
                "ai_model_used": {
                    "type": "string",
                    "description": "AI model used for OCR processing",
                    "examples": ["mistral-ocr-latest"]
                },
                "confidence_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Average confidence score for OCR accuracy (0-1)"
                },
                "pages_processed": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Number of pages successfully processed"
                }
            }
        },
        "OCRResponse": {
            "type": "object",
            "required": ["status", "message", "extracted_text", "processing_info"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["success"],
                    "description": "Operation status indicator"
                },
                "message": {
                    "type": "string",
                    "description": "Human-readable operation result message"
                },
                "extracted_text": {
                    "type": "string",
                    "description": "Complete extracted text content in Markdown format"
                },
                "images": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/OCRImage"},
                    "description": "Extracted images from the document (if extract_images is True)"
                },
                "metadata": {
                    "$ref": "#/components/schemas/OCRMetadata",
                    "description": "Document metadata (if include_metadata is True)"
                },
                "processing_info": {
                    "$ref": "#/components/schemas/OCRProcessingInfo",
                    "description": "Processing information and performance metrics"
                }
            }
        },
        "OCRErrorResponse": {
            "type": "object",
            "required": ["status", "error_code", "message"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["error"],
                    "description": "Error status indicator"
                },
                "error_code": {
                    "type": "string",
                    "enum": [
                        "OCR_INVALID_FILE_FORMAT", "OCR_FILE_TOO_LARGE", "OCR_FILE_CORRUPTED",
                        "OCR_FILE_EMPTY", "OCR_FILE_UNREADABLE", "OCR_URL_UNREACHABLE",
                        "OCR_URL_INVALID", "OCR_DOWNLOAD_FAILED", "OCR_DOWNLOAD_TIMEOUT",
                        "OCR_API_AUTH_FAILED", "OCR_API_RATE_LIMIT", "OCR_API_QUOTA_EXCEEDED",
                        "OCR_API_SERVICE_UNAVAILABLE", "OCR_API_TIMEOUT", "OCR_API_INVALID_RESPONSE",
                        "OCR_PROCESSING_FAILED", "OCR_PARSING_FAILED", "OCR_EXTRACTION_FAILED",
                        "OCR_IMAGE_PROCESSING_FAILED", "OCR_STORAGE_ERROR", "OCR_MEMORY_ERROR",
                        "OCR_TIMEOUT_ERROR", "OCR_INTERNAL_ERROR", "OCR_INVALID_CONFIG",
                        "OCR_MISSING_CREDENTIALS", "OCR_SERVICE_UNAVAILABLE"
                    ],
                    "description": "Standardized error code for programmatic handling"
                },
                "message": {
                    "type": "string",
                    "description": "Human-readable error message"
                },
                "details": {
                    "type": "object",
                    "description": "Additional error context and troubleshooting information",
                    "properties": {
                        "correlation_id": {
                            "type": "string",
                            "description": "Unique identifier for error tracking"
                        },
                        "timestamp": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Error occurrence timestamp"
                        }
                    }
                }
            }
        },
        "HealthResponse": {
            "type": "object",
            "required": ["timestamp", "health_score", "status"],
            "properties": {
                "timestamp": {
                    "type": "number",
                    "description": "Unix timestamp of health check"
                },
                "health_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Overall health score (0-1)"
                },
                "status": {
                    "type": "string",
                    "enum": ["healthy", "degraded", "unhealthy"],
                    "description": "Overall service status"
                },
                "components": {
                    "type": "object",
                    "description": "Status of individual service components"
                },
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Operational recommendations"
                },
                "metrics": {
                    "type": "object",
                    "description": "Performance and error metrics"
                },
                "circuit_breakers": {
                    "type": "object",
                    "description": "Circuit breaker status for external services"
                }
            }
        }
    }

def get_enhanced_security_schemes() -> Dict[str, Any]:
    """Get enhanced security scheme definitions for OpenAPI."""
    return {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header", 
            "name": "X-API-Key",
            "description": "Mistral AI API key for OCR processing authentication"
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "string",
            "description": "Bearer token authentication using Mistral AI API key"
        }
    }
