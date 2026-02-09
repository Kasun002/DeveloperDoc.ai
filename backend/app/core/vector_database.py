"""
Vector Database connection manager using AsyncPG for pgvector operations.

This module provides async database connection management for the AI Agent System's
vector database operations. It includes connection pooling, retry logic, and health checks.
"""

import asyncio
import logging
from typing import Optional

import asyncpg
from app.core.config import settings
from app.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class VectorDatabaseManager:
    """
    Manages AsyncPG connection pool for vector database operations.
    
    This class provides connection pooling, automatic reconnection, and health checks
    for the pgvector database used by the AI Agent System.
    
    Attributes:
        pool: AsyncPG connection pool
        _connection_url: Database connection URL
    """
    
    def __init__(self, connection_url: Optional[str] = None):
        """
        Initialize the Vector Database Manager.
        
        Args:
            connection_url: PostgreSQL connection URL. If None, uses VECTOR_DATABASE_URL from settings.
        """
        self.pool: Optional[asyncpg.Pool] = None
        self._connection_url = connection_url or settings.vector_database_url
        
        # Initialize circuit breaker for connection failures
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,  # Open circuit after 5 consecutive failures
            recovery_timeout=60.0,  # Wait 60 seconds before attempting recovery
            expected_exception=(
                asyncpg.PostgresConnectionError,
                asyncpg.CannotConnectNowError,
                ConnectionError,
                OSError
            )
        )
        
    async def connect(self) -> None:
        """
        Create connection pool with retry logic and circuit breaker protection.
        
        Establishes a connection pool to the vector database with automatic retry
        on connection failures. Uses exponential backoff for retries and circuit
        breaker to prevent cascading failures.
        
        Raises:
            ConnectionError: If unable to connect after all retry attempts
            CircuitBreakerOpenError: If circuit breaker is open
        """
        if self.pool is not None:
            return
            
        @retry(
            retry=retry_if_exception_type((
                asyncpg.PostgresConnectionError,
                asyncpg.CannotConnectNowError,
                OSError
            )),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True
        )
        async def _create_pool():
            return await asyncpg.create_pool(
                self._connection_url,
                min_size=2,  # Minimum connections in pool
                max_size=10,  # Maximum connections in pool
                max_queries=50000,  # Max queries per connection before recycling
                max_inactive_connection_lifetime=300,  # 5 minutes
                command_timeout=60,  # Command timeout in seconds
            )
        
        try:
            # Use circuit breaker to protect against repeated connection failures
            self.pool = await self._circuit_breaker.call(_create_pool)
            logger.info("Successfully connected to vector database")
        except CircuitBreakerOpenError as e:
            logger.error(f"Circuit breaker is open, cannot connect: {str(e)}")
            raise ConnectionError(f"Circuit breaker open: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to connect to vector database: {str(e)}", exc_info=True)
            raise ConnectionError(f"Failed to connect to vector database: {str(e)}")
    
    async def disconnect(self) -> None:
        """
        Close the connection pool gracefully.
        
        Closes all connections in the pool and releases resources.
        """
        if self.pool is not None:
            await self.pool.close()
            self.pool = None
    
    async def health_check(self) -> dict:
        """
        Perform health check on the database connection.
        
        Verifies that the database is accessible and pgvector extension is available.
        
        Returns:
            dict: Health check results with status and details
            
        Example:
            {
                "status": "healthy",
                "pool_size": 5,
                "pool_free": 3,
                "pgvector_available": True
            }
        """
        if self.pool is None:
            return {
                "status": "disconnected",
                "error": "Connection pool not initialized"
            }
        
        try:
            async with self.pool.acquire() as conn:
                # Test basic connectivity
                await conn.fetchval("SELECT 1")
                
                # Check pgvector extension
                pgvector_check = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )
                
                # Get pool statistics
                pool_size = self.pool.get_size()
                pool_free = self.pool.get_idle_size()
                
                return {
                    "status": "healthy",
                    "pool_size": pool_size,
                    "pool_free": pool_free,
                    "pgvector_available": bool(pgvector_check)
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def reconnect(self) -> None:
        """
        Reconnect to the database with circuit breaker protection.
        
        Closes existing connection pool and creates a new one.
        Useful for recovering from connection failures. Respects
        circuit breaker state to prevent cascading failures.
        
        Raises:
            ConnectionError: If reconnection fails
            CircuitBreakerOpenError: If circuit breaker is open
        """
        logger.info("Attempting to reconnect to vector database")
        await self.disconnect()
        await self.connect()
        logger.info("Successfully reconnected to vector database")
    
    async def acquire(self):
        """
        Acquire a connection from the pool.
        
        Returns:
            asyncpg.Connection: Database connection
            
        Raises:
            ConnectionError: If pool is not initialized
        """
        if self.pool is None:
            raise ConnectionError("Connection pool not initialized. Call connect() first.")
        return self.pool.acquire()
    
    async def execute(self, query: str, *args, timeout: Optional[float] = None):
        """
        Execute a query with automatic retry on connection failure.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            timeout: Query timeout in seconds
            
        Returns:
            Query result
            
        Raises:
            ConnectionError: If unable to execute after retry attempts
            CircuitBreakerOpenError: If circuit breaker is open
        """
        @retry(
            retry=retry_if_exception_type((
                asyncpg.PostgresConnectionError,
                asyncpg.ConnectionDoesNotExistError
            )),
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=1, min=1, max=5),
            reraise=True
        )
        async def _execute_with_retry():
            async with self.pool.acquire() as conn:
                return await conn.execute(query, *args, timeout=timeout)
        
        try:
            return await _execute_with_retry()
        except (asyncpg.PostgresConnectionError, asyncpg.ConnectionDoesNotExistError) as e:
            # Attempt reconnection on connection failure
            logger.warning(f"Connection error during execute, attempting reconnect: {str(e)}")
            try:
                await self.reconnect()
                # Retry once after reconnection
                async with self.pool.acquire() as conn:
                    return await conn.execute(query, *args, timeout=timeout)
            except Exception as reconnect_error:
                logger.error(f"Reconnection failed: {str(reconnect_error)}", exc_info=True)
                raise ConnectionError(f"Database operation failed after reconnection attempt: {str(reconnect_error)}")
    
    async def fetch(self, query: str, *args, timeout: Optional[float] = None):
        """
        Fetch multiple rows with automatic retry on connection failure.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            timeout: Query timeout in seconds
            
        Returns:
            List of records
            
        Raises:
            ConnectionError: If unable to execute after retry attempts
            CircuitBreakerOpenError: If circuit breaker is open
        """
        @retry(
            retry=retry_if_exception_type((
                asyncpg.PostgresConnectionError,
                asyncpg.ConnectionDoesNotExistError
            )),
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=1, min=1, max=5),
            reraise=True
        )
        async def _fetch_with_retry():
            async with self.pool.acquire() as conn:
                return await conn.fetch(query, *args, timeout=timeout)
        
        try:
            return await _fetch_with_retry()
        except (asyncpg.PostgresConnectionError, asyncpg.ConnectionDoesNotExistError) as e:
            # Attempt reconnection on connection failure
            logger.warning(f"Connection error during fetch, attempting reconnect: {str(e)}")
            try:
                await self.reconnect()
                # Retry once after reconnection
                async with self.pool.acquire() as conn:
                    return await conn.fetch(query, *args, timeout=timeout)
            except Exception as reconnect_error:
                logger.error(f"Reconnection failed: {str(reconnect_error)}", exc_info=True)
                raise ConnectionError(f"Database operation failed after reconnection attempt: {str(reconnect_error)}")
    
    async def fetchrow(self, query: str, *args, timeout: Optional[float] = None):
        """
        Fetch a single row with automatic retry on connection failure.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            timeout: Query timeout in seconds
            
        Returns:
            Single record or None
            
        Raises:
            ConnectionError: If unable to execute after retry attempts
            CircuitBreakerOpenError: If circuit breaker is open
        """
        @retry(
            retry=retry_if_exception_type((
                asyncpg.PostgresConnectionError,
                asyncpg.ConnectionDoesNotExistError
            )),
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=1, min=1, max=5),
            reraise=True
        )
        async def _fetchrow_with_retry():
            async with self.pool.acquire() as conn:
                return await conn.fetchrow(query, *args, timeout=timeout)
        
        try:
            return await _fetchrow_with_retry()
        except (asyncpg.PostgresConnectionError, asyncpg.ConnectionDoesNotExistError) as e:
            # Attempt reconnection on connection failure
            logger.warning(f"Connection error during fetchrow, attempting reconnect: {str(e)}")
            try:
                await self.reconnect()
                # Retry once after reconnection
                async with self.pool.acquire() as conn:
                    return await conn.fetchrow(query, *args, timeout=timeout)
            except Exception as reconnect_error:
                logger.error(f"Reconnection failed: {str(reconnect_error)}", exc_info=True)
                raise ConnectionError(f"Database operation failed after reconnection attempt: {str(reconnect_error)}")
    
    async def fetchval(self, query: str, *args, timeout: Optional[float] = None):
        """
        Fetch a single value with automatic retry on connection failure.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            timeout: Query timeout in seconds
            
        Returns:
            Single value or None
            
        Raises:
            ConnectionError: If unable to execute after retry attempts
            CircuitBreakerOpenError: If circuit breaker is open
        """
        @retry(
            retry=retry_if_exception_type((
                asyncpg.PostgresConnectionError,
                asyncpg.ConnectionDoesNotExistError
            )),
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=1, min=1, max=5),
            reraise=True
        )
        async def _fetchval_with_retry():
            async with self.pool.acquire() as conn:
                return await conn.fetchval(query, *args, timeout=timeout)
        
        try:
            return await _fetchval_with_retry()
        except (asyncpg.PostgresConnectionError, asyncpg.ConnectionDoesNotExistError) as e:
            # Attempt reconnection on connection failure
            logger.warning(f"Connection error during fetchval, attempting reconnect: {str(e)}")
            try:
                await self.reconnect()
                # Retry once after reconnection
                async with self.pool.acquire() as conn:
                    return await conn.fetchval(query, *args, timeout=timeout)
            except Exception as reconnect_error:
                logger.error(f"Reconnection failed: {str(reconnect_error)}", exc_info=True)
                raise ConnectionError(f"Database operation failed after reconnection attempt: {str(reconnect_error)}")
    
    def get_circuit_breaker_status(self) -> dict:
        """
        Get circuit breaker status for monitoring.
        
        Returns:
            dict: Circuit breaker status including state and failure count
        """
        return self._circuit_breaker.get_status()


# Global vector database manager instance
vector_db_manager = VectorDatabaseManager()


async def get_vector_db() -> VectorDatabaseManager:
    """
    Dependency injection function for FastAPI endpoints.
    
    Returns:
        VectorDatabaseManager: Global vector database manager instance
    """
    if vector_db_manager.pool is None:
        await vector_db_manager.connect()
    return vector_db_manager
