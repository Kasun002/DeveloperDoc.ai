"""
Unit tests for MCP client with retry logic.

Tests the MCP client implementation including:
- Tool listing and retrieval
- Tool invocation with parameters
- Retry logic with exponential backoff
- Error handling and exceptions
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from app.services.mcp_client import (
    MCPClient,
    MCPClientError,
    MCPToolNotFoundError,
    MCPToolExecutionError,
    MCPConnectionError
)
from app.schemas.mcp import (
    MCPToolDefinition,
    MCPToolInputSchema,
    MCPToolResponse,
    MCPToolListResponse
)


@pytest.fixture
def mcp_client():
    """Create MCP client instance for testing."""
    return MCPClient(
        base_url="http://localhost:8001",
        timeout=5.0,
        max_retries=3
    )


@pytest.fixture
def sample_tool_definition():
    """Sample tool definition for testing."""
    return MCPToolDefinition(
        name="search_framework_docs",
        description="Search framework documentation",
        inputSchema=MCPToolInputSchema(
            type="object",
            properties={
                "query": {"type": "string"},
                "frameworks": {"type": "array", "items": {"type": "string"}},
                "top_k": {"type": "integer", "default": 10}
            },
            required=["query"]
        )
    )


@pytest.fixture
def sample_tool_response():
    """Sample tool response for testing."""
    return MCPToolResponse(
        tool_name="search_framework_docs",
        result=[
            {
                "content": "NestJS controller example",
                "score": 0.92,
                "framework": "NestJS",
                "source": "https://docs.nestjs.com/controllers",
                "metadata": {"section": "Controllers"}
            }
        ],
        success=True,
        error=None
    )


class TestMCPClientInitialization:
    """Test MCP client initialization and configuration."""
    
    def test_client_initialization(self):
        """Test that client initializes with correct configuration."""
        client = MCPClient(
            base_url="http://test:8001",
            timeout=10.0,
            max_retries=5
        )
        
        assert client.base_url == "http://test:8001"
        assert client.timeout == 10.0
        assert client.max_retries == 5
        assert client.client is not None
    
    def test_client_strips_trailing_slash(self):
        """Test that trailing slash is removed from base URL."""
        client = MCPClient(base_url="http://test:8001/")
        assert client.base_url == "http://test:8001"
    
    def test_get_retry_info(self, mcp_client):
        """Test that retry info is correctly returned."""
        retry_info = mcp_client.get_retry_info()
        
        assert retry_info["max_retries"] == 3
        assert retry_info["retry_strategy"] == "exponential_backoff"
        assert retry_info["backoff_multiplier"] == 1
        assert retry_info["min_wait_seconds"] == 1
        assert retry_info["max_wait_seconds"] == 10


class TestMCPClientToolListing:
    """Test tool listing functionality."""
    
    @pytest.mark.asyncio
    async def test_list_tools_success(self, mcp_client, sample_tool_definition):
        """Test successful tool listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tools": [sample_tool_definition.model_dump()]
        }
        
        with patch.object(mcp_client.client, 'get', return_value=mock_response):
            tools = await mcp_client.list_tools()
            
            assert len(tools) == 1
            assert tools[0].name == "search_framework_docs"
            assert tools[0].description == "Search framework documentation"
    
    @pytest.mark.asyncio
    async def test_list_tools_connection_error(self, mcp_client):
        """Test that connection errors are raised correctly."""
        from tenacity import RetryError
        
        with patch.object(
            mcp_client.client,
            'get',
            side_effect=httpx.NetworkError("Connection failed")
        ):
            with pytest.raises((MCPConnectionError, RetryError)):
                await mcp_client.list_tools()
    
    @pytest.mark.asyncio
    async def test_list_tools_http_error(self, mcp_client):
        """Test that HTTP errors are handled correctly."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=Mock(),
            response=mock_response
        )
        
        with patch.object(mcp_client.client, 'get', return_value=mock_response):
            with pytest.raises(MCPClientError):
                await mcp_client.list_tools()


class TestMCPClientToolRetrieval:
    """Test tool retrieval functionality."""
    
    @pytest.mark.asyncio
    async def test_get_tool_success(self, mcp_client, sample_tool_definition):
        """Test successful tool retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_tool_definition.model_dump()
        
        with patch.object(mcp_client.client, 'get', return_value=mock_response):
            tool = await mcp_client.get_tool("search_framework_docs")
            
            assert tool.name == "search_framework_docs"
            assert tool.description == "Search framework documentation"
    
    @pytest.mark.asyncio
    async def test_get_tool_not_found(self, mcp_client):
        """Test that 404 raises MCPToolNotFoundError."""
        mock_response = Mock()
        mock_response.status_code = 404
        
        with patch.object(mcp_client.client, 'get', return_value=mock_response):
            with pytest.raises(MCPToolNotFoundError) as exc_info:
                await mcp_client.get_tool("nonexistent_tool")
            
            assert "nonexistent_tool" in str(exc_info.value)


class TestMCPClientToolInvocation:
    """Test tool invocation functionality."""
    
    @pytest.mark.asyncio
    async def test_call_tool_success(self, mcp_client, sample_tool_response):
        """Test successful tool invocation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_tool_response.model_dump()
        
        with patch.object(mcp_client.client, 'post', return_value=mock_response):
            result = await mcp_client.call_tool(
                "search_framework_docs",
                {"query": "NestJS controller", "top_k": 5}
            )
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["framework"] == "NestJS"
    
    @pytest.mark.asyncio
    async def test_call_tool_with_trace_id(self, mcp_client, sample_tool_response):
        """Test that trace_id is included in headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_tool_response.model_dump()
        
        mock_post = AsyncMock(return_value=mock_response)
        
        with patch.object(mcp_client.client, 'post', mock_post):
            await mcp_client.call_tool(
                "search_framework_docs",
                {"query": "test"},
                trace_id="test-trace-123"
            )
            
            # Verify trace_id was included in headers
            call_args = mock_post.call_args
            assert call_args.kwargs["headers"]["X-Trace-ID"] == "test-trace-123"
    
    @pytest.mark.asyncio
    async def test_call_tool_not_found(self, mcp_client):
        """Test that 404 raises MCPToolNotFoundError."""
        mock_response = Mock()
        mock_response.status_code = 404
        
        with patch.object(mcp_client.client, 'post', return_value=mock_response):
            with pytest.raises(MCPToolNotFoundError):
                await mcp_client.call_tool("nonexistent_tool", {})
    
    @pytest.mark.asyncio
    async def test_call_tool_validation_error(self, mcp_client):
        """Test that 400 raises MCPClientError without retry."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Invalid parameters"}
        
        with patch.object(mcp_client.client, 'post', return_value=mock_response):
            with pytest.raises(MCPClientError) as exc_info:
                await mcp_client.call_tool("search_framework_docs", {})
            
            assert "Invalid tool parameters" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_call_tool_execution_failure(self, mcp_client):
        """Test that tool execution failures are handled correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tool_name": "search_framework_docs",
            "result": None,
            "success": False,
            "error": "Database connection failed"
        }
        
        with patch.object(mcp_client.client, 'post', return_value=mock_response):
            with pytest.raises(MCPToolExecutionError) as exc_info:
                await mcp_client.call_tool("search_framework_docs", {"query": "test"})
            
            assert "Database connection failed" in str(exc_info.value)


class TestMCPClientRetryLogic:
    """Test retry logic with exponential backoff."""
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, mcp_client, sample_tool_response):
        """Test that timeouts trigger retry."""
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                raise httpx.TimeoutException("Request timeout")
            
            # Success on third attempt
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_tool_response.model_dump()
            return mock_response
        
        with patch.object(mcp_client.client, 'post', side_effect=mock_post):
            result = await mcp_client.call_tool(
                "search_framework_docs",
                {"query": "test"}
            )
            
            assert call_count == 3  # Initial + 2 retries
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_retry_on_network_error(self, mcp_client, sample_tool_response):
        """Test that network errors trigger retry."""
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count < 2:
                raise httpx.NetworkError("Network unreachable")
            
            # Success on second attempt
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_tool_response.model_dump()
            return mock_response
        
        with patch.object(mcp_client.client, 'post', side_effect=mock_post):
            result = await mcp_client.call_tool(
                "search_framework_docs",
                {"query": "test"}
            )
            
            assert call_count == 2  # Initial + 1 retry
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_max_retries_enforced(self, mcp_client):
        """Test that maximum retry limit is enforced."""
        from tenacity import RetryError
        
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Request timeout")
        
        with patch.object(mcp_client.client, 'post', side_effect=mock_post):
            with pytest.raises((MCPConnectionError, RetryError)):
                await mcp_client.call_tool(
                    "search_framework_docs",
                    {"query": "test"}
                )
            
            # Should be exactly 3 attempts (initial + 2 retries)
            assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_no_retry_on_validation_error(self, mcp_client):
        """Test that validation errors (400) don't trigger retry."""
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"detail": "Invalid parameters"}
            return mock_response
        
        with patch.object(mcp_client.client, 'post', side_effect=mock_post):
            with pytest.raises(MCPClientError):
                await mcp_client.call_tool("search_framework_docs", {})
            
            # Should only be called once (no retries)
            assert call_count == 1


class TestMCPClientContextManager:
    """Test async context manager functionality."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test that client can be used as async context manager."""
        async with MCPClient() as client:
            assert client is not None
            assert client.client is not None
        
        # Client should be closed after context exit
        # Note: We can't easily test this without accessing internal state
    
    @pytest.mark.asyncio
    async def test_close_method(self, mcp_client):
        """Test that close method works correctly."""
        await mcp_client.close()
        # If no exception is raised, the test passes
