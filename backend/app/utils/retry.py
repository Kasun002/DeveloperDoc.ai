"""
Retry utilities with exponential backoff.

This module provides reusable retry decorators and utilities for handling
transient failures with exponential backoff. It uses the tenacity library
to implement configurable retry strategies.
"""

import logging
from functools import wraps
from typing import Callable, Optional, Tuple, Type

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    after_log,
    RetryCallState
)

from app.core.config import settings

logger = logging.getLogger(__name__)


def create_retry_decorator(
    max_attempts: int = 3,
    multiplier: int = 1,
    min_wait: int = 1,
    max_wait: int = 10,
    retry_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    logger_instance: Optional[logging.Logger] = None
):
    """
    Create a retry decorator with exponential backoff.
    
    This factory function creates a retry decorator with configurable parameters
    for exponential backoff. The decorator will retry the function on specified
    exceptions with increasing delays between attempts.
    
    Backoff formula: wait = min(max_wait, multiplier * (2 ** (attempt - 1)))
    Example with multiplier=1, min=1, max=10:
    - Attempt 1: immediate
    - Attempt 2: wait 1s
    - Attempt 3: wait 2s
    - Attempt 4: wait 4s (if max_attempts > 3)
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        multiplier: Multiplier for exponential backoff (default: 1)
        min_wait: Minimum wait time in seconds (default: 1)
        max_wait: Maximum wait time in seconds (default: 10)
        retry_exceptions: Tuple of exception types to retry on (default: Exception)
        logger_instance: Logger to use for retry logging (default: module logger)
        
    Returns:
        Callable: Retry decorator function
        
    Example:
        >>> @create_retry_decorator(max_attempts=3, retry_exceptions=(ConnectionError,))
        ... async def fetch_data():
        ...     # Function that might fail with ConnectionError
        ...     pass
    """
    if retry_exceptions is None:
        retry_exceptions = (Exception,)
    
    if logger_instance is None:
        logger_instance = logger
    
    return retry(
        retry=retry_if_exception_type(retry_exceptions),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
        before_sleep=before_sleep_log(logger_instance, logging.WARNING),
        after=after_log(logger_instance, logging.INFO),
        reraise=True
    )


def mcp_tool_retry(func: Optional[Callable] = None):
    """
    Decorator for MCP tool calls with standard retry configuration.
    
    Applies retry logic specifically configured for MCP tool calls:
    - Maximum 3 attempts (initial + 2 retries)
    - Exponential backoff: 1s, 2s, 4s
    - Retries on network and timeout errors
    
    This decorator uses the configuration from settings for consistency
    across all MCP tool calls.
    
    Args:
        func: Function to decorate (can be used with or without parentheses)
        
    Returns:
        Callable: Decorated function with retry logic
        
    Example:
        >>> @mcp_tool_retry
        ... async def call_search_tool(query: str):
        ...     # MCP tool call that might fail
        ...     pass
        
        >>> # Or with explicit call
        >>> @mcp_tool_retry()
        ... async def call_search_tool(query: str):
        ...     pass
    """
    # Import here to avoid circular dependency
    from app.services.mcp_client import MCPConnectionError
    import httpx
    
    retry_decorator = create_retry_decorator(
        max_attempts=settings.mcp_tool_retry_attempts,
        multiplier=settings.mcp_tool_retry_backoff_multiplier,
        min_wait=settings.mcp_tool_retry_min_wait,
        max_wait=settings.mcp_tool_retry_max_wait,
        retry_exceptions=(
            httpx.TimeoutException,
            httpx.NetworkError,
            MCPConnectionError
        )
    )
    
    if func is None:
        # Called with parentheses: @mcp_tool_retry()
        return retry_decorator
    else:
        # Called without parentheses: @mcp_tool_retry
        return retry_decorator(func)


def database_retry(func: Optional[Callable] = None):
    """
    Decorator for database operations with standard retry configuration.
    
    Applies retry logic specifically configured for database operations:
    - Maximum 3 attempts
    - Exponential backoff: 1s, 2s, 4s
    - Retries on connection and operational errors
    
    Args:
        func: Function to decorate (can be used with or without parentheses)
        
    Returns:
        Callable: Decorated function with retry logic
        
    Example:
        >>> @database_retry
        ... async def query_database(query: str):
        ...     # Database query that might fail
        ...     pass
    """
    import asyncpg
    
    retry_decorator = create_retry_decorator(
        max_attempts=3,
        multiplier=1,
        min_wait=1,
        max_wait=10,
        retry_exceptions=(
            asyncpg.PostgresConnectionError,
            asyncpg.ConnectionDoesNotExistError,
            asyncpg.TooManyConnectionsError
        )
    )
    
    if func is None:
        return retry_decorator
    else:
        return retry_decorator(func)


def llm_api_retry(func: Optional[Callable] = None):
    """
    Decorator for LLM API calls with standard retry configuration.
    
    Applies retry logic specifically configured for LLM API calls:
    - Maximum 3 attempts
    - Exponential backoff: 1s, 2s, 4s
    - Retries on rate limit and timeout errors
    
    Args:
        func: Function to decorate (can be used with or without parentheses)
        
    Returns:
        Callable: Decorated function with retry logic
        
    Example:
        >>> @llm_api_retry
        ... async def call_openai(prompt: str):
        ...     # OpenAI API call that might fail
        ...     pass
    """
    import openai
    import httpx
    
    retry_decorator = create_retry_decorator(
        max_attempts=3,
        multiplier=1,
        min_wait=1,
        max_wait=10,
        retry_exceptions=(
            openai.RateLimitError,
            openai.APITimeoutError,
            openai.APIConnectionError,
            httpx.TimeoutException,
            httpx.NetworkError
        )
    )
    
    if func is None:
        return retry_decorator
    else:
        return retry_decorator(func)


class RetryExhaustedError(Exception):
    """
    Exception raised when all retry attempts are exhausted.
    
    This exception provides detailed information about the retry attempts
    and the final error that caused the failure.
    """
    
    def __init__(
        self,
        message: str,
        attempts: int,
        last_exception: Exception
    ):
        """
        Initialize RetryExhaustedError.
        
        Args:
            message: Error message
            attempts: Number of attempts made
            last_exception: The final exception that caused the failure
        """
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(f"{message} (after {attempts} attempts): {str(last_exception)}")


def get_retry_state_info(retry_state: RetryCallState) -> dict:
    """
    Extract information from a retry state for logging.
    
    Args:
        retry_state: Tenacity retry state object
        
    Returns:
        dict: Retry state information including attempt number and outcome
    """
    return {
        "attempt_number": retry_state.attempt_number,
        "idle_for": retry_state.idle_for,
        "next_action": str(retry_state.next_action) if retry_state.next_action else None,
        "outcome_failed": retry_state.outcome.failed if retry_state.outcome else None,
        "seconds_since_start": retry_state.seconds_since_start
    }


# Example usage and testing utilities
async def test_retry_behavior():
    """
    Test function to demonstrate retry behavior.
    
    This function can be used to verify that retry logic works correctly
    with different failure scenarios.
    """
    attempt_count = 0
    
    @create_retry_decorator(max_attempts=3, retry_exceptions=(ValueError,))
    async def failing_function():
        nonlocal attempt_count
        attempt_count += 1
        logger.info(f"Attempt {attempt_count}")
        
        if attempt_count < 3:
            raise ValueError(f"Attempt {attempt_count} failed")
        
        return "Success"
    
    try:
        result = await failing_function()
        logger.info(f"Function succeeded: {result}")
        return result
    except ValueError as e:
        logger.error(f"All retries exhausted: {e}")
        raise


if __name__ == "__main__":
    """
    Run retry behavior test when module is executed directly.
    """
    import asyncio
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(test_retry_behavior())
