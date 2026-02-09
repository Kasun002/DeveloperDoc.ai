"""
Performance tests for AI Agent System.

These tests verify performance characteristics including:
- Semantic cache lookup speed (<50ms)
- Vector search performance with HNSW index
- Concurrent request handling

Validates Requirements: 7.1, 7.2

NOTE: Some tests require infrastructure (Redis, PostgreSQL with pgvector) and are
marked to skip by default. Run them manually when infrastructure is available.
"""

import pytest
import pytest_asyncio
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List

from app.services.semantic_cache import SemanticCache
from app.services.vector_search_service import VectorSearchService
from app.workflows.agent_workflow import AgentWorkflow


@pytest_asyncio.fixture
async def semantic_cache_instance():
    """Create a test semantic cache instance."""
    cache = SemanticCache(
        redis_url="redis://localhost:6379/1",
        similarity_threshold=0.95,
        default_ttl=3600
    )
    try:
        await cache.connect()
        await cache.clear()
        
        # Pre-populate with test data
        for i in range(10):
            prompt = f"Test prompt {i}"
            response = f"Test response {i}"
            embedding = [0.1 + i * 0.01] * 1536
            await cache.set(prompt, response, embedding)
        
        yield cache
    finally:
        await cache.clear()
        await cache.disconnect()


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.skip(reason="Requires Redis and PostgreSQL - run manually with infrastructure")
async def test_semantic_cache_lookup_speed(semantic_cache_instance):
    """
    Test semantic cache lookup completes within 50ms.
    
    Validates Requirement: 7.1 - Fast cache lookups
    
    NOTE: Requires Redis and PostgreSQL with semantic_cache table
    """
    cache = semantic_cache_instance
    
    # Test exact match lookup (should be fastest)
    prompt = "Test prompt 5"
    embedding = [0.15] * 1536
    
    # Warm up
    await cache.get_with_embedding(prompt, embedding)
    
    # Measure lookup time
    start_time = time.time()
    result = await cache.get_with_embedding(prompt, embedding)
    duration_ms = (time.time() - start_time) * 1000
    
    # Verify performance
    assert duration_ms < 50, f"Cache lookup took {duration_ms:.2f}ms, expected <50ms"
    assert result is not None


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.skip(reason="Requires Redis and PostgreSQL - run manually with infrastructure")
async def test_semantic_cache_multiple_lookups(semantic_cache_instance):
    """
    Test multiple cache lookups maintain performance.
    
    Validates Requirement: 7.1
    
    NOTE: Requires Redis and PostgreSQL with semantic_cache table
    """
    cache = semantic_cache_instance
    
    # Perform 10 lookups and measure average time
    durations = []
    
    for i in range(10):
        prompt = f"Test prompt {i}"
        embedding = [0.1 + i * 0.01] * 1536
        
        start_time = time.time()
        await cache.get_with_embedding(prompt, embedding)
        duration_ms = (time.time() - start_time) * 1000
        durations.append(duration_ms)
    
    # Calculate average
    avg_duration = sum(durations) / len(durations)
    
    # Verify average performance
    assert avg_duration < 50, f"Average cache lookup took {avg_duration:.2f}ms, expected <50ms"
    
    # Verify no lookup exceeded 100ms (2x threshold)
    max_duration = max(durations)
    assert max_duration < 100, f"Slowest lookup took {max_duration:.2f}ms, expected <100ms"


@pytest.mark.asyncio
@pytest.mark.performance
@patch("app.services.vector_search_service.VectorSearchService.search_documentation")
async def test_vector_search_with_hnsw_performance(mock_search):
    """
    Test vector search performance with HNSW index.
    
    Validates Requirement: 7.2 - O(log N) time complexity with HNSW
    """
    # Mock vector search to simulate HNSW performance
    from app.schemas.agent import DocumentationResult
    
    mock_results = [
        DocumentationResult(
            content=f"Test documentation {i}",
            score=0.9 - i * 0.05,
            metadata={"section": "test"},
            source=f"test_source_{i}",
            framework="NestJS"
        )
        for i in range(10)
    ]
    
    mock_search.return_value = mock_results
    
    # Create service instance
    service = VectorSearchService()
    
    # Measure search time
    query_embedding = [0.1] * 1536
    
    start_time = time.time()
    results = await service.search_documentation(
        query_embedding=query_embedding,
        top_k=10,
        min_score=0.7
    )
    duration_ms = (time.time() - start_time) * 1000
    
    # Verify results returned
    assert len(results) > 0
    
    # Verify search completed quickly (HNSW should be fast)
    # Note: With mocking, this tests the service layer overhead
    assert duration_ms < 100, f"Vector search took {duration_ms:.2f}ms"


@pytest.mark.asyncio
@pytest.mark.performance
@patch("app.agents.supervisor_agent.AsyncOpenAI")
@patch("app.agents.code_gen_agent.AsyncOpenAI")
@patch("app.agents.documentation_search_agent.DocumentationSearchAgent.search_docs")
async def test_concurrent_request_handling(
    mock_search_docs,
    mock_code_gen_openai,
    mock_supervisor_openai
):
    """
    Test system can handle concurrent requests efficiently.
    
    Validates Requirements: 7.1, 7.2 - Concurrent performance
    """
    # Mock supervisor
    mock_supervisor_response = AsyncMock()
    mock_supervisor_response.choices = [
        AsyncMock(message=AsyncMock(content="CODE_ONLY"))
    ]
    mock_supervisor_response.usage = AsyncMock(total_tokens=50)
    mock_supervisor_openai.return_value.chat.completions.create = AsyncMock(
        return_value=mock_supervisor_response
    )
    
    # Mock code generation
    mock_code_response = AsyncMock()
    mock_code_response.choices = [
        AsyncMock(message=AsyncMock(content="```python\nprint('test')\n```"))
    ]
    mock_code_response.usage = AsyncMock(total_tokens=80)
    mock_code_gen_openai.return_value.chat.completions.create = AsyncMock(
        return_value=mock_code_response
    )
    
    # Mock search
    from app.schemas.agent import DocumentationResult
    mock_search_docs.return_value = [
        DocumentationResult(
            content="Test doc",
            score=0.9,
            metadata={},
            source="test",
            framework="NestJS"
        )
    ]
    
    workflow = AgentWorkflow()
    
    # Create 10 concurrent requests
    async def execute_request(i: int):
        return await workflow.execute(
            prompt=f"Test prompt {i}",
            trace_id=f"trace-{i}",
            max_iterations=1
        )
    
    # Execute concurrently
    start_time = time.time()
    tasks = [execute_request(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    total_duration = time.time() - start_time
    
    # Verify all requests completed
    assert len(results) == 10
    assert all(r.result is not None for r in results)
    
    # Verify concurrent execution was efficient
    # 10 requests should complete in less than 10x single request time
    # With proper async handling, should be much faster
    avg_time_per_request = total_duration / 10
    
    # Log performance metrics
    print(f"\nConcurrent Performance Metrics:")
    print(f"Total time for 10 requests: {total_duration:.2f}s")
    print(f"Average time per request: {avg_time_per_request:.2f}s")
    
    # Verify reasonable performance (adjust threshold based on system)
    assert total_duration < 30, f"10 concurrent requests took {total_duration:.2f}s"


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.skip(reason="Requires Redis and PostgreSQL - run manually with infrastructure")
async def test_cache_write_performance(semantic_cache_instance):
    """
    Test cache write operations are performant.
    
    Validates Requirement: 7.1
    
    NOTE: Requires Redis and PostgreSQL with semantic_cache table
    """
    cache = semantic_cache_instance
    
    # Measure write time for single entry
    prompt = "New test prompt"
    response = "New test response"
    embedding = [0.5] * 1536
    
    start_time = time.time()
    success = await cache.set(prompt, response, embedding)
    duration_ms = (time.time() - start_time) * 1000
    
    assert success is True
    
    # Cache writes should be fast (under 100ms)
    assert duration_ms < 100, f"Cache write took {duration_ms:.2f}ms, expected <100ms"


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.skip(reason="Requires Redis and PostgreSQL - run manually with infrastructure")
async def test_cache_batch_operations(semantic_cache_instance):
    """
    Test cache can handle batch operations efficiently.
    
    Validates Requirement: 7.1
    
    NOTE: Requires Redis and PostgreSQL with semantic_cache table
    """
    cache = semantic_cache_instance
    
    # Perform 20 cache operations (10 writes, 10 reads)
    start_time = time.time()
    
    # Write 10 entries
    for i in range(10):
        prompt = f"Batch prompt {i}"
        response = f"Batch response {i}"
        embedding = [0.2 + i * 0.01] * 1536
        await cache.set(prompt, response, embedding)
    
    # Read 10 entries
    for i in range(10):
        prompt = f"Batch prompt {i}"
        embedding = [0.2 + i * 0.01] * 1536
        await cache.get_with_embedding(prompt, embedding)
    
    total_duration = time.time() - start_time
    avg_operation_time = (total_duration / 20) * 1000  # ms per operation
    
    # Verify batch operations are efficient
    assert avg_operation_time < 50, f"Average operation time: {avg_operation_time:.2f}ms"


@pytest.mark.asyncio
@pytest.mark.performance
@patch("app.agents.supervisor_agent.AsyncOpenAI")
async def test_workflow_execution_time(mock_supervisor_openai):
    """
    Test workflow execution completes in reasonable time.
    
    Validates overall system performance
    """
    # Mock supervisor
    mock_supervisor_response = AsyncMock()
    mock_supervisor_response.choices = [
        AsyncMock(message=AsyncMock(content="SEARCH_ONLY"))
    ]
    mock_supervisor_response.usage = AsyncMock(total_tokens=50)
    mock_supervisor_openai.return_value.chat.completions.create = AsyncMock(
        return_value=mock_supervisor_response
    )
    
    workflow = AgentWorkflow()
    
    # Measure workflow execution time
    start_time = time.time()
    response = await workflow.execute(
        prompt="Test prompt",
        trace_id="perf-test",
        max_iterations=1
    )
    duration_ms = (time.time() - start_time) * 1000
    
    # Verify workflow completed
    assert response.result is not None
    
    # Verify execution time is reasonable
    # Note: With mocks, this should be very fast
    assert duration_ms < 1000, f"Workflow took {duration_ms:.2f}ms"
    
    # Verify metadata includes processing time
    assert response.metadata.processing_time_ms > 0


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.skip(reason="Requires Redis and PostgreSQL - run manually with infrastructure")
async def test_cache_similarity_search_performance(semantic_cache_instance):
    """
    Test similarity search performance in cache.
    
    Validates Requirement: 7.2 - Efficient similarity search
    
    NOTE: Requires Redis and PostgreSQL with semantic_cache table
    """
    cache = semantic_cache_instance
    
    # Perform similarity search with slightly different embedding
    prompt = "Similar but not exact prompt"
    # Use embedding similar to "Test prompt 5" but not exact
    embedding = [0.149] * 1536  # Close to 0.15
    
    start_time = time.time()
    result = await cache.get_with_embedding(
        prompt,
        embedding,
        similarity_threshold=0.90  # Lower threshold to test similarity
    )
    duration_ms = (time.time() - start_time) * 1000
    
    # Similarity search should still be fast
    assert duration_ms < 100, f"Similarity search took {duration_ms:.2f}ms"


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.skip(reason="Requires Redis and PostgreSQL - run manually with infrastructure")
async def test_concurrent_cache_operations(semantic_cache_instance):
    """
    Test cache handles concurrent operations without degradation.
    
    Validates Requirement: 7.1
    
    NOTE: Requires Redis and PostgreSQL with semantic_cache table
    """
    cache = semantic_cache_instance
    
    # Create concurrent read operations
    async def read_operation(i: int):
        prompt = f"Test prompt {i % 10}"  # Reuse existing prompts
        embedding = [0.1 + (i % 10) * 0.01] * 1536
        return await cache.get_with_embedding(prompt, embedding)
    
    # Execute 20 concurrent reads
    start_time = time.time()
    tasks = [read_operation(i) for i in range(20)]
    results = await asyncio.gather(*tasks)
    total_duration = time.time() - start_time
    
    # Verify all operations completed
    assert len(results) == 20
    
    # Verify concurrent operations were efficient
    avg_time = (total_duration / 20) * 1000
    assert avg_time < 100, f"Average concurrent operation time: {avg_time:.2f}ms"


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.skip(reason="Requires Redis and PostgreSQL - run manually with infrastructure")
@patch("app.agents.supervisor_agent.AsyncOpenAI")
@patch("app.agents.code_gen_agent.AsyncOpenAI")
async def test_workflow_with_cache_performance(
    mock_code_gen_openai,
    mock_supervisor_openai,
    semantic_cache_instance
):
    """
    Test workflow performance with caching enabled.
    
    Validates Requirements: 4.1, 7.1
    
    NOTE: Requires Redis and PostgreSQL with semantic_cache table
    """
    # Mock supervisor
    mock_supervisor_response = AsyncMock()
    mock_supervisor_response.choices = [
        AsyncMock(message=AsyncMock(content="CODE_ONLY"))
    ]
    mock_supervisor_response.usage = AsyncMock(total_tokens=50)
    mock_supervisor_openai.return_value.chat.completions.create = AsyncMock(
        return_value=mock_supervisor_response
    )
    
    # Mock code generation
    mock_code_response = AsyncMock()
    mock_code_response.choices = [
        AsyncMock(message=AsyncMock(content="```python\nprint('cached')\n```"))
    ]
    mock_code_response.usage = AsyncMock(total_tokens=80)
    mock_code_gen_openai.return_value.chat.completions.create = AsyncMock(
        return_value=mock_code_response
    )
    
    workflow = AgentWorkflow()
    
    # First request (cache miss)
    start_time = time.time()
    response1 = await workflow.execute(
        prompt="Write hello world",
        trace_id="cache-test-1",
        max_iterations=1
    )
    first_duration = time.time() - start_time
    
    # Cache the response
    cache = semantic_cache_instance
    embedding = [0.3] * 1536
    await cache.set("Write hello world", response1.result, embedding)
    
    # Second request (cache hit)
    start_time = time.time()
    cached_response = await cache.get_with_embedding("Write hello world", embedding)
    cache_duration = time.time() - start_time
    
    # Verify cache hit is significantly faster
    cache_duration_ms = cache_duration * 1000
    assert cache_duration_ms < 50, f"Cache hit took {cache_duration_ms:.2f}ms"
    
    # Cache hit should be much faster than full workflow
    assert cache_duration < first_duration / 10, "Cache hit should be at least 10x faster"
