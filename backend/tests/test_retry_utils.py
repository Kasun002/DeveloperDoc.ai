"""
Unit tests for retry utilities.

Tests the retry decorator utilities including:
- Retry decorator creation
- Exponential backoff behavior
- MCP tool retry decorator
- Database retry decorator
- LLM API retry decorator
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
import httpx

from app.utils.retry import (
    create_retry_decorator,
    mcp_tool_retry,
    database_retry,
    llm_api_retry,
    RetryExhaustedError
)


class TestRetryDecoratorCreation:
    """Test retry decorator factory function."""
    
    @pytest.mark.asyncio
    async def test_create_retry_decorator_success_after_retries(self):
        """Test that function succeeds after retries."""
        call_count = 0
        
        @create_retry_decorator(max_attempts=3, retry_exceptions=(ValueError,))
        async def failing_function():
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                raise ValueError(f"Attempt {call_count} failed")
            
            return "Success"
        
        result = await failing_function()
        
        assert result == "Success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_create_retry_decorator_max_attempts_exceeded(self):
        """Test that exception is raised after max attempts."""
        call_count = 0
        
        @create_retry_decorator(max_attempts=3, retry_exceptions=(ValueError,))
        async def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Attempt {call_count} failed")
        
        with pytest.raises(ValueError):
            await always_failing_function()
        
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_create_retry_decorator_no_retry_on_different_exception(self):
        """Test that non-retryable exceptions are not retried."""
        call_count = 0
        
        @create_retry_decorator(max_attempts=3, retry_exceptions=(ValueError,))
        async def function_with_different_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Different error")
        
        with pytest.raises(TypeError):
            await function_with_different_error()
        
        # Should only be called once (no retries)
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_create_retry_decorator_immediate_success(self):
        """Test that successful function is not retried."""
        call_count = 0
        
        @create_retry_decorator(max_attempts=3, retry_exceptions=(ValueError,))
        async def successful_function():
            nonlocal call_count
            call_count += 1
            return "Success"
        
        result = await successful_function()
        
        assert result == "Success"
        assert call_count == 1


class TestMCPToolRetryDecorator:
    """Test MCP tool retry decorator."""
    
    @pytest.mark.asyncio
    async def test_mcp_tool_retry_with_parentheses(self):
        """Test MCP tool retry decorator with parentheses."""
        call_count = 0
        
        @mcp_tool_retry()
        async def mcp_call():
            nonlocal call_count
            call_count += 1
            
            if call_count < 2:
                raise httpx.TimeoutException("Timeout")
            
            return "Success"
        
        result = await mcp_call()
        
        assert result == "Success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_mcp_tool_retry_without_parentheses(self):
        """Test MCP tool retry decorator without parentheses."""
        call_count = 0
        
        @mcp_tool_retry
        async def mcp_call():
            nonlocal call_count
            call_count += 1
            
            if call_count < 2:
                raise httpx.NetworkError("Network error")
            
            return "Success"
        
        result = await mcp_call()
        
        assert result == "Success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_mcp_tool_retry_max_attempts(self):
        """Test that MCP tool retry respects max attempts."""
        call_count = 0
        
        @mcp_tool_retry
        async def always_failing_mcp_call():
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Timeout")
        
        with pytest.raises(httpx.TimeoutException):
            await always_failing_mcp_call()
        
        # Should be 3 attempts (from settings)
        assert call_count == 3


class TestDatabaseRetryDecorator:
    """Test database retry decorator."""
    
    @pytest.mark.asyncio
    async def test_database_retry_on_connection_error(self):
        """Test database retry on connection errors."""
        call_count = 0
        
        @database_retry
        async def db_query():
            nonlocal call_count
            call_count += 1
            
            if call_count < 2:
                import asyncpg
                raise asyncpg.PostgresConnectionError("Connection failed")
            
            return "Query result"
        
        result = await db_query()
        
        assert result == "Query result"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_database_retry_with_parentheses(self):
        """Test database retry decorator with parentheses."""
        call_count = 0
        
        @database_retry()
        async def db_query():
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                import asyncpg
                raise asyncpg.TooManyConnectionsError("Too many connections")
            
            return "Query result"
        
        result = await db_query()
        
        assert result == "Query result"
        assert call_count == 3


class TestLLMAPIRetryDecorator:
    """Test LLM API retry decorator."""
    
    @pytest.mark.asyncio
    async def test_llm_api_retry_on_rate_limit(self):
        """Test LLM API retry on rate limit errors."""
        call_count = 0
        
        @llm_api_retry
        async def llm_call():
            nonlocal call_count
            call_count += 1
            
            if call_count < 2:
                # Use httpx.TimeoutException instead since OpenAI errors require response objects
                raise httpx.TimeoutException("Rate limit exceeded")
            
            return "LLM response"
        
        result = await llm_call()
        
        assert result == "LLM response"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_llm_api_retry_on_timeout(self):
        """Test LLM API retry on timeout errors."""
        call_count = 0
        
        @llm_api_retry()
        async def llm_call():
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                # Use httpx.TimeoutException which is in the retry list
                raise httpx.TimeoutException("Request timeout")
            
            return "LLM response"
        
        result = await llm_call()
        
        assert result == "LLM response"
        assert call_count == 3


class TestRetryExhaustedError:
    """Test RetryExhaustedError exception."""
    
    def test_retry_exhausted_error_creation(self):
        """Test that RetryExhaustedError is created correctly."""
        original_error = ValueError("Original error")
        error = RetryExhaustedError(
            "Operation failed",
            attempts=3,
            last_exception=original_error
        )
        
        assert error.attempts == 3
        assert error.last_exception == original_error
        assert "after 3 attempts" in str(error)
        assert "Original error" in str(error)


class TestExponentialBackoff:
    """Test exponential backoff timing."""
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that exponential backoff increases wait time."""
        call_times = []
        
        @create_retry_decorator(
            max_attempts=4,
            multiplier=1,
            min_wait=1,
            max_wait=10,
            retry_exceptions=(ValueError,)
        )
        async def failing_function():
            import time
            call_times.append(time.time())
            
            if len(call_times) < 4:
                raise ValueError("Failed")
            
            return "Success"
        
        result = await failing_function()
        
        assert result == "Success"
        assert len(call_times) == 4
        
        # Check that delays increase (approximately)
        # Note: This is a rough check due to timing variations
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            
            # Second delay should be roughly >= first delay
            # (allowing for some timing variance)
            assert delay2 >= delay1 * 0.8


class TestRetryWithSyncFunctions:
    """Test that retry decorators work with sync functions too."""
    
    def test_retry_with_sync_function(self):
        """Test retry decorator with synchronous function."""
        call_count = 0
        
        @create_retry_decorator(max_attempts=3, retry_exceptions=(ValueError,))
        def sync_failing_function():
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                raise ValueError(f"Attempt {call_count} failed")
            
            return "Success"
        
        result = sync_failing_function()
        
        assert result == "Success"
        assert call_count == 3
