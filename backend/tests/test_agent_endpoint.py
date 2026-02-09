"""
Integration tests for the AI Agent query endpoint.

Tests the /api/v1/agent/query endpoint with various scenarios including
cache hits, cache misses, error handling, and response validation.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# Disable OpenTelemetry during tests to avoid span export errors
os.environ["OTEL_ENABLED"] = "false"

from app.main import app
from app.schemas.agent import (
    AgentRequest,
    AgentResponse,
    ResponseMetadata,
    CachedResponse,
)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_semantic_cache():
    """Mock semantic cache for testing."""
    with patch("app.api.v1.endpoints.agent.semantic_cache") as mock_cache:
        mock_cache.redis_client = MagicMock()
        mock_cache.pg_pool = MagicMock()
        yield mock_cache


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for testing."""
    with patch("app.api.v1.endpoints.agent.embedding_service") as mock_service:
        mock_service.embed_text = AsyncMock(return_value=[0.1] * 1536)
        yield mock_service


@pytest.fixture
def mock_agent_workflow():
    """Mock agent workflow for testing."""
    with patch("app.api.v1.endpoints.agent.agent_workflow") as mock_workflow:
        yield mock_workflow


def test_agent_query_endpoint_exists(client):
    """Test that the agent query endpoint exists and accepts POST requests."""
    # Send a request without proper payload to check endpoint exists
    response = client.post("/api/v1/agent/query", json={})
    
    # Should return 422 (validation error) not 404 (not found)
    assert response.status_code in [422, 400], "Endpoint should exist and validate input"


def test_agent_query_validation_error(client):
    """Test that invalid requests return 400/422 with validation errors."""
    # Empty prompt should fail validation
    response = client.post("/api/v1/agent/query", json={"prompt": ""})
    
    assert response.status_code in [422, 400]
    assert "detail" in response.json()


def test_agent_query_prompt_too_long(client):
    """Test that prompts exceeding max length are rejected."""
    # Create a prompt longer than 10000 characters
    long_prompt = "a" * 10001
    
    response = client.post("/api/v1/agent/query", json={"prompt": long_prompt})
    
    assert response.status_code in [422, 400]
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_agent_query_cache_hit(
    client, mock_semantic_cache, mock_embedding_service, mock_agent_workflow
):
    """Test that cache hits return cached responses without invoking workflow."""
    from datetime import datetime
    
    # Mock cache hit
    cached_response = CachedResponse(
        response="Cached code result",
        embedding=[0.1] * 1536,
        similarity_score=0.97,
        cached_at=datetime.utcnow(),
        ttl=3600
    )
    mock_semantic_cache.get_with_embedding = AsyncMock(return_value=cached_response)
    
    # Make request
    response = client.post(
        "/api/v1/agent/query",
        json={"prompt": "Create a NestJS controller"}
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    
    # Should have result and metadata
    assert "result" in data
    assert "metadata" in data
    
    # Metadata should indicate cache hit
    metadata = data["metadata"]
    assert metadata["cache_hit"] is True
    assert metadata["tokens_used"] == 0  # No tokens used for cache hit
    assert len(metadata["agents_invoked"]) == 0  # No agents invoked
    
    # Workflow should not be executed
    mock_agent_workflow.execute.assert_not_called()


@pytest.mark.asyncio
async def test_agent_query_cache_miss(
    client, mock_semantic_cache, mock_embedding_service, mock_agent_workflow
):
    """Test that cache misses execute the workflow and cache the result."""
    # Mock cache miss
    mock_semantic_cache.get_with_embedding = AsyncMock(return_value=None)
    mock_semantic_cache.set = AsyncMock(return_value=True)
    
    # Mock workflow execution
    mock_response = AgentResponse(
        result="Generated code",
        metadata=ResponseMetadata(
            trace_id="test-trace-id",
            cache_hit=False,
            processing_time_ms=1000.0,
            tokens_used=500,
            agents_invoked=["supervisor", "code_gen"],
            workflow_iterations=1
        )
    )
    mock_agent_workflow.execute = AsyncMock(return_value=mock_response)
    
    # Make request
    response = client.post(
        "/api/v1/agent/query",
        json={"prompt": "Create a NestJS controller"}
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    
    # Should have result and metadata
    assert "result" in data
    assert data["result"] == "Generated code"
    
    # Metadata should indicate cache miss
    metadata = data["metadata"]
    assert metadata["cache_hit"] is False
    assert metadata["tokens_used"] == 500
    assert "supervisor" in metadata["agents_invoked"]
    
    # Workflow should be executed
    mock_agent_workflow.execute.assert_called_once()
    
    # Result should be cached
    mock_semantic_cache.set.assert_called_once()


def test_agent_query_with_context(client, mock_semantic_cache, mock_embedding_service, mock_agent_workflow):
    """Test that requests with context are processed correctly."""
    # Mock cache miss
    mock_semantic_cache.get_with_embedding = AsyncMock(return_value=None)
    mock_semantic_cache.set = AsyncMock(return_value=True)
    
    # Mock workflow execution
    mock_response = AgentResponse(
        result="Generated NestJS code",
        metadata=ResponseMetadata(
            trace_id="test-trace-id",
            cache_hit=False,
            processing_time_ms=1000.0,
            tokens_used=500,
            agents_invoked=["supervisor", "documentation_search", "code_gen"],
            workflow_iterations=1
        )
    )
    mock_agent_workflow.execute = AsyncMock(return_value=mock_response)
    
    # Make request with context
    response = client.post(
        "/api/v1/agent/query",
        json={
            "prompt": "Create a controller",
            "context": {"framework": "NestJS"}
        }
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    
    # Verify workflow was called with context
    call_args = mock_agent_workflow.execute.call_args
    assert call_args is not None
    assert call_args.kwargs.get("context") == {"framework": "NestJS"}


def test_agent_query_with_max_iterations(client, mock_semantic_cache, mock_embedding_service, mock_agent_workflow):
    """Test that max_iterations parameter is passed to workflow."""
    # Mock cache miss
    mock_semantic_cache.get_with_embedding = AsyncMock(return_value=None)
    mock_semantic_cache.set = AsyncMock(return_value=True)
    
    # Mock workflow execution
    mock_response = AgentResponse(
        result="Generated code",
        metadata=ResponseMetadata(
            trace_id="test-trace-id",
            cache_hit=False,
            processing_time_ms=1000.0,
            tokens_used=500,
            agents_invoked=["supervisor", "code_gen"],
            workflow_iterations=2
        )
    )
    mock_agent_workflow.execute = AsyncMock(return_value=mock_response)
    
    # Make request with max_iterations
    response = client.post(
        "/api/v1/agent/query",
        json={
            "prompt": "Create a controller",
            "max_iterations": 5
        }
    )
    
    # Verify response
    assert response.status_code == 200
    
    # Verify workflow was called with max_iterations
    call_args = mock_agent_workflow.execute.call_args
    assert call_args is not None
    assert call_args.kwargs.get("max_iterations") == 5


def test_agent_health_check(client):
    """Test the agent health check endpoint."""
    response = client.get("/api/v1/agent/health")
    
    # Should return 200 or 503 depending on service state
    assert response.status_code in [200, 503]
    
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "unhealthy"]


@pytest.mark.asyncio
async def test_agent_query_graceful_cache_degradation(
    client, mock_semantic_cache, mock_embedding_service, mock_agent_workflow
):
    """Test that cache failures don't break the request."""
    # Mock cache failure
    mock_semantic_cache.get_with_embedding = AsyncMock(
        side_effect=Exception("Cache unavailable")
    )
    mock_semantic_cache.set = AsyncMock(return_value=False)
    
    # Mock workflow execution
    mock_response = AgentResponse(
        result="Generated code",
        metadata=ResponseMetadata(
            trace_id="test-trace-id",
            cache_hit=False,
            processing_time_ms=1000.0,
            tokens_used=500,
            agents_invoked=["supervisor", "code_gen"],
            workflow_iterations=1
        )
    )
    mock_agent_workflow.execute = AsyncMock(return_value=mock_response)
    
    # Make request
    response = client.post(
        "/api/v1/agent/query",
        json={"prompt": "Create a NestJS controller"}
    )
    
    # Should still succeed despite cache failure
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert data["result"] == "Generated code"
    
    # Workflow should still be executed
    mock_agent_workflow.execute.assert_called_once()


def test_agent_query_response_metadata_completeness(client, mock_semantic_cache, mock_embedding_service, mock_agent_workflow):
    """Test that response metadata includes all required fields."""
    # Mock cache miss
    mock_semantic_cache.get_with_embedding = AsyncMock(return_value=None)
    mock_semantic_cache.set = AsyncMock(return_value=True)
    
    # Mock workflow execution
    mock_response = AgentResponse(
        result="Generated code",
        metadata=ResponseMetadata(
            trace_id="test-trace-id",
            cache_hit=False,
            processing_time_ms=1000.0,
            tokens_used=500,
            agents_invoked=["supervisor", "code_gen"],
            workflow_iterations=1
        )
    )
    mock_agent_workflow.execute = AsyncMock(return_value=mock_response)
    
    # Make request
    response = client.post(
        "/api/v1/agent/query",
        json={"prompt": "Create a controller"}
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    
    # Verify all required metadata fields are present
    metadata = data["metadata"]
    required_fields = [
        "trace_id",
        "cache_hit",
        "processing_time_ms",
        "tokens_used",
        "agents_invoked",
        "workflow_iterations"
    ]
    
    for field in required_fields:
        assert field in metadata, f"Missing required metadata field: {field}"
    
    # Verify field types
    assert isinstance(metadata["trace_id"], str)
    assert isinstance(metadata["cache_hit"], bool)
    assert isinstance(metadata["processing_time_ms"], (int, float))
    assert isinstance(metadata["tokens_used"], int)
    assert isinstance(metadata["agents_invoked"], list)
    assert isinstance(metadata["workflow_iterations"], int)
