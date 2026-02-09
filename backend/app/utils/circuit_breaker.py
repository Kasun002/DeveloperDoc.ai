"""
Circuit breaker pattern implementation for database connections.

This module provides a circuit breaker to prevent cascading failures when
database connections fail repeatedly. The circuit breaker has three states:
- CLOSED: Normal operation, requests pass through
- OPEN: Too many failures, requests fail immediately
- HALF_OPEN: Testing if service recovered, limited requests pass through
"""

import asyncio
import time
from enum import Enum
from typing import Callable, Optional


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.
    
    The circuit breaker monitors failures and opens the circuit when
    a failure threshold is reached. After a timeout, it enters half-open
    state to test if the service has recovered.
    
    Attributes:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before testing recovery
        expected_exception: Exception type to catch (default: Exception)
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """
        Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of consecutive failures before opening (default: 5)
            recovery_timeout: Seconds before attempting recovery (default: 60)
            expected_exception: Exception type to monitor (default: Exception)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = CircuitState.CLOSED
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
    
    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count
    
    async def call(self, func: Callable, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func execution
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from func if circuit allows
            
        Example:
            >>> breaker = CircuitBreaker(failure_threshold=3)
            >>> result = await breaker.call(database_query, "SELECT 1")
        """
        async with self._lock:
            # Check if circuit should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._failure_count = 0
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is OPEN. "
                        f"Retry after {self._time_until_retry():.1f} seconds"
                    )
        
        # Execute the function
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset circuit if in HALF_OPEN state
            async with self._lock:
                if self._state == CircuitState.HALF_OPEN:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._last_failure_time = None
            
            return result
            
        except self.expected_exception as e:
            # Failure - increment counter and potentially open circuit
            async with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.time()
                
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker opened after {self._failure_count} failures"
                    ) from e
            
            raise
    
    def _should_attempt_reset(self) -> bool:
        """
        Check if enough time has passed to attempt recovery.
        
        Returns:
            bool: True if should attempt reset
        """
        if self._last_failure_time is None:
            return True
        
        return (time.time() - self._last_failure_time) >= self.recovery_timeout
    
    def _time_until_retry(self) -> float:
        """
        Calculate time remaining until retry attempt.
        
        Returns:
            float: Seconds until retry
        """
        if self._last_failure_time is None:
            return 0.0
        
        elapsed = time.time() - self._last_failure_time
        remaining = self.recovery_timeout - elapsed
        return max(0.0, remaining)
    
    async def reset(self):
        """
        Manually reset the circuit breaker to CLOSED state.
        
        This can be used for administrative purposes or testing.
        """
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
    
    def get_status(self) -> dict:
        """
        Get current circuit breaker status.
        
        Returns:
            dict: Status information including state and failure count
        """
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "time_until_retry": self._time_until_retry() if self._state == CircuitState.OPEN else 0.0
        }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass
