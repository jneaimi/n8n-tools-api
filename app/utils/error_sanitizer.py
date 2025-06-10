"""
Error message sanitization and production-safe error handling.

Provides utilities to sanitize error messages, remove sensitive information,
and generate user-friendly error messages for production environments.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class ErrorSanitizationLevel(str, Enum):
    """Error sanitization levels."""
    DEVELOPMENT = "development"  # Show detailed errors
    STAGING = "staging"         # Show sanitized errors with some detail
    PRODUCTION = "production"   # Show minimal user-friendly errors

class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorSanitizer:
    """Sanitizes error messages for safe display to users."""
    
    # Patterns to remove from error messages
    SENSITIVE_PATTERNS = [
        # File paths
        r'/[a-zA-Z0-9_\-\.\/]+\.(pdf|png|jpg|jpeg|tiff)',
        r'[C-Z]:\\[a-zA-Z0-9_\-\.\\\s]+',
        r'/tmp/[a-zA-Z0-9_\-\.\/]+',
        r'/var/[a-zA-Z0-9_\-\.\/]+',
        
        # API keys and tokens
        r'sk-[a-zA-Z0-9\-_]{10,}',  # OpenAI/Anthropic style keys (10+ chars after sk-)
        r'[Aa][Pp][Ii][-_]?[Kk][Ee][Yy][-_:]?\s*[a-zA-Z0-9\-_]{20,}',
        r'[Bb][Ee][Aa][Rr][Ee][Rr]\s+[a-zA-Z0-9\-_]{20,}',
        r'[Tt][Oo][Kk][Ee][Nn][-_:]?\s*[a-zA-Z0-9\-_]{20,}',
        
        # IP addresses and hostnames
        r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
        r'[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}',
        
        # Database connection strings
        r'[a-zA-Z]+://[a-zA-Z0-9_\-\.:@]+/[a-zA-Z0-9_\-]+',
        
        # Email addresses
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        
        # Internal error details
        r'Traceback \(most recent call last\):.*',
        r'File "[^"]+", line \d+.*',
        r'in [a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)',
        
        # Stack traces
        r'at [a-zA-Z_][a-zA-Z0-9_.]*\([^)]*\)',
        r'line \d+ in [a-zA-Z_][a-zA-Z0-9_]*',
        
        # Memory addresses
        r'0x[a-fA-F0-9]{8,16}',
        
        # UUIDs
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        
        # Passwords and secrets
        r'[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd][-_:]?\s*[a-zA-Z0-9]+',
        r'[Ss][Ee][Cc][Rr][Ee][Tt][-_:]?\s*[a-zA-Z0-9]+',
    ]
    
    # Replacements for sensitive patterns
    REPLACEMENTS = {
        r'sk-[a-zA-Z0-9\-_]{10,}': '[API_KEY]',
        r'/[a-zA-Z0-9_\-\.\/]+\.(pdf|png|jpg|jpeg|tiff)': '[FILE_PATH]',
        r'[C-Z]:\\[a-zA-Z0-9_\-\.\\\s]+': '[FILE_PATH]',
        r'/tmp/[a-zA-Z0-9_\-\.\/]+': '[TEMP_PATH]',
        r'/var/[a-zA-Z0-9_\-\.\/]+': '[VAR_PATH]',
        r'[Aa][Pp][Ii][-_]?[Kk][Ee][Yy][-_:]?\s*[a-zA-Z0-9\-_]{20,}': '[API_KEY]',
        r'[Bb][Ee][Aa][Rr][Ee][Rr]\s+[a-zA-Z0-9\-_]{20,}': '[BEARER_TOKEN]',
        r'[Tt][Oo][Kk][Ee][Nn][-_:]?\s*[a-zA-Z0-9\-_]{20,}': '[TOKEN]',
        r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b': '[IP_ADDRESS]',
        r'[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}': '[HOSTNAME]',
        r'[a-zA-Z]+://[a-zA-Z0-9_\-\.:@]+/[a-zA-Z0-9_\-]+': '[DATABASE_URL]',
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': '[EMAIL]',
        r'0x[a-fA-F0-9]{8,16}': '[MEMORY_ADDRESS]',
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}': '[UUID]',
        r'[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd][-_:]?\s*[a-zA-Z0-9]+': '[PASSWORD]',
        r'[Ss][Ee][Cc][Rr][Ee][Tt][-_:]?\s*[a-zA-Z0-9]+': '[SECRET]',
    }
    
    # User-friendly error message mappings
    USER_FRIENDLY_MESSAGES = {
        # Python exceptions
        "AttributeError": "A processing error occurred while handling your request",
        "FileNotFoundError": "The requested file could not be found",
        "MemoryError": "The file is too large to process",
        "ConnectionError": "Unable to connect to the processing service",
        "TimeoutError": "The request took too long to process",
        "ValueError": "Invalid data provided in the request",
        "TypeError": "Invalid data type provided",
        "KeyError": "Required information is missing from the request",
        "IndexError": "Invalid data structure in the request",
        "IOError": "File input/output error occurred",
        "OSError": "System error occurred while processing",
        
        # HTTP/Network errors
        "HTTPException": "Service communication error",
        "ClientError": "Request processing error",
        "ServerError": "Service temporarily unavailable",
        "SSLError": "Secure connection error",
        "ProxyError": "Network proxy error",
        
        # OCR specific errors
        "PDFProcessingError": "PDF document processing failed",
        "OCRError": "Text extraction processing failed",
        "MistralAIError": "AI processing service error",
        "ValidationError": "Document validation failed",
        
        # Generic patterns
        "failed to": "Operation was unsuccessful",
        "unable to": "Operation could not be completed",
        "cannot": "Operation is not possible",
        "denied": "Access was denied",
        "forbidden": "Operation not permitted",
        "unauthorized": "Authentication required",
        "invalid": "Invalid input provided",
        "corrupt": "Document appears to be damaged",
        "timeout": "Operation took too long",
        "exceeded": "Limit was exceeded"
    }
    
    def __init__(self, sanitization_level: ErrorSanitizationLevel = ErrorSanitizationLevel.PRODUCTION):
        self.sanitization_level = sanitization_level
    
    def sanitize_error_message(self, message: str) -> str:
        """
        Sanitize error message by removing sensitive information.
        
        Args:
            message: Original error message
            
        Returns:
            Sanitized error message
        """
        if self.sanitization_level == ErrorSanitizationLevel.DEVELOPMENT:
            return message  # Return original message in development
        
        sanitized = message
        
        # Apply replacements for sensitive patterns
        for pattern, replacement in self.REPLACEMENTS.items():
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        # Remove any remaining sensitive patterns that don't have specific replacements
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern not in self.REPLACEMENTS:
                sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
        
        # Additional cleanup
        sanitized = self._clean_technical_details(sanitized)
        
        return sanitized
    
    def get_user_friendly_message(self, technical_error: str) -> str:
        """
        Convert technical error message to user-friendly message.
        
        Args:
            technical_error: Technical error message
            
        Returns:
            User-friendly error message
        """
        if self.sanitization_level == ErrorSanitizationLevel.DEVELOPMENT:
            return technical_error
        
        # Look for known error patterns
        for pattern, friendly_message in self.USER_FRIENDLY_MESSAGES.items():
            if pattern.lower() in technical_error.lower():
                return friendly_message
        
        # Default user-friendly message
        return "An error occurred while processing your request. Please try again or contact support if the issue persists."
    
    def _clean_technical_details(self, message: str) -> str:
        """Remove technical implementation details."""
        # Remove common technical phrases
        technical_phrases = [
            r"Traceback.*?(?=\n\n|\Z)",
            r"File \".*?\", line \d+.*?(?=\n\n|\Z)",
            r"in [a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\).*?(?=\n|\Z)",
            r"raise [A-Za-z]+.*?(?=\n|\Z)",
            r"during handling of.*?(?=\n|\Z)",
            r"The above exception.*?(?=\n|\Z)",
            r"subprocess\..*?(?=\n|\Z)",
            r"thread.*?(?=\n|\Z)"
        ]
        
        cleaned = message
        for phrase in technical_phrases:
            cleaned = re.sub(phrase, '', cleaned, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean up multiple newlines and whitespace
        cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
        cleaned = re.sub(r'^\s+|\s+$', '', cleaned)
        
        return cleaned
    
    def categorize_error_severity(self, error_message: str, error_code: str = None) -> ErrorSeverity:
        """
        Categorize error severity based on message content and error code.
        
        Args:
            error_message: Error message to analyze
            error_code: Optional error code
            
        Returns:
            Error severity level
        """
        critical_indicators = [
            "memory", "system", "database", "connection", "network",
            "authentication", "authorization", "security", "crash"
        ]
        
        high_indicators = [
            "timeout", "unavailable", "failed", "error", "exception",
            "invalid", "corrupt", "denied"
        ]
        
        medium_indicators = [
            "warning", "limit", "exceeded", "retry", "temporary"
        ]
        
        message_lower = error_message.lower()
        
        if any(indicator in message_lower for indicator in critical_indicators):
            return ErrorSeverity.CRITICAL
        elif any(indicator in message_lower for indicator in high_indicators):
            return ErrorSeverity.HIGH
        elif any(indicator in message_lower for indicator in medium_indicators):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def create_safe_error_response(
        self,
        original_error: str,
        error_code: str = "UNKNOWN_ERROR",
        include_suggestions: bool = True
    ) -> Dict[str, Any]:
        """
        Create a production-safe error response.
        
        Args:
            original_error: Original error message
            error_code: Error code
            include_suggestions: Whether to include helpful suggestions
            
        Returns:
            Safe error response dictionary
        """
        sanitized_message = self.sanitize_error_message(original_error)
        user_friendly_message = self.get_user_friendly_message(original_error)
        severity = self.categorize_error_severity(original_error, error_code)
        
        response = {
            "status": "error",
            "error_code": error_code,
            "message": user_friendly_message if self.sanitization_level == ErrorSanitizationLevel.PRODUCTION else sanitized_message,
            "severity": severity.value,
            "timestamp": round(time.time(), 3)
        }
        
        if include_suggestions:
            response["suggestions"] = self._generate_suggestions(original_error, error_code)
        
        # Include technical details only in non-production environments
        if self.sanitization_level != ErrorSanitizationLevel.PRODUCTION:
            response["technical_details"] = sanitized_message
        
        return response
    
    def _generate_suggestions(self, error_message: str, error_code: str) -> List[str]:
        """Generate helpful suggestions based on error content."""
        suggestions = []
        message_lower = error_message.lower()
        
        if "file" in message_lower:
            if "size" in message_lower or "large" in message_lower:
                suggestions.extend([
                    "Try reducing the file size",
                    "Compress the document before uploading",
                    "Split large documents into smaller files"
                ])
            elif "format" in message_lower or "invalid" in message_lower:
                suggestions.extend([
                    "Ensure the file is a valid PDF, PNG, JPG, JPEG, or TIFF",
                    "Check that the file is not corrupted",
                    "Try saving the file in a different format"
                ])
        
        if "network" in message_lower or "connection" in message_lower:
            suggestions.extend([
                "Check your internet connection",
                "Try again in a few moments",
                "Verify the URL is accessible"
            ])
        
        if "timeout" in message_lower:
            suggestions.extend([
                "Try processing a smaller document",
                "Retry the operation",
                "Break large documents into smaller chunks"
            ])
        
        if "authentication" in message_lower or "api" in message_lower:
            suggestions.extend([
                "Verify your API key is valid and active",
                "Check that your API key has the required permissions",
                "Ensure your API key is not expired"
            ])
        
        if "rate" in message_lower and "limit" in message_lower:
            suggestions.extend([
                "Wait a moment before trying again",
                "Reduce the frequency of requests",
                "Consider upgrading your API plan"
            ])
        
        # Default suggestions if none found
        if not suggestions:
            suggestions = [
                "Try the operation again",
                "Contact support if the issue persists",
                "Check the service status page"
            ]
        
        return suggestions[:3]  # Limit to 3 suggestions for readability

# Import time at the top
import time

# Default sanitizer instance
default_sanitizer = ErrorSanitizer()

def sanitize_error_message(message: str, level: ErrorSanitizationLevel = ErrorSanitizationLevel.PRODUCTION) -> str:
    """Convenience function for sanitizing error messages."""
    sanitizer = ErrorSanitizer(level)
    return sanitizer.sanitize_error_message(message)

def get_user_friendly_message(technical_error: str, level: ErrorSanitizationLevel = ErrorSanitizationLevel.PRODUCTION) -> str:
    """Convenience function for getting user-friendly error messages."""
    sanitizer = ErrorSanitizer(level)
    return sanitizer.get_user_friendly_message(technical_error)

def create_safe_error_response(
    original_error: str,
    error_code: str = "UNKNOWN_ERROR",
    level: ErrorSanitizationLevel = ErrorSanitizationLevel.PRODUCTION
) -> Dict[str, Any]:
    """Convenience function for creating safe error responses."""
    sanitizer = ErrorSanitizer(level)
    return sanitizer.create_safe_error_response(original_error, error_code)
