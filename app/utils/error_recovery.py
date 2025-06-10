"""
Error recovery and retry mechanisms for OCR operations.

Provides intelligent retry logic, circuit breakers, fallback mechanisms,
and recovery strategies for robust OCR processing.
"""

import asyncio
import time
from typing import Callable, Any, Dict, Optional, List, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import random

from app.core.ocr_errors import (
    OCRError, OCRErrorCode, OCRTimeoutError, OCRAPIError,
    OCRErrorContext, ocr_error_handler
)
from app.core.logging import app_logger



class RetryStrategy(str, Enum):
    """Retry strategy types."""
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    RANDOM_JITTER = "random_jitter"

class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter_range: float = 0.1
    timeout_per_attempt: Optional[float] = None
    
    # Error codes that should trigger retries
    retryable_error_codes: List[OCRErrorCode] = field(default_factory=lambda: [
        OCRErrorCode.API_TIMEOUT,
        OCRErrorCode.API_SERVICE_UNAVAILABLE,
        OCRErrorCode.API_RATE_LIMIT_EXCEEDED,
        OCRErrorCode.DOWNLOAD_TIMEOUT,
        OCRErrorCode.TIMEOUT_ERROR,
        OCRErrorCode.STORAGE_ERROR
    ])
    
    # Error codes that should never be retried
    non_retryable_error_codes: List[OCRErrorCode] = field(default_factory=lambda: [
        OCRErrorCode.API_AUTHENTICATION_FAILED,
        OCRErrorCode.INVALID_FILE_FORMAT,
        OCRErrorCode.FILE_TOO_LARGE,
        OCRErrorCode.FILE_CORRUPTED,
        OCRErrorCode.INVALID_CONFIGURATION,
        OCRErrorCode.MISSING_CREDENTIALS
    ])

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: float = 60.0  # Seconds before trying half-open
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: float = 30.0  # Request timeout in seconds

class RetryManager:
    """Manages retry logic for OCR operations."""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self.attempt_history: Dict[str, List[Dict[str, Any]]] = {}
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        if self.config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.config.base_delay
        
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
        
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * attempt
        
        elif self.config.strategy == RetryStrategy.RANDOM_JITTER:
            base_delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
            jitter = random.uniform(-self.config.jitter_range, self.config.jitter_range)
            delay = base_delay * (1 + jitter)
        
        else:
            delay = self.config.base_delay
        
        return min(delay, self.config.max_delay)
    
    def is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error should trigger a retry."""
        if isinstance(error, OCRError):
            # Check if error code is explicitly non-retryable
            if error.error_code in self.config.non_retryable_error_codes:
                return False
            
            # Check if error code is explicitly retryable
            if error.error_code in self.config.retryable_error_codes:
                return True
            
            # Check if error is marked as recoverable
            return error.recoverable
        
        # Handle specific exception types
        if isinstance(error, (asyncio.TimeoutError, ConnectionError)):
            return True
        
        if isinstance(error, (ValueError, TypeError, AttributeError)):
            return False
        
        # Default to non-retryable for unknown errors
        return False
    
    def record_attempt(self, operation_id: str, attempt: int, success: bool, error: Exception = None):
        """Record retry attempt for analytics."""
        if operation_id not in self.attempt_history:
            self.attempt_history[operation_id] = []
        
        self.attempt_history[operation_id].append({
            "attempt": attempt,
            "timestamp": time.time(),
            "success": success,
            "error_type": type(error).__name__ if error else None,
            "error_code": error.error_code.value if isinstance(error, OCRError) else None
        })

class CircuitBreaker:
    """Circuit breaker pattern implementation for OCR services."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.request_count = 0
        self.success_rate = 1.0
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time < self.config.recovery_timeout:
                raise OCRError(
                    f"Circuit breaker '{self.name}' is open - service unavailable",
                    OCRErrorCode.SERVICE_UNAVAILABLE,
                    suggestions=[
                        f"Wait {self.config.recovery_timeout} seconds before retrying",
                        "Check service health status",
                        "Try using an alternative processing method"
                    ]
                )
            else:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        
        except Exception as e:
            self._record_failure()
            raise
    
    async def acall(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function through circuit breaker."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time < self.config.recovery_timeout:
                raise OCRError(
                    f"Circuit breaker '{self.name}' is open - service unavailable",
                    OCRErrorCode.SERVICE_UNAVAILABLE,
                    suggestions=[
                        f"Wait {self.config.recovery_timeout} seconds before retrying",
                        "Check service health status",
                        "Try using an alternative processing method"
                    ]
                )
            else:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
        
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        
        except Exception as e:
            self._record_failure()
            raise
    
    def _record_success(self):
        """Record successful operation."""
        self.request_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                app_logger.info(f"Circuit breaker '{self.name}' closed - service recovered")
        
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)
        
        # Update success rate
        self._update_success_rate(True)
    
    def _record_failure(self):
        """Record failed operation."""
        self.request_count += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                app_logger.warning(f"Circuit breaker '{self.name}' opened - service failing")
        
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            app_logger.warning(f"Circuit breaker '{self.name}' re-opened - service still failing")
        
        # Update success rate
        self._update_success_rate(False)
    
    def _update_success_rate(self, success: bool):
        """Update rolling success rate."""
        # Simple exponential moving average
        alpha = 0.1
        new_rate = 1.0 if success else 0.0
        self.success_rate = alpha * new_rate + (1 - alpha) * self.success_rate
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "success_rate": round(self.success_rate, 3),
            "request_count": self.request_count,
            "last_failure_time": self.last_failure_time,
            "time_until_half_open": max(0, self.config.recovery_timeout - (time.time() - self.last_failure_time))
        }

class OCRRecoveryManager:
    """Manages error recovery for OCR operations."""
    
    def __init__(self):
        self.retry_manager = RetryManager()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.fallback_strategies: Dict[str, Callable] = {}
    
    def register_circuit_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """Register a circuit breaker for a service."""
        breaker = CircuitBreaker(name, config)
        self.circuit_breakers[name] = breaker
        return breaker
    
    def register_fallback(self, operation: str, fallback_func: Callable):
        """Register a fallback function for an operation."""
        self.fallback_strategies[operation] = fallback_func
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self.circuit_breakers.get(name)
    
    def get_circuit_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers."""
        return {
            name: breaker.get_status()
            for name, breaker in self.circuit_breakers.items()
        }

def retry_on_error(
    max_attempts: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    circuit_breaker: str = None
):
    """
    Decorator for adding retry logic to functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        strategy: Retry strategy to use
        base_delay: Base delay between retries
        max_delay: Maximum delay between retries
        circuit_breaker: Name of circuit breaker to use
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                strategy=strategy,
                base_delay=base_delay,
                max_delay=max_delay
            )
            retry_manager = RetryManager(config)
            operation_id = f"{func.__name__}_{int(time.time())}"
            
            # Get circuit breaker if specified
            breaker = None
            if circuit_breaker and circuit_breaker in recovery_manager.circuit_breakers:
                breaker = recovery_manager.circuit_breakers[circuit_breaker]
            
            last_error = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    # Apply circuit breaker if available
                    if breaker:
                        result = await breaker.acall(func, *args, **kwargs)
                    else:
                        result = await func(*args, **kwargs)
                    
                    retry_manager.record_attempt(operation_id, attempt, True)
                    return result
                
                except Exception as e:
                    last_error = e
                    retry_manager.record_attempt(operation_id, attempt, False, e)
                    
                    # Check if error is retryable
                    if not retry_manager.is_retryable_error(e):
                        app_logger.warning(f"Non-retryable error in {func.__name__}: {str(e)}")
                        break
                    
                    # Don't retry on the last attempt
                    if attempt == max_attempts:
                        break
                    
                    # Calculate and apply delay
                    delay = retry_manager.calculate_delay(attempt)
                    app_logger.info(f"Retrying {func.__name__} (attempt {attempt + 1}/{max_attempts}) after {delay:.1f}s delay")
                    await asyncio.sleep(delay)
            
            # All retries exhausted or non-retryable error
            if isinstance(last_error, OCRError):
                raise last_error
            else:
                # Wrap unknown errors
                wrapped_error = ocr_error_handler.handle_unknown_error(last_error, func.__name__)
                raise wrapped_error
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, convert to async temporarily
            return asyncio.run(async_wrapper(*args, **kwargs))
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def with_circuit_breaker(breaker_name: str, config: CircuitBreakerConfig = None):
    """
    Decorator for adding circuit breaker protection to functions.
    
    Args:
        breaker_name: Name of the circuit breaker
        config: Circuit breaker configuration
    """
    def decorator(func: Callable):
        # Register circuit breaker if not exists
        if breaker_name not in recovery_manager.circuit_breakers:
            recovery_manager.register_circuit_breaker(breaker_name, config)
        
        breaker = recovery_manager.circuit_breakers[breaker_name]
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.acall(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def with_fallback(fallback_func: Callable):
    """
    Decorator for adding fallback behavior to functions.
    
    Args:
        fallback_func: Function to call if primary function fails
    """
    def decorator(primary_func: Callable):
        @wraps(primary_func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await primary_func(*args, **kwargs)
            except Exception as e:
                app_logger.warning(f"Primary function {primary_func.__name__} failed, using fallback: {str(e)}")
                
                try:
                    if asyncio.iscoroutinefunction(fallback_func):
                        return await fallback_func(*args, **kwargs)
                    else:
                        return fallback_func(*args, **kwargs)
                except Exception as fallback_error:
                    app_logger.error(f"Fallback function also failed: {str(fallback_error)}")
                    # Raise original error, not fallback error
                    raise e
        
        @wraps(primary_func)
        def sync_wrapper(*args, **kwargs):
            try:
                return primary_func(*args, **kwargs)
            except Exception as e:
                app_logger.warning(f"Primary function {primary_func.__name__} failed, using fallback: {str(e)}")
                
                try:
                    return fallback_func(*args, **kwargs)
                except Exception as fallback_error:
                    app_logger.error(f"Fallback function also failed: {str(fallback_error)}")
                    # Raise original error, not fallback error
                    raise e
        
        if asyncio.iscoroutinefunction(primary_func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Global recovery manager instance
recovery_manager = OCRRecoveryManager()

# Register default circuit breakers
recovery_manager.register_circuit_breaker("mistral_api", CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=30.0,
    success_threshold=2,
    timeout=60.0
))

recovery_manager.register_circuit_breaker("url_download", CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=10.0,
    success_threshold=3,
    timeout=30.0
))
