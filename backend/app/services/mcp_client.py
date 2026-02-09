"""
MCP (Model Context Protocol) client for tool communication.

This module implements the MCP protocol client that handles communication with
MCP tools, including request/response serialization and retry logic with
exponential backoff for transient failures.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    after_log
)

from app.core.config import settings
from app.schemas.mcp import (
    MCPToolDefinition,
    MCPToolRequest,
    MCPToolResponse,
    MCPToolListResponse
)

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Base exception for MCP client errors."""
    pass


class MCPToolNotFoundError(MCPClientError):
    """Exception raised when a requested tool is not found."""
    pass


class MCPToolExecutionError(MCPClientError):
    """Exception raised when tool execution fails."""
    pass


class MCPConnectionError(MCPClientError):
    """Exception raised when connection to MCP service fails."""
    pass


class MCPClient:
    """
    Client for communicating with MCP (Model Context Protocol) tools.
    
    This client handles:
    - Tool discovery and listing
    - Tool invocation with parameter validation
    - Request/response serialization
    - Retry logic with exponential backoff for transient failures
    - Connection pooling and timeout management
    
    The client implements the MCP protocol specification for tool communication,
    allowing agents to invoke external tools in a standardized way.
    
    Attributes:
        base_url: Base URL of the MCP service
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        client: HTTP client for making requests
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize the MCP client.
        
        Args:
            base_url: Base URL of the MCP service (default: http://localhost:8001)
            timeout: Request timeout in seconds (default: 30.0)
            max_retries: Maximum number of retry attempts (default: 3)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Create HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20
            )
        )
        
        logger.info(
            f"MCP client initialized",
            extra={
                "base_url": self.base_url,
                "timeout": timeout,
                "max_retries": max_retries
            }
        )
    
    async def close(self):
        """Close the HTTP client and release resources."""
        await self.client.aclose()
        logger.info("MCP client closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, MCPConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO)
    )
    async def list_tools(self) -> List[MCPToolDefinition]:
        """
        List all available MCP tools.
        
        Retrieves the list of available tools from the MCP service with their
        definitions, including input schemas and descriptions.
        
        Returns:
            List[MCPToolDefinition]: List of available tool definitions
            
        Raises:
            MCPConnectionError: If connection to MCP service fails after retries
            MCPClientError: If the request fails for other reasons
            
        Example:
            >>> client = MCPClient()
            >>> tools = await client.list_tools()
            >>> for tool in tools:
            ...     print(f"{tool.name}: {tool.description}")
        """
        try:
            logger.info("Listing MCP tools")
            
            response = await self.client.get("/mcp/tools")
            response.raise_for_status()
            
            tool_list = MCPToolListResponse(**response.json())
            
            logger.info(
                f"Successfully listed MCP tools",
                extra={"tool_count": len(tool_list.tools)}
            )
            
            return tool_list.tools
            
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.error(
                f"Network error while listing tools",
                extra={"error": str(e)},
                exc_info=True
            )
            raise MCPConnectionError(f"Failed to connect to MCP service: {str(e)}") from e
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error while listing tools",
                extra={
                    "status_code": e.response.status_code,
                    "error": str(e)
                },
                exc_info=True
            )
            raise MCPClientError(f"Failed to list tools: {str(e)}") from e
            
        except Exception as e:
            logger.error(
                f"Unexpected error while listing tools",
                extra={"error": str(e)},
                exc_info=True
            )
            raise MCPClientError(f"Unexpected error: {str(e)}") from e
    
    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, MCPConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO)
    )
    async def get_tool(self, tool_name: str) -> MCPToolDefinition:
        """
        Get definition for a specific MCP tool.
        
        Retrieves the tool definition including input schema and description.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            MCPToolDefinition: Tool definition
            
        Raises:
            MCPToolNotFoundError: If the tool does not exist
            MCPConnectionError: If connection to MCP service fails after retries
            MCPClientError: If the request fails for other reasons
            
        Example:
            >>> client = MCPClient()
            >>> tool = await client.get_tool("search_framework_docs")
            >>> print(tool.description)
        """
        try:
            logger.info(f"Getting MCP tool definition", extra={"tool_name": tool_name})
            
            response = await self.client.get(f"/mcp/tools/{tool_name}")
            
            if response.status_code == 404:
                raise MCPToolNotFoundError(f"Tool '{tool_name}' not found")
            
            response.raise_for_status()
            
            tool = MCPToolDefinition(**response.json())
            
            logger.info(
                f"Successfully retrieved tool definition",
                extra={"tool_name": tool_name}
            )
            
            return tool
            
        except MCPToolNotFoundError:
            raise
            
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.error(
                f"Network error while getting tool",
                extra={"tool_name": tool_name, "error": str(e)},
                exc_info=True
            )
            raise MCPConnectionError(f"Failed to connect to MCP service: {str(e)}") from e
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error while getting tool",
                extra={
                    "tool_name": tool_name,
                    "status_code": e.response.status_code,
                    "error": str(e)
                },
                exc_info=True
            )
            raise MCPClientError(f"Failed to get tool: {str(e)}") from e
            
        except Exception as e:
            logger.error(
                f"Unexpected error while getting tool",
                extra={"tool_name": tool_name, "error": str(e)},
                exc_info=True
            )
            raise MCPClientError(f"Unexpected error: {str(e)}") from e
    
    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, MCPConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO)
    )
    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        trace_id: Optional[str] = None
    ) -> Any:
        """
        Invoke an MCP tool with the specified parameters.
        
        Calls the tool and returns the result. Implements retry logic with
        exponential backoff for transient failures (network errors, timeouts).
        
        The retry configuration:
        - Maximum 3 attempts (initial + 2 retries)
        - Exponential backoff: 1s, 2s, 4s (multiplier=1, min=1, max=10)
        - Only retries on network/timeout errors, not on validation errors
        
        Args:
            tool_name: Name of the tool to invoke
            parameters: Tool parameters matching the tool's input schema
            trace_id: Optional trace ID for request tracking
            
        Returns:
            Any: Tool execution result (structure depends on tool)
            
        Raises:
            MCPToolNotFoundError: If the tool does not exist
            MCPToolExecutionError: If tool execution fails
            MCPConnectionError: If connection fails after all retries
            MCPClientError: If the request fails for other reasons
            
        Example:
            >>> client = MCPClient()
            >>> result = await client.call_tool(
            ...     "search_framework_docs",
            ...     {
            ...         "query": "How to create a controller",
            ...         "frameworks": ["NestJS"],
            ...         "top_k": 5
            ...     }
            ... )
            >>> print(f"Found {len(result)} results")
        """
        try:
            logger.info(
                f"Calling MCP tool",
                extra={
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "trace_id": trace_id
                }
            )
            
            # Prepare request
            request_data = MCPToolRequest(
                tool_name=tool_name,
                parameters=parameters
            )
            
            # Add trace_id to headers if provided
            headers = {}
            if trace_id:
                headers["X-Trace-ID"] = trace_id
            
            # Make request
            response = await self.client.post(
                "/mcp/tools/invoke",
                json=request_data.model_dump(),
                headers=headers
            )
            
            # Handle 404 (tool not found)
            if response.status_code == 404:
                raise MCPToolNotFoundError(f"Tool '{tool_name}' not found")
            
            # Handle 400 (validation error) - don't retry
            if response.status_code == 400:
                error_detail = response.json().get("detail", "Invalid parameters")
                raise MCPClientError(f"Invalid tool parameters: {error_detail}")
            
            response.raise_for_status()
            
            # Parse response
            tool_response = MCPToolResponse(**response.json())
            
            # Check if tool execution was successful
            if not tool_response.success:
                error_msg = tool_response.error or "Unknown error"
                logger.error(
                    f"Tool execution failed",
                    extra={
                        "tool_name": tool_name,
                        "error": error_msg,
                        "trace_id": trace_id
                    }
                )
                raise MCPToolExecutionError(f"Tool execution failed: {error_msg}")
            
            logger.info(
                f"Tool execution successful",
                extra={
                    "tool_name": tool_name,
                    "trace_id": trace_id
                }
            )
            
            return tool_response.result
            
        except (MCPToolNotFoundError, MCPClientError):
            # Don't retry these errors
            raise
            
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.error(
                f"Network error while calling tool",
                extra={
                    "tool_name": tool_name,
                    "error": str(e),
                    "trace_id": trace_id
                },
                exc_info=True
            )
            raise MCPConnectionError(f"Failed to connect to MCP service: {str(e)}") from e
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error while calling tool",
                extra={
                    "tool_name": tool_name,
                    "status_code": e.response.status_code,
                    "error": str(e),
                    "trace_id": trace_id
                },
                exc_info=True
            )
            raise MCPClientError(f"Failed to call tool: {str(e)}") from e
            
        except Exception as e:
            logger.error(
                f"Unexpected error while calling tool",
                extra={
                    "tool_name": tool_name,
                    "error": str(e),
                    "trace_id": trace_id
                },
                exc_info=True
            )
            raise MCPClientError(f"Unexpected error: {str(e)}") from e
    
    def get_retry_info(self) -> Dict[str, Any]:
        """
        Get information about retry configuration.
        
        Returns:
            dict: Retry configuration details
        """
        return {
            "max_retries": self.max_retries,
            "retry_strategy": "exponential_backoff",
            "backoff_multiplier": 1,
            "min_wait_seconds": 1,
            "max_wait_seconds": 10,
            "retryable_errors": [
                "TimeoutException",
                "NetworkError",
                "MCPConnectionError"
            ]
        }


# Global MCP client instance
# This can be configured with environment variables
mcp_client = MCPClient(
    base_url=getattr(settings, "mcp_service_url", "http://localhost:8001"),
    timeout=30.0,
    max_retries=settings.mcp_tool_retry_attempts
)


async def get_mcp_client() -> MCPClient:
    """
    Dependency injection function for FastAPI endpoints.
    
    Returns:
        MCPClient: Global MCP client instance
    """
    return mcp_client
