"""
Tests for caching layer (semantic cache and tool cache).

This module contains unit tests for the SemanticCache and ToolCache
implementations to verify basic functionality.
"""

import pytest
from app.services.semantic_cache import SemanticCache
from app.services.tool_cache import ToolCache


class TestToolCache:
    """Tests for ToolCache functionality."""
    
    @pytest.mark.asyncio
    async def test_tool_cache_generate_cache_key(self):
        """Test cache key generation is deterministic."""
        cache = ToolCache()
        
        # Same inputs should produce same key
        key1 = cache.generate_cache_key(
            "search_framework_docs",
            {"query": "NestJS controller", "top_k": 10}
        )
        key2 = cache.generate_cache_key(
            "search_framework_docs",
            {"query": "NestJS controller", "top_k": 10}
        )
        
        assert key1 == key2
        assert key1.startswith("tool_cache:search_framework_docs:")
    
    @pytest.mark.asyncio
    async def test_tool_cache_key_order_independence(self):
        """Test cache key is independent of parameter order."""
        cache = ToolCache()
        
        # Different parameter order should produce same key
        key1 = cache.generate_cache_key(
            "search_docs",
            {"query": "test", "top_k": 10, "framework": "NestJS"}
        )
        key2 = cache.generate_cache_key(
            "search_docs",
            {"framework": "NestJS", "query": "test", "top_k": 10}
        )
        
        assert key1 == key2
    
    @pytest.mark.asyncio
    async def test_tool_cache_different_params_different_keys(self):
        """Test different parameters produce different keys."""
        cache = ToolCache()
        
        key1 = cache.generate_cache_key(
            "search_docs",
            {"query": "test1", "top_k": 10}
        )
        key2 = cache.generate_cache_key(
            "search_docs",
            {"query": "test2", "top_k": 10}
        )
        
        assert key1 != key2
    
    @pytest.mark.asyncio
    async def test_tool_cache_connect_requires_redis(self):
        """Test cache connection requires valid Redis URL."""
        cache = ToolCache(redis_url="redis://invalid:9999")
        
        with pytest.raises(ConnectionError):
            await cache.connect()
    
    @pytest.mark.asyncio
    async def test_tool_cache_operations_require_connection(self):
        """Test cache operations fail without connection."""
        cache = ToolCache()
        
        with pytest.raises(RuntimeError, match="not connected"):
            await cache.get("test_key")
        
        with pytest.raises(RuntimeError, match="not connected"):
            await cache.set("test_key", {"result": "test"})


class TestSemanticCache:
    """Tests for SemanticCache functionality."""
    
    @pytest.mark.asyncio
    async def test_semantic_cache_generate_cache_key(self):
        """Test cache key generation from prompt."""
        cache = SemanticCache()
        
        # Same prompt should produce same key
        key1 = cache._generate_cache_key("How to create a NestJS controller?")
        key2 = cache._generate_cache_key("How to create a NestJS controller?")
        
        assert key1 == key2
        assert key1.startswith("semantic_cache:")
    
    @pytest.mark.asyncio
    async def test_semantic_cache_different_prompts_different_keys(self):
        """Test different prompts produce different keys."""
        cache = SemanticCache()
        
        key1 = cache._generate_cache_key("How to create a NestJS controller?")
        key2 = cache._generate_cache_key("How to create a React component?")
        
        assert key1 != key2
    
    @pytest.mark.asyncio
    async def test_semantic_cache_default_threshold(self):
        """Test default similarity threshold is 0.95."""
        cache = SemanticCache()
        
        assert cache.similarity_threshold == 0.95
    
    @pytest.mark.asyncio
    async def test_semantic_cache_default_ttl(self):
        """Test default TTL is 3600 seconds (1 hour)."""
        cache = SemanticCache()
        
        assert cache.default_ttl == 3600
    
    @pytest.mark.asyncio
    async def test_semantic_cache_custom_threshold(self):
        """Test custom similarity threshold can be set."""
        cache = SemanticCache(similarity_threshold=0.90)
        
        assert cache.similarity_threshold == 0.90
    
    @pytest.mark.asyncio
    async def test_semantic_cache_operations_require_connection(self):
        """Test cache operations fail without connection."""
        cache = SemanticCache()
        
        with pytest.raises(RuntimeError, match="not connected"):
            await cache.get("test prompt")
        
        with pytest.raises(RuntimeError, match="not connected"):
            await cache.set("test prompt", "response", [0.1] * 1536)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
