"""
Semantic cache implementation using Redis and pgvector.

This module provides semantic caching functionality for the AI Agent System.
It uses Redis for fast key-value storage and pgvector for similarity-based
cache lookups with a 0.95 similarity threshold. All cache operations implement
graceful degradation to ensure system continues functioning even if cache fails.
"""

import hashlib
import json
from datetime import datetime
from typing import List, Optional

import asyncpg
from app.core.config import settings
from app.core.logging_config import get_logger
from pydantic import BaseModel
from redis import asyncio as aioredis

logger = get_logger(__name__)


class CachedResponse(BaseModel):
    """
    Model for cached response data.
    
    Attributes:
        response: The cached response text
        embedding: The embedding vector for similarity search
        similarity_score: Similarity score when retrieved from cache
        cached_at: Timestamp when response was cached
        ttl: Time-to-live in seconds
    """
    response: str
    embedding: List[float]
    similarity_score: float = 0.0
    cached_at: datetime
    ttl: int


class SemanticCache:
    """
    Semantic cache using Redis and pgvector for similarity-based lookups.
    
    This cache stores responses with their embeddings and performs similarity
    search to find cached responses for similar prompts. Uses a similarity
    threshold of 0.95 (cosine similarity) to determine cache hits.
    
    Attributes:
        redis_client: Async Redis client for key-value storage
        pg_pool: AsyncPG connection pool for pgvector similarity search
        similarity_threshold: Minimum similarity score for cache hits (default: 0.95)
        default_ttl: Default time-to-live in seconds (default: 3600 = 1 hour)
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        vector_db_url: Optional[str] = None,
        similarity_threshold: float = 0.95,
        default_ttl: int = 3600
    ):
        """
        Initialize the Semantic Cache.
        
        Args:
            redis_url: Redis connection URL. If None, uses settings.redis_url
            vector_db_url: PostgreSQL connection URL. If None, uses settings.vector_database_url
            similarity_threshold: Minimum similarity for cache hits (default: 0.95)
            default_ttl: Default TTL in seconds (default: 3600 = 1 hour)
        """
        self.redis_url = redis_url or settings.redis_url
        self.vector_db_url = vector_db_url or settings.vector_database_url
        self.similarity_threshold = similarity_threshold
        self.default_ttl = default_ttl
        self.redis_client: Optional[aioredis.Redis] = None
        self.pg_pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """
        Establish connections to Redis and PostgreSQL.
        
        This method should be called before using the cache.
        Typically called during application startup.
        
        Raises:
            ConnectionError: If connection to Redis or PostgreSQL fails
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
            logger.info(
                "redis_connection_successful",
                service="semantic_cache",
                redis_host=settings.redis_host
            )
            
            # Connect to PostgreSQL with pgvector
            self.pg_pool = await asyncpg.create_pool(
                self.vector_db_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info(
                "postgresql_connection_successful",
                service="semantic_cache",
                pool_min_size=2,
                pool_max_size=10
            )
            
        except Exception as e:
            logger.error(
                "cache_backend_connection_failed",
                service="semantic_cache",
                error=str(e),
                exc_info=True
            )
            raise ConnectionError(f"Failed to connect to cache backends: {str(e)}")
    
    async def disconnect(self):
        """
        Close connections to Redis and PostgreSQL.
        
        This method should be called during application shutdown.
        """
        try:
            if self.redis_client:
                await self.redis_client.close()
                logger.info("connection_closed", service="semantic_cache", backend="redis")
        except Exception as e:
            logger.warning("connection_close_error", service="semantic_cache", backend="redis", error=str(e))
        
        try:
            if self.pg_pool:
                await self.pg_pool.close()
                logger.info("connection_closed", service="semantic_cache", backend="postgresql")
        except Exception as e:
            logger.warning("connection_close_error", service="semantic_cache", backend="postgresql", error=str(e))
    
    def _generate_cache_key(self, prompt: str) -> str:
        """
        Generate a deterministic cache key from prompt.
        
        Args:
            prompt: User prompt text
            
        Returns:
            str: Cache key (hash of prompt)
        """
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        return f"semantic_cache:{prompt_hash}"
    
    async def get(
        self,
        prompt: str,
        similarity_threshold: Optional[float] = None
    ) -> Optional[CachedResponse]:
        """
        Retrieve cached response if similar prompt exists.
        
        Performs similarity search using pgvector to find cached responses
        with similarity above the threshold. Returns None if no match found.
        Implements graceful degradation - cache failures don't break requests.
        
        Args:
            prompt: User prompt to search for
            similarity_threshold: Override default similarity threshold
            
        Returns:
            Optional[CachedResponse]: Cached response if found, None otherwise
            
        Note:
            This method implements graceful degradation. If cache operations fail,
            it logs the error and returns None, allowing the request to proceed
            without caching.
            
        Example:
            >>> cache = SemanticCache()
            >>> await cache.connect()
            >>> result = await cache.get("How to create a NestJS controller?")
            >>> if result:
            ...     print(f"Cache hit with similarity {result.similarity_score}")
        """
        if not self.redis_client or not self.pg_pool:
            logger.warning("cache_not_connected", operation="get", service="semantic_cache")
            return None
        
        threshold = similarity_threshold or self.similarity_threshold
        
        try:
            # First, try exact match in Redis for fast lookup
            cache_key = self._generate_cache_key(prompt)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                logger.info(
                    "cache_hit",
                    match_type="exact",
                    service="semantic_cache",
                    prompt_preview=prompt[:50],
                    similarity_score=1.0
                )
                return CachedResponse(
                    response=data["response"],
                    embedding=data["embedding"],
                    similarity_score=1.0,  # Exact match
                    cached_at=datetime.fromisoformat(data["cached_at"]),
                    ttl=data["ttl"]
                )
            
            # If no exact match, perform similarity search
            # Note: This requires the embedding to be passed or generated
            # For now, return None as similarity search requires embedding
            # This will be enhanced when integrated with embedding service
            logger.debug(f"Cache miss for prompt: {prompt[:50]}...")
            return None
            
        except Exception as e:
            # Graceful degradation: log error but don't fail the request
            # This allows the system to continue without caching
            logger.warning(
                f"Cache get operation failed, continuing without cache: {str(e)}",
                exc_info=True
            )
            return None
    
    async def get_with_embedding(
        self,
        prompt: str,
        embedding: List[float],
        similarity_threshold: Optional[float] = None
    ) -> Optional[CachedResponse]:
        """
        Retrieve cached response using embedding for similarity search.
        
        Performs similarity search using pgvector with the provided embedding.
        This is more efficient than get() as it doesn't require re-generating
        the embedding. Implements graceful degradation - cache failures don't break requests.
        
        Args:
            prompt: User prompt text
            embedding: Pre-computed embedding vector
            similarity_threshold: Override default similarity threshold
            
        Returns:
            Optional[CachedResponse]: Cached response if found, None otherwise
            
        Note:
            This method implements graceful degradation. If cache operations fail,
            it logs the error and returns None, allowing the request to proceed
            without caching.
            
        Example:
            >>> cache = SemanticCache()
            >>> await cache.connect()
            >>> embedding = await embedding_service.embed_text(prompt)
            >>> result = await cache.get_with_embedding(prompt, embedding)
        """
        if not self.redis_client or not self.pg_pool:
            logger.warning("Cache not connected, skipping cache lookup")
            return None
        
        threshold = similarity_threshold or self.similarity_threshold
        
        try:
            # First, try exact match in Redis
            cache_key = self._generate_cache_key(prompt)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                logger.info(
                    "cache_hit",
                    match_type="exact",
                    service="semantic_cache",
                    prompt_preview=prompt[:50],
                    similarity_score=1.0
                )
                return CachedResponse(
                    response=data["response"],
                    embedding=data["embedding"],
                    similarity_score=1.0,  # Exact match
                    cached_at=datetime.fromisoformat(data["cached_at"]),
                    ttl=data["ttl"]
                )
            
            # Perform similarity search in pgvector
            # Query semantic_cache table for similar embeddings
            async with self.pg_pool.acquire() as conn:
                query = """
                    SELECT prompt, response, embedding, cached_at, ttl,
                           1 - (embedding <=> $1::vector) as similarity
                    FROM semantic_cache
                    WHERE 1 - (embedding <=> $1::vector) >= $2
                    ORDER BY similarity DESC
                    LIMIT 1
                """
                
                # Convert embedding to pgvector format
                embedding_str = f"[{','.join(map(str, embedding))}]"
                
                row = await conn.fetchrow(query, embedding_str, threshold)
                
                if row:
                    logger.info(
                        "cache_hit",
                        match_type="similarity",
                        service="semantic_cache",
                        prompt_preview=prompt[:50],
                        similarity_score=float(row['similarity'])
                    )
                    return CachedResponse(
                        response=row["response"],
                        embedding=list(row["embedding"]),
                        similarity_score=float(row["similarity"]),
                        cached_at=row["cached_at"],
                        ttl=row["ttl"]
                    )
            
            logger.debug("cache_miss", service="semantic_cache", prompt_preview=prompt[:50])
            return None
            
        except Exception as e:
            # Graceful degradation
            logger.warning(
                f"Cache get_with_embedding operation failed, continuing without cache: {str(e)}",
                exc_info=True
            )
            return None
    
    async def set(
        self,
        prompt: str,
        response: str,
        embedding: List[float],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store response with embedding for similarity search.
        
        Stores the response in both Redis (for fast exact lookups) and
        PostgreSQL with pgvector (for similarity search).
        Implements graceful degradation - cache failures don't break requests.
        
        Args:
            prompt: User prompt text
            response: Response to cache
            embedding: Embedding vector for similarity search
            ttl: Time-to-live in seconds (default: self.default_ttl)
            
        Returns:
            bool: True if successful, False otherwise
            
        Note:
            This method implements graceful degradation. If cache operations fail,
            it logs the error and returns False, allowing the request to proceed
            without caching.
            
        Example:
            >>> cache = SemanticCache()
            >>> await cache.connect()
            >>> embedding = await embedding_service.embed_text(prompt)
            >>> success = await cache.set(prompt, response, embedding)
        """
        if not self.redis_client or not self.pg_pool:
            logger.warning("Cache not connected, skipping cache storage")
            return False
        
        cache_ttl = ttl or self.default_ttl
        
        try:
            # Store in Redis for fast exact lookups
            cache_key = self._generate_cache_key(prompt)
            cache_data = {
                "response": response,
                "embedding": embedding,
                "cached_at": datetime.utcnow().isoformat(),
                "ttl": cache_ttl
            }
            
            await self.redis_client.setex(
                cache_key,
                cache_ttl,
                json.dumps(cache_data)
            )
            
            # Store in PostgreSQL for similarity search
            async with self.pg_pool.acquire() as conn:
                # Convert embedding to pgvector format
                embedding_str = f"[{','.join(map(str, embedding))}]"
                
                query = """
                    INSERT INTO semantic_cache (prompt, response, embedding, cached_at, ttl)
                    VALUES ($1, $2, $3::vector, $4, $5)
                    ON CONFLICT (prompt) DO UPDATE
                    SET response = EXCLUDED.response,
                        embedding = EXCLUDED.embedding,
                        cached_at = EXCLUDED.cached_at,
                        ttl = EXCLUDED.ttl
                """
                
                await conn.execute(
                    query,
                    prompt,
                    response,
                    embedding_str,
                    datetime.utcnow(),
                    cache_ttl
                )
            
            logger.info(
                "cache_set_successful",
                service="semantic_cache",
                prompt_preview=prompt[:50],
                ttl=cache_ttl
            )
            return True
            
        except Exception as e:
            # Graceful degradation: log error but don't fail
            logger.warning(
                "cache_set_failed",
                service="semantic_cache",
                error=str(e),
                exc_info=True
            )
            return False
    
    async def clear(self) -> bool:
        """
        Clear all cached entries.
        
        Removes all entries from both Redis and PostgreSQL.
        Useful for testing and maintenance. Implements graceful degradation.
        
        Returns:
            bool: True if successful, False otherwise
            
        Note:
            This method implements graceful degradation. If cache operations fail,
            it logs the error and returns False.
        """
        if not self.redis_client or not self.pg_pool:
            logger.warning("cache_not_connected", operation="clear", service="semantic_cache")
            return False
        
        try:
            # Clear Redis cache
            keys = await self.redis_client.keys("semantic_cache:*")
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(
                    "cache_cleared",
                    service="semantic_cache",
                    backend="redis",
                    entries_cleared=len(keys)
                )
            
            # Clear PostgreSQL cache
            async with self.pg_pool.acquire() as conn:
                result = await conn.execute("DELETE FROM semantic_cache")
                logger.info(
                    "cache_cleared",
                    service="semantic_cache",
                    backend="postgresql",
                    result=result
                )
            
            return True
            
        except Exception as e:
            logger.warning(
                "cache_clear_failed",
                service="semantic_cache",
                error=str(e),
                exc_info=True
            )
            return False


# Global semantic cache instance
semantic_cache = SemanticCache()


async def get_semantic_cache() -> SemanticCache:
    """
    Dependency injection function for FastAPI endpoints.
    
    Returns:
        SemanticCache: Global semantic cache instance
    """
    return semantic_cache
