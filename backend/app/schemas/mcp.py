"""
MCP (Model Context Protocol) schemas for tool definitions and communication.

This module defines the schemas for MCP tool interfaces, including tool
definitions, requests, and responses following the MCP protocol specification.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MCPToolInputSchema(BaseModel):
    """Schema definition for MCP tool input parameters.
    
    Defines the JSON schema for tool input validation.
    """
    
    type: str = Field(
        default="object",
        description="Schema type (typically 'object')"
    )
    properties: Dict[str, Any] = Field(
        ...,
        description="Property definitions for the tool parameters"
    )
    required: Optional[List[str]] = Field(
        default=None,
        description="List of required parameter names"
    )


class MCPToolDefinition(BaseModel):
    """MCP tool definition schema.
    
    Defines a tool that can be called by agents following the MCP protocol.
    """
    
    name: str = Field(
        ...,
        description="Unique tool name",
        examples=["search_framework_docs"]
    )
    description: str = Field(
        ...,
        description="Human-readable description of what the tool does",
        examples=["Search framework documentation using semantic similarity"]
    )
    inputSchema: MCPToolInputSchema = Field(
        ...,
        description="JSON schema for tool input parameters"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "search_framework_docs",
                    "description": "Search framework documentation (NestJS, React, FastAPI, etc.) using semantic similarity",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query text"
                            },
                            "frameworks": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional filter for specific frameworks"
                            },
                            "top_k": {
                                "type": "integer",
                                "default": 10,
                                "description": "Maximum number of results to return"
                            },
                            "min_score": {
                                "type": "number",
                                "default": 0.7,
                                "description": "Minimum similarity score threshold"
                            }
                        },
                        "required": ["query"]
                    }
                }
            ]
        }
    }


class MCPToolRequest(BaseModel):
    """Request schema for MCP tool invocation.
    
    Represents a request to execute an MCP tool with specific parameters.
    """
    
    tool_name: str = Field(
        ...,
        description="Name of the tool to invoke",
        examples=["search_framework_docs"]
    )
    parameters: Dict[str, Any] = Field(
        ...,
        description="Tool parameters matching the tool's input schema",
        examples=[{
            "query": "How to create a controller in NestJS",
            "frameworks": ["NestJS"],
            "top_k": 10,
            "min_score": 0.7
        }]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tool_name": "search_framework_docs",
                    "parameters": {
                        "query": "How to create a controller in NestJS",
                        "frameworks": ["NestJS"],
                        "top_k": 10,
                        "min_score": 0.7
                    }
                }
            ]
        }
    }


class MCPToolResponse(BaseModel):
    """Response schema for MCP tool invocation.
    
    Contains the result of tool execution and metadata.
    """
    
    tool_name: str = Field(
        ...,
        description="Name of the tool that was invoked",
        examples=["search_framework_docs"]
    )
    result: Any = Field(
        ...,
        description="Tool execution result (structure depends on tool)",
        examples=[[{
            "content": "@Controller() decorator is used...",
            "score": 0.92,
            "framework": "NestJS",
            "source": "https://docs.nestjs.com/controllers"
        }]]
    )
    success: bool = Field(
        ...,
        description="Whether the tool execution was successful",
        examples=[True]
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if execution failed",
        examples=[None]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tool_name": "search_framework_docs",
                    "result": [{
                        "content": "@Controller() decorator is used to define a basic controller in NestJS...",
                        "score": 0.92,
                        "framework": "NestJS",
                        "source": "https://docs.nestjs.com/controllers",
                        "metadata": {"section": "Controllers", "version": "10.x"}
                    }],
                    "success": True,
                    "error": None
                }
            ]
        }
    }


class MCPToolListResponse(BaseModel):
    """Response schema for listing available MCP tools.
    
    Returns a list of all available tools with their definitions.
    """
    
    tools: List[MCPToolDefinition] = Field(
        ...,
        description="List of available MCP tools"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tools": [{
                        "name": "search_framework_docs",
                        "description": "Search framework documentation using semantic similarity",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "frameworks": {"type": "array", "items": {"type": "string"}},
                                "top_k": {"type": "integer", "default": 10},
                                "min_score": {"type": "number", "default": 0.7}
                            },
                            "required": ["query"]
                        }
                    }]
                }
            ]
        }
    }
