"""
AI Agent Pydantic schemas for request validation and response serialization.

This module defines all request and response schemas for the AI Agent System,
including agent requests, responses, documentation results, code generation results,
cached responses, routing strategies, and workflow state.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict

from pydantic import BaseModel, Field


class RoutingStrategy(str, Enum):
    """Enum for agent routing strategies.
    
    Defines how the supervisor agent routes requests to specialized agents.
    """
    
    SEARCH_ONLY = "search_only"
    CODE_ONLY = "code_only"
    SEARCH_THEN_CODE = "search_then_code"
    PARALLEL = "parallel"  # Future: parallel execution


class AgentRequest(BaseModel):
    """Request schema for AI agent queries.
    
    Validates incoming requests with prompt length constraints and optional context.
    """
    
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User prompt for the AI agent",
        examples=["Create a NestJS controller for user authentication"]
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional context information for the request",
        examples=[{"framework": "NestJS", "language": "TypeScript"}]
    )
    trace_id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for request tracing",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    max_iterations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of workflow iterations",
        examples=[3]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "prompt": "Create a NestJS controller for user authentication",
                    "context": {"framework": "NestJS"},
                    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                    "max_iterations": 3
                }
            ]
        }
    }


class ResponseMetadata(BaseModel):
    """Metadata for agent responses.
    
    Contains tracing, performance, and execution information.
    """
    
    trace_id: str = Field(
        ...,
        description="Unique identifier for request tracing",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    cache_hit: bool = Field(
        ...,
        description="Whether the response was served from cache",
        examples=[False]
    )
    processing_time_ms: float = Field(
        ...,
        description="Total processing time in milliseconds",
        examples=[1234.56]
    )
    tokens_used: int = Field(
        ...,
        description="Total tokens consumed by LLM calls",
        examples=[500]
    )
    agents_invoked: List[str] = Field(
        ...,
        description="List of agents invoked during processing",
        examples=[["supervisor", "documentation_search", "code_gen"]]
    )
    workflow_iterations: int = Field(
        ...,
        description="Number of workflow cycles executed",
        examples=[1]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                    "cache_hit": False,
                    "processing_time_ms": 1234.56,
                    "tokens_used": 500,
                    "agents_invoked": ["supervisor", "documentation_search", "code_gen"],
                    "workflow_iterations": 1
                }
            ]
        }
    }


class AgentResponse(BaseModel):
    """Response schema for AI agent queries.
    
    Contains the generated result and comprehensive metadata.
    """
    
    result: str = Field(
        ...,
        description="Generated result from the AI agent",
        examples=["@Controller('auth')\nexport class AuthController { ... }"]
    )
    metadata: ResponseMetadata = Field(
        ...,
        description="Response metadata including tracing and performance info"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "result": "@Controller('auth')\nexport class AuthController { ... }",
                    "metadata": {
                        "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                        "cache_hit": False,
                        "processing_time_ms": 1234.56,
                        "tokens_used": 500,
                        "agents_invoked": ["supervisor", "documentation_search", "code_gen"],
                        "workflow_iterations": 1
                    }
                }
            ]
        }
    }


class DocumentationResult(BaseModel):
    """Schema for documentation search results.
    
    Represents a single documentation excerpt with relevance score and metadata.
    """
    
    content: str = Field(
        ...,
        description="Documentation content excerpt",
        examples=["@Controller() decorator is used to define a basic controller in NestJS..."]
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score between 0.0 and 1.0",
        examples=[0.92]
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the documentation",
        examples=[{"section": "Controllers", "version": "10.x"}]
    )
    source: str = Field(
        ...,
        description="Documentation source URL or file path",
        examples=["https://docs.nestjs.com/controllers"]
    )
    framework: str = Field(
        ...,
        description="Framework name (e.g., NestJS, React, FastAPI)",
        examples=["NestJS"]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "content": "@Controller() decorator is used to define a basic controller in NestJS...",
                    "score": 0.92,
                    "metadata": {"section": "Controllers", "version": "10.x"},
                    "source": "https://docs.nestjs.com/controllers",
                    "framework": "NestJS"
                }
            ]
        }
    }


class CodeGenerationResult(BaseModel):
    """Schema for code generation results.
    
    Contains generated code with syntax validation and metadata.
    """
    
    code: str = Field(
        ...,
        description="Generated code",
        examples=["@Controller('users')\nexport class UsersController { ... }"]
    )
    language: str = Field(
        ...,
        description="Programming language of the generated code",
        examples=["TypeScript"]
    )
    framework: Optional[str] = Field(
        default=None,
        description="Framework used (e.g., NestJS, React, FastAPI)",
        examples=["NestJS"]
    )
    syntax_valid: bool = Field(
        ...,
        description="Whether the generated code is syntactically valid",
        examples=[True]
    )
    validation_errors: List[str] = Field(
        default_factory=list,
        description="List of syntax validation errors if any",
        examples=[[]]
    )
    tokens_used: int = Field(
        ...,
        description="Number of tokens used for code generation",
        examples=[350]
    )
    documentation_sources: List[str] = Field(
        default_factory=list,
        description="URLs/sources of documentation used for generation",
        examples=[["https://docs.nestjs.com/controllers"]]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "@Controller('users')\nexport class UsersController { ... }",
                    "language": "TypeScript",
                    "framework": "NestJS",
                    "syntax_valid": True,
                    "validation_errors": [],
                    "tokens_used": 350,
                    "documentation_sources": ["https://docs.nestjs.com/controllers"]
                }
            ]
        }
    }


class CachedResponse(BaseModel):
    """Schema for cached agent responses.
    
    Stores response with embedding for semantic similarity matching.
    """
    
    response: str = Field(
        ...,
        description="Cached response content",
        examples=["@Controller('auth')\nexport class AuthController { ... }"]
    )
    embedding: List[float] = Field(
        ...,
        description="1536-dimensional embedding vector for similarity search",
        examples=[[0.123, -0.456, 0.789]]
    )
    similarity_score: float = Field(
        ...,
        description="Similarity score when retrieved from cache",
        examples=[0.97]
    )
    cached_at: datetime = Field(
        ...,
        description="Timestamp when the response was cached",
        examples=["2024-01-15T10:30:00Z"]
    )
    ttl: int = Field(
        ...,
        description="Time-to-live in seconds",
        examples=[3600]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "@Controller('auth')\nexport class AuthController { ... }",
                    "embedding": [0.123, -0.456, 0.789],
                    "similarity_score": 0.97,
                    "cached_at": "2024-01-15T10:30:00Z",
                    "ttl": 3600
                }
            ]
        }
    }


class WorkflowState(TypedDict, total=False):
    """TypedDict for LangGraph workflow state.
    
    Maintains state across agent transitions in the workflow.
    Note: Using TypedDict for LangGraph compatibility.
    """
    
    prompt: str
    routing_strategy: RoutingStrategy
    documentation_results: Optional[List[DocumentationResult]]
    generated_code: Optional[str]
    code_generation_result: Optional[CodeGenerationResult]
    framework: Optional[str]
    iteration_count: int
    max_iterations: int
    trace_id: str
    errors: List[str]
