"""
Authentication and authorization utilities for OCR endpoints.

Provides secure header-based API key validation.
"""

import hashlib
import secrets
import time
from typing import Optional
from fastapi import HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.logging import app_logger

# Security configuration
MIN_API_KEY_LENGTH = 32
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 100

class APIKeyValidationError(Exception):
    """Custom exception for API key validation errors."""
    pass

class RateLimitExceededError(Exception):
    """Custom exception for rate limit violations."""
    pass

def validate_api_key_format(api_key: str) -> bool:
    """
    Validate API key format without checking actual validity.
    
    Args:
        api_key: The API key to validate
        
    Returns:
        bool: True if format is valid
    """
    if not api_key:
        return False
    
    # Check minimum length
    if len(api_key) < MIN_API_KEY_LENGTH:
        return False
    
    # Check for basic format (alphanumeric + some special chars)
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.')
    if not all(c in allowed_chars for c in api_key):
        return False
    
    return True

def hash_api_key(api_key: str) -> str:
    """
    Create a secure hash of the API key for logging.
    
    Args:
        api_key: The API key to hash
        
    Returns:
        str: SHA-256 hash (first 8 characters)
    """
    return hashlib.sha256(api_key.encode()).hexdigest()[:8]

async def verify_mistral_api_key(api_key: str) -> bool:
    """
    Verify API key with Mistral AI service.
    
    Note: In a real implementation, this would make a test call to Mistral's API
    to verify the key is valid. For this implementation, we'll do basic validation.
    
    Args:
        api_key: The API key to verify
        
    Returns:
        bool: True if key is valid
    """
    # Basic format validation
    if not validate_api_key_format(api_key):
        return False
    
    # TODO: In production, implement actual Mistral API key verification
    # This would involve making a lightweight API call to Mistral to verify the key
    # For now, we'll accept any properly formatted key
    
    # Simulate some keys that would be invalid (for testing purposes)
    invalid_key_patterns = [
        'test-invalid',
        'fake-key',
        'demo-only'
    ]
    
    api_key_lower = api_key.lower()
    if any(pattern in api_key_lower for pattern in invalid_key_patterns):
        return False
    
    return True

# Simple in-memory rate limiting (in production, use Redis or similar)
_rate_limit_store = {}

def check_rate_limit(client_id: str, max_requests: int = RATE_LIMIT_MAX_REQUESTS) -> bool:
    """
    Check if client has exceeded rate limit.
    
    Args:
        client_id: Unique identifier for the client
        max_requests: Maximum requests allowed in time window
        
    Returns:
        bool: True if within limits, False if exceeded
    """
    current_time = time.time()
    
    # Clean up old entries
    cutoff_time = current_time - RATE_LIMIT_WINDOW_SECONDS
    _rate_limit_store[client_id] = [
        timestamp for timestamp in _rate_limit_store.get(client_id, [])
        if timestamp > cutoff_time
    ]
    
    # Check current request count
    request_count = len(_rate_limit_store.get(client_id, []))
    
    if request_count >= max_requests:
        return False
    
    # Add current request
    _rate_limit_store.setdefault(client_id, []).append(current_time)
    return True

async def validate_ocr_api_key(
    x_api_key: Optional[str] = Header(None, description="Mistral AI API key"),
    authorization: Optional[str] = Header(None, description="Authorization header (Bearer token)")
) -> str:
    """
    Validate API key from headers.
    
    Supports both:
    - X-API-Key header
    - Authorization: Bearer <token> header
    
    Args:
        x_api_key: API key from X-API-Key header
        authorization: Authorization header value
        
    Returns:
        str: Validated API key
        
    Raises:
        HTTPException: If authentication fails
    """
    api_key = None
    
    # Try X-API-Key header first
    if x_api_key:
        api_key = x_api_key.strip()
    
    # Try Authorization header if X-API-Key not provided
    elif authorization:
        if authorization.startswith('Bearer '):
            api_key = authorization[7:].strip()  # Remove 'Bearer ' prefix
        else:
            app_logger.warning("Invalid Authorization header format")
            raise HTTPException(
                status_code=401,
                detail={
                    "status": "error",
                    "error_code": "INVALID_AUTH_HEADER",
                    "message": "Authorization header must use Bearer token format",
                    "details": {"expected_format": "Authorization: Bearer <api_key>"}
                }
            )
    
    # No API key provided
    if not api_key:
        app_logger.warning("No API key provided in request")
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "error_code": "MISSING_API_KEY",
                "message": "API key required for OCR operations",
                "details": {
                    "auth_methods": [
                        "X-API-Key: <your_api_key>",
                        "Authorization: Bearer <your_api_key>"
                    ]
                }
            }
        )
    
    # Validate API key format
    if not validate_api_key_format(api_key):
        api_key_hash = hash_api_key(api_key)
        app_logger.warning(f"Invalid API key format: {api_key_hash}")
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "error_code": "INVALID_API_KEY_FORMAT",
                "message": "Invalid API key format",
                "details": {
                    "requirements": [
                        f"Minimum {MIN_API_KEY_LENGTH} characters",
                        "Alphanumeric characters, hyphens, underscores, and dots only"
                    ]
                }
            }
        )
    
    # Rate limiting check
    api_key_hash = hash_api_key(api_key)
    if not check_rate_limit(api_key_hash):
        app_logger.warning(f"Rate limit exceeded for API key: {api_key_hash}")
        raise HTTPException(
            status_code=429,
            detail={
                "status": "error",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded",
                "details": {
                    "limit": f"{RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS} seconds",
                    "retry_after": RATE_LIMIT_WINDOW_SECONDS
                }
            }
        )
    
    # Verify API key with Mistral
    try:
        is_valid = await verify_mistral_api_key(api_key)
        if not is_valid:
            app_logger.warning(f"Invalid Mistral API key: {api_key_hash}")
            raise HTTPException(
                status_code=401,
                detail={
                    "status": "error",
                    "error_code": "INVALID_API_KEY",
                    "message": "Invalid Mistral AI API key",
                    "details": {
                        "help": "Ensure you're using a valid Mistral AI API key"
                    }
                }
            )
    except APIKeyValidationError as e:
        app_logger.error(f"API key validation error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "error_code": "API_KEY_VALIDATION_ERROR",
                "message": "Error validating API key",
                "details": {"error": str(e)}
            }
        )
    
    app_logger.info(f"Successfully authenticated API key: {api_key_hash}")
    return api_key

# FastAPI dependency for OCR endpoints
async def require_api_key(api_key: str = Depends(validate_ocr_api_key)) -> str:
    """
    FastAPI dependency to require valid API key.
    
    Use this as a dependency in OCR endpoints:
    ```python
    async def my_endpoint(api_key: str = Depends(require_api_key)):
        # Endpoint implementation
    ```
    
    Args:
        api_key: Validated API key from validate_ocr_api_key
        
    Returns:
        str: The validated API key
    """
    return api_key

def get_auth_info(api_key: str) -> dict:
    """
    Get authentication information for logging/response.
    
    Args:
        api_key: The authenticated API key
        
    Returns:
        dict: Authentication information (without exposing the key)
    """
    return {
        "authenticated": True,
        "key_hash": hash_api_key(api_key),
        "auth_method": "api_key",
        "rate_limit_remaining": RATE_LIMIT_MAX_REQUESTS - len(
            _rate_limit_store.get(hash_api_key(api_key), [])
        )
    }
