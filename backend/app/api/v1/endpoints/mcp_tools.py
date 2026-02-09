"""
MCP (Model Context Protocol) tool endpoints.

This module defines the MCP protocol endpoints for tool discovery and invocation.
Provides the search_framework_docs tool for semantic documentation search.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.mcp import (
    MCPToolDefinition,
    MCPToolInputSchema,
    MCPToolListResponse,
    MCPToolRequest,
    MCPToolResponse,
)

router = APIRouter()


def get_tool_definitions() -> Dict[str, MCPToolDefinition]:
    """
    Get all available MCP tool definitions.
    
    Returns:
        Dict[str, MCPToolDefinition]: Dictionary mapping tool names to definitions
    """
    return {
        "search_framework_docs": MCPToolDefinition(
            name="search_framework_docs",
            description=(
                "Search framework documentation (NestJS, React, FastAPI, Spring Boot, "
                ".NET Core, Vue.js, Angular, Django, Express.js, and others) using "
                "semantic similarity. Returns relevant documentation excerpts with "
                "relevance scores."
            ),
            inputSchema=MCPToolInputSchema(
                type="object",
                properties={
                    "query": {
                        "type": "string",
                        "description": "Search query text for finding relevant documentation"
                    },
                    "frameworks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional list of framework names to filter results "
                            "(e.g., ['NestJS', 'React', 'FastAPI'])"
                        )
                    },
                    "top_k": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of results to return (default: 10)"
                    },
                    "min_score": {
                        "type": "number",
                        "default": 0.7,
                        "description": "Minimum similarity score threshold 0.0-1.0 (default: 0.7)"
                    }
                },
                required=["query"]
            )
        )
    }


@router.get(
    "/tools",
    response_model=MCPToolListResponse,
    status_code=status.HTTP_200_OK,
    summary="List available MCP tools",
    description="Get a list of all available MCP tools with their definitions and input schemas.",
    responses={
        200: {
            "description": "List of available tools retrieved successfully",
            "model": MCPToolListResponse,
        }
    },
)
async def list_tools() -> MCPToolListResponse:
    """
    List all available MCP tools.
    
    Returns tool definitions including names, descriptions, and input schemas
    following the MCP protocol specification.
    
    Returns:
        MCPToolListResponse: List of available tools with their definitions
        
    Example:
        >>> GET /api/v1/mcp/tools
        {
            "tools": [
                {
                    "name": "search_framework_docs",
                    "description": "Search framework documentation...",
                    "inputSchema": {...}
                }
            ]
        }
    """
    tool_definitions = get_tool_definitions()
    return MCPToolListResponse(tools=list(tool_definitions.values()))


@router.post(
    "/tools/invoke",
    response_model=MCPToolResponse,
    status_code=status.HTTP_200_OK,
    summary="Invoke an MCP tool",
    description="Execute an MCP tool with the specified parameters.",
    responses={
        200: {
            "description": "Tool executed successfully",
            "model": MCPToolResponse,
        },
        400: {
            "description": "Invalid request - tool not found or invalid parameters",
            "content": {
                "application/json": {
                    "examples": {
                        "tool_not_found": {
                            "summary": "Tool not found",
                            "value": {"detail": "Tool 'unknown_tool' not found"}
                        },
                        "invalid_params": {
                            "summary": "Invalid parameters",
                            "value": {"detail": "Missing required parameter: query"}
                        }
                    }
                }
            }
        },
        500: {
            "description": "Tool execution failed",
            "content": {
                "application/json": {
                    "example": {"detail": "Tool execution error: ..."}
                }
            }
        }
    },
)
async def invoke_tool(request: MCPToolRequest) -> MCPToolResponse:
    """
    Invoke an MCP tool with specified parameters.
    
    Executes the requested tool and returns the result. Currently supports
    the search_framework_docs tool for semantic documentation search.
    
    Args:
        request: Tool invocation request with tool name and parameters
        
    Returns:
        MCPToolResponse: Tool execution result with success status
        
    Raises:
        HTTPException 400: If tool not found or parameters invalid
        HTTPException 500: If tool execution fails
        
    Example:
        >>> POST /api/v1/mcp/tools/invoke
        {
            "tool_name": "search_framework_docs",
            "parameters": {
                "query": "How to create a controller in NestJS",
                "frameworks": ["NestJS"],
                "top_k": 5
            }
        }
    """
    # Get available tools
    tool_definitions = get_tool_definitions()
    
    # Validate tool exists
    if request.tool_name not in tool_definitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool '{request.tool_name}' not found. Available tools: {list(tool_definitions.keys())}"
        )
    
    # Route to appropriate tool handler
    try:
        if request.tool_name == "search_framework_docs":
            # Import here to avoid circular dependencies
            from app.agents.documentation_search_agent import get_documentation_search_agent
            
            agent = await get_documentation_search_agent()
            result = await agent.search_docs(**request.parameters)
            
            # Convert DocumentationResult objects to dicts for JSON serialization
            result_dicts = [
                {
                    "content": r.content,
                    "score": r.score,
                    "metadata": r.metadata,
                    "source": r.source,
                    "framework": r.framework
                }
                for r in result
            ]
            
            return MCPToolResponse(
                tool_name=request.tool_name,
                result=result_dicts,
                success=True,
                error=None
            )
        else:
            # Should not reach here due to validation above
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tool '{request.tool_name}' is not implemented"
            )
            
    except ValueError as e:
        # Parameter validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameters: {str(e)}"
        )
    except Exception as e:
        # Tool execution errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Tool execution error for {request.tool_name}: {e}", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution error: {str(e)}"
        )


@router.get(
    "/tools/{tool_name}",
    response_model=MCPToolDefinition,
    status_code=status.HTTP_200_OK,
    summary="Get tool definition",
    description="Get the definition and input schema for a specific MCP tool.",
    responses={
        200: {
            "description": "Tool definition retrieved successfully",
            "model": MCPToolDefinition,
        },
        404: {
            "description": "Tool not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Tool 'unknown_tool' not found"}
                }
            }
        }
    },
)
async def get_tool(tool_name: str) -> MCPToolDefinition:
    """
    Get definition for a specific MCP tool.
    
    Returns the tool's description and input schema.
    
    Args:
        tool_name: Name of the tool to retrieve
        
    Returns:
        MCPToolDefinition: Tool definition with input schema
        
    Raises:
        HTTPException 404: If tool not found
        
    Example:
        >>> GET /api/v1/mcp/tools/search_framework_docs
        {
            "name": "search_framework_docs",
            "description": "Search framework documentation...",
            "inputSchema": {...}
        }
    """
    tool_definitions = get_tool_definitions()
    
    if tool_name not in tool_definitions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' not found. Available tools: {list(tool_definitions.keys())}"
        )
    
    return tool_definitions[tool_name]
