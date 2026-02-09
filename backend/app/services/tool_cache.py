"""
Tool cache implementation for MCP tool results.

This module provides caching functionality for expensive MCP tool call results.
Uses Redis for fast key-value storage with short TTL (5-10 minutes) to cache
tool results and avoid redundant expensive operations. All cache operations
implement graceful degradation to ensure system continues functioning even if cache fails.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.config import settings
from redis import asyncio as aioredis

logger = logging.getLogger(__name__)


class ToolCache:
    """
    Cache for MCP tool call results.
    
    This cache stores results from expensive MCP tool calls with a short TTL
    (5-10 minutes) to avoid redundant operations. Cache keys are generated
    deterministically from tool name and parameters.
    
    Attributes:
        redis_client: Async Redis client for key-value storage
        default_ttl: Default time-to-live in seconds (default: 300 = 5 minutes)
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 300
    ):
        """
        Initialize the Tool Cache.
        
        Args:
            redis_url: Redis connection URL. If None, uses settings.redis_url
            default_ttl: Default TTL in seconds (default: 300 = 5 minutes)
        """
        self.redis_url = redis_url or settings.redis_url
        self.default_ttl = default_ttl
        self.redis_client: Optional[aioredis.Redis] = None
    
    async def connect(self):
        """
        Establish connection to Redis.
        
        This method should be called before using the cache.
        Typically called during application startup.
        
        Raises:
            ConnectionError: If connection to Redis fails
        """
        try:
            # Connect to Redis
            self.redis_client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test Redis connection
            await self.redis_client.ping()
            logger.info("Successfully connected to Redis for tool cache")
            
        except Exception as e:
            logger.error(
                f"Failed to connect to Redis for tool cache: {str(e)}",
                exc_info=True
            )
            raise ConnectionError(f"Failed to connect to Redis: {str(e)}")
    
    async def disconnect(self):
        """
        Close connection to Redis.
        
        This method should be called during application shutdown.
        """
        try:
            if self.redis_client:
                await self.redis_client.close()
                logger.info("Closed Redis connection for tool cache")
        except Exception as e:
            logger.warning(f"Error closing Redis connection for tool cache: {str(e)}")
    
    def generate_cache_key(self, tool_name: str, params: Dict[str, Any]) -> str:
        """
        Generate deterministic cache key from tool name and params.
        
        Creates a hash from the tool name and sorted parameters to ensure
        identical calls produce the same cache key.
        
        Args:
            tool_name: Name of the MCP tool
            params: Tool parameters dictionary
            
        Returns:
            str: Cache key (hash string)
            
        Example:
            >>> cache = ToolCache()
            >>> key = cache.generate_cache_key(
            ...     "search_framework_docs",
            ...     {"query": "NestJS controller", "top_k": 10}
            ... )
            >>> key
            'tool_cache:search_framework_docs:a3f5b2c1...'
        """
        # Sort params to ensure consistent ordering
        sorted_params = json.dumps(params, sort_keys=True)
        
        # Create hash from tool name + params
        cache_input = f"{tool_name}:{sorted_params}"
        params_hash = hashlib.sha256(cache_input.encode()).hexdigest()[:16]
        
        return f"tool_cache:{tool_name}:{params_hash}"
    
    async def get(self, cache_key: str) -> Optional[Any]:
        """
        Retrieve cached tool result.
        
        Implements graceful degradation - cache failures don't break requests.
        
        Args:
            cache_key: Cache key (from generate_cache_key)
            
        Returns:
            Optional[Any]: Cached result if found and not expired, None otherwise
            
        Note:
            This method implements graceful degradation. If cache operations fail,
            it logs the error and returns None, allowing the request to proceed
            without caching.
            
        Example:
            >>> cache = ToolCache()
            >>> await cache.connect()
            >>> key = cache.generate_cache_key("search_docs", {"query": "test"})
            >>> result = await cache.get(key)
            >>> if result:
            ...     print("Cache hit!")
        """
        if not self.redis_client:
            logger.warning("Tool cache not connected, skipping cache lookup")
            return None
        
        try:
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                logger.info(f"Tool cache hit for key: {cache_key}")
                return data["result"]
            
            logger.debug(f"Tool cache miss for key: {cache_key}")
            return None
            
        except Exception as e:
            # Graceful degradation: log error but don't fail
            logger.warning(
                f"Tool cache get operation failed, continuing without cache: {str(e)}",
                exc_info=True
            )
            return None
    
    async def get_with_metadata(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached tool result with metadata.
        
        Returns the cached result along with metadata like cached_at timestamp
        and TTL information. Implements graceful degradation.
        
        Args:
            cache_key: Cache key (from generate_cache_key)
            
        Returns:
            Optional[Dict]: Dictionary with 'result', 'cached_at', 'ttl' keys
            
        Note:
            This method implements graceful degradation. If cache operations fail,
            it logs the error and returns None.
            
        Example:
            >>> cache = ToolCache()
            >>> await cache.connect()
            >>> key = cache.generate_cache_key("search_docs", {"query": "test"})
            >>> data = await cache.get_with_metadata(key)
            >>> if data:
            ...     print(f"Cached at: {data['cached_at']}")
            ...     print(f"Result: {data['result']}")
        """
        if not self.redis_client:
            logger.warning("Tool cache not connected, skipping cache lookup")
            return None
        
        try:
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                logger.info(f"Tool cache hit (with metadata) for key: {cache_key}")
                return json.loads(cached_data)
            
            logger.debug(f"Tool cache miss for key: {cache_key}")
            return None
            
        except Exception as e:
            # Graceful degradation
            logger.warning(
                f"Tool cache get_with_metadata operation failed, continuing without cache: {str(e)}",
                exc_info=True
            )
            return None
    
    async def set(
        self,
        cache_key: str,
        result: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store tool result with TTL.
        
        Stores the tool result in Redis with the specified TTL. After the TTL
        expires, the cached entry is automatically removed by Redis.
        Implements graceful degradation - cache failures don't break requests.
        
        Args:
            cache_key: Cache key (from generate_cache_key)
            result: Tool result to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (default: self.default_ttl)
            
        Returns:
            bool: True if successful, False otherwise
            
        Note:
            This method implements graceful degradation. If cache operations fail,
            it logs the error and returns False, allowing the request to proceed
            without caching.
            
        Example:
            >>> cache = ToolCache()
            >>> await cache.connect()
            >>> key = cache.generate_cache_key("search_docs", {"query": "test"})
            >>> result = [{"content": "...", "score": 0.9}]
            >>> success = await cache.set(key, result, ttl=600)  # 10 minutes
        """
        if not self.redis_client:
            logger.warning("Tool cache not connected, skipping cache storage")
            return False
        
        cache_ttl = ttl or self.default_ttl
        
        try:
            cache_data = {
                "result": result,
                "cached_at": datetime.utcnow().isoformat(),
                "ttl": cache_ttl
            }
            
            await self.redis_client.setex(
                cache_key,
                cache_ttl,
                json.dumps(cache_data)
            )
            
            logger.info(f"Successfully cached tool result for key: {cache_key}")
            return True
            
        except Exception as e:
            # Graceful degradation: log error but don't fail
            logger.warning(
                f"Tool cache set operation failed, continuing without caching: {str(e)}",
                exc_info=True
            )
            return False
    
    async def delete(self, cache_key: str) -> bool:
        """
        Delete a cached entry.
        
        Implements graceful degradation - failures are logged but don't break requests.
        
        Args:
            cache_key: Cache key to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.redis_client:
            logger.warning("Tool cache not connected, cannot delete entry")
            return False
        
        try:
            await self.redis_client.delete(cache_key)
            logger.info(f"Deleted tool cache entry: {cache_key}")
            return True
            
        except Exception as e:
            logger.warning(
                f"Tool cache delete operation failed: {str(e)}",
                exc_info=True
            )
            return False
    
    async def clear(self) -> bool:
        """
        Clear all cached tool results.
        
        Removes all entries with the tool_cache prefix.
        Useful for testing and maintenance. Implements graceful degradation.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.redis_client:
            logger.warning("Tool cache not connected, cannot clear cache")
            return False
        
        try:
            keys = await self.redis_client.keys("tool_cache:*")
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} entries from tool cache")
            
            return True
            
        except Exception as e:
            logger.warning(
                f"Tool cache clear operation failed: {str(e)}",
                exc_info=True
            )
            return False
    
    async def get_or_set(
        self,
        tool_name: str,
        params: Dict[str, Any],
        fetch_fn,
        ttl: Optional[int] = None
    ) -> Any:
        """
        Get cached result or fetch and cache if not found.
        
        This is a convenience method that combines get and set operations.
        If the result is cached, it returns immediately. Otherwise, it calls
        the fetch function, caches the result, and returns it.
        Implements graceful degradation - cache failures don't prevent fetching.
        
        Args:
            tool_name: Name of the MCP tool
            params: Tool parameters dictionary
            fetch_fn: Async function to call if cache miss (should return result)
            ttl: Time-to-live in seconds (default: self.default_ttl)
            
        Returns:
            Any: Cached or freshly fetched result
            
        Note:
            If cache operations fail, this method will still fetch and return
            the result, just without caching it.
            
        Example:
            >>> cache = ToolCache()
            >>> await cache.connect()
            >>> 
            >>> async def fetch_docs(query):
            ...     return await search_agent.search_docs(query)
            >>> 
            >>> result = await cache.get_or_set(
            ...     "search_framework_docs",
            ...     {"query": "NestJS controller", "top_k": 10},
            ...     lambda: fetch_docs("NestJS controller")
            ... )
        """
        if not self.redis_client:
            logger.warning("Tool cache not connected, fetching without cache")
            return await fetch_fn()
        
        # Generate cache key
        cache_key = self.generate_cache_key(tool_name, params)
        
        # Try to get from cache
        cached_result = await self.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Cache miss - fetch result
        try:
            result = await fetch_fn()
            
            # Cache the result (graceful degradation if caching fails)
            await self.set(cache_key, result, ttl)
            
            return result
            
        except Exception as e:
            # If fetch fails, re-raise the exception
            logger.error(f"Fetch function failed in get_or_set: {str(e)}", exc_info=True)
            raise


# Global tool cache instance
tool_cache = ToolCache()


async def get_tool_cache() -> ToolCache:
    """
    Dependency injection function for FastAPI endpoints.
    
    Returns:
        ToolCache: Global tool cache instance
    """
    return tool_cache
