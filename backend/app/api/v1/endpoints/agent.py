"""
AI Agent query endpoint.

This module implements the /api/v1/agent/query endpoint that handles
user prompts, integrates semantic caching, and orchestrates the agent workflow.
"""

import time
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.logging_config import get_logger
from app.core.telemetry import get_tracer, add_span_attributes
from app.schemas.agent import AgentRequest, AgentResponse, ResponseMetadata
from app.services.semantic_cache import semantic_cache
from app.services.embedding_service import embedding_service
from app.services.framework_detector import extract_context_from_prompt
from app.workflows.agent_workflow import agent_workflow

logger = get_logger(__name__)
tracer = get_tracer(__name__)

router = APIRouter()


@router.post(
    "/query",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Query AI Agent",
    description="""
    Submit a prompt to the AI Agent System for processing.
    
    The system will:
    1. Check semantic cache for similar previous queries
    2. If cache miss, route the request through the supervisor agent
    3. Execute appropriate specialized agents (documentation search, code generation)
    4. Return the result with comprehensive metadata
    
    **Features:**
    - Semantic caching for fast responses to similar queries
    - Multi-agent orchestration with LangGraph
    - Framework-specific documentation search (NestJS, React, FastAPI, etc.)
    - Syntactically valid code generation
    - Comprehensive observability with tracing and logging
    """,
    responses={
        200: {
            "description": "Successful response with agent result",
            "content": {
                "application/json": {
                    "example": {
                        "result": "@Controller('auth')\\nexport class AuthController { ... }",
                        "metadata": {
                            "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                            "cache_hit": False,
                            "processing_time_ms": 1234.56,
                            "tokens_used": 500,
                            "agents_invoked": ["supervisor", "documentation_search", "code_gen"],
                            "workflow_iterations": 1
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid request (e.g., prompt too long, invalid parameters)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Prompt exceeds maximum length of 10000 characters"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An internal server error occurred"
                    }
                }
            }
        },
        503: {
            "description": "Service unavailable (e.g., LLM API down, database unavailable)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Service temporarily unavailable. Please try again later."
                    }
                }
            }
        },
        504: {
            "description": "Gateway timeout (e.g., workflow execution timeout)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Request timeout. The operation took too long to complete."
                    }
                }
            }
        }
    }
)
async def query_agent(request: AgentRequest) -> AgentResponse:
    """
    Process an AI agent query with semantic caching and workflow orchestration.
    
    This endpoint implements the complete agent query flow:
    1. Auto-detect framework and context from prompt (if not provided)
    2. Semantic cache check (similarity threshold 0.95)
    3. Supervisor agent routing
    4. Specialized agent execution (search, code generation)
    5. Response caching for future similar queries
    
    Args:
        request: AgentRequest with prompt (context auto-detected if not provided)
        
    Returns:
        AgentResponse: Result with comprehensive metadata
        
    Raises:
        HTTPException: 400 for invalid requests, 500 for server errors,
                      503 for service unavailable, 504 for timeouts
    """
    start_time = time.time()
    
    # Generate trace_id if not provided
    trace_id = request.trace_id or str(uuid.uuid4())
    
    # Set default max_iterations if not provided
    max_iterations = request.max_iterations or 3
    
    # Auto-detect context from prompt if not provided
    if not request.context:
        detected_context = extract_context_from_prompt(request.prompt)
        request.context = detected_context if detected_context else {}
        
        logger.info(
            "context_auto_detected",
            trace_id=trace_id,
            detected_context=request.context,
            prompt_preview=request.prompt[:100]
        )
    
    # Start OpenTelemetry span
    with tracer.start_as_current_span("agent_query_endpoint") as span:
        add_span_attributes(
            span,
            trace_id=trace_id,
            prompt_length=len(request.prompt),
            max_iterations=max_iterations,
            has_context=bool(request.context),
            framework=request.context.get("framework", "unknown") if request.context else "unknown"
        )
        
        logger.info(
            "agent_query_received",
            trace_id=trace_id,
            prompt_length=len(request.prompt),
            max_iterations=max_iterations,
            context=request.context
        )
        
        try:
            # Step 1: Check semantic cache
            cache_result = None
            cache_hit = False
            
            try:
                # Generate embedding for cache lookup
                embedding = await embedding_service.embed_text(request.prompt)
                
                # Check cache with embedding
                cache_result = await semantic_cache.get_with_embedding(
                    prompt=request.prompt,
                    embedding=embedding,
                    similarity_threshold=0.95
                )
                
                if cache_result:
                    cache_hit = True
                    processing_time_ms = (time.time() - start_time) * 1000
                    
                    logger.info(
                        "semantic_cache_hit",
                        trace_id=trace_id,
                        similarity_score=cache_result.similarity_score,
                        processing_time_ms=processing_time_ms
                    )
                    
                    # Add span attributes for cache hit
                    add_span_attributes(
                        span,
                        cache_hit=True,
                        similarity_score=cache_result.similarity_score,
                        processing_time_ms=processing_time_ms
                    )
                    
                    # Return cached response
                    metadata = ResponseMetadata(
                        trace_id=trace_id,
                        cache_hit=True,
                        processing_time_ms=processing_time_ms,
                        tokens_used=0,  # No tokens used for cache hit
                        agents_invoked=[],
                        workflow_iterations=0
                    )
                    
                    return AgentResponse(
                        result=cache_result.response,
                        metadata=metadata
                    )
                else:
                    logger.info(
                        "semantic_cache_miss",
                        trace_id=trace_id,
                        prompt_preview=request.prompt[:50]
                    )
                    
            except Exception as cache_error:
                # Graceful degradation: log cache error but continue processing
                logger.warning(
                    "semantic_cache_error",
                    trace_id=trace_id,
                    error=str(cache_error),
                    error_type=type(cache_error).__name__,
                    message="Continuing without cache"
                )
                embedding = None  # Will regenerate if needed for caching later
            
            # Step 2: Execute workflow (cache miss or cache error)
            logger.info(
                "workflow_execution_starting",
                trace_id=trace_id,
                reason="cache_miss" if not cache_hit else "cache_error"
            )
            
            # Execute agent workflow
            response = await agent_workflow.execute(
                prompt=request.prompt,
                trace_id=trace_id,
                context=request.context,
                max_iterations=max_iterations
            )
            
            # Step 3: Cache the response for future queries
            try:
                # Generate embedding if not already done
                if embedding is None:
                    embedding = await embedding_service.embed_text(request.prompt)
                
                # Store in semantic cache
                await semantic_cache.set(
                    prompt=request.prompt,
                    response=response.result,
                    embedding=embedding,
                    ttl=3600  # 1 hour TTL
                )
                
                logger.info(
                    "response_cached",
                    trace_id=trace_id,
                    ttl=3600
                )
                
            except Exception as cache_error:
                # Graceful degradation: log cache error but return response
                logger.warning(
                    "response_caching_failed",
                    trace_id=trace_id,
                    error=str(cache_error),
                    error_type=type(cache_error).__name__,
                    message="Response not cached but returning result"
                )
            
            # Calculate total processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Update response metadata with actual processing time
            response.metadata.processing_time_ms = processing_time_ms
            
            # Add final span attributes
            add_span_attributes(
                span,
                cache_hit=False,
                processing_time_ms=processing_time_ms,
                tokens_used=response.metadata.tokens_used,
                workflow_iterations=response.metadata.workflow_iterations,
                agents_invoked=",".join(response.metadata.agents_invoked)
            )
            
            logger.info(
                "agent_query_complete",
                trace_id=trace_id,
                processing_time_ms=processing_time_ms,
                tokens_used=response.metadata.tokens_used,
                workflow_iterations=response.metadata.workflow_iterations,
                agents_invoked=response.metadata.agents_invoked
            )
            
            return response
            
        except ValueError as ve:
            # Client error (400)
            logger.warning(
                "agent_query_validation_error",
                trace_id=trace_id,
                error=str(ve),
                error_type="ValueError"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(ve)
            )
            
        except TimeoutError as te:
            # Gateway timeout (504)
            logger.error(
                "agent_query_timeout",
                trace_id=trace_id,
                error=str(te),
                processing_time_ms=(time.time() - start_time) * 1000
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timeout. The operation took too long to complete."
            )
            
        except ConnectionError as ce:
            # Service unavailable (503)
            logger.error(
                "agent_query_connection_error",
                trace_id=trace_id,
                error=str(ce),
                error_type="ConnectionError"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again later."
            )
            
        except Exception as e:
            # Internal server error (500)
            logger.error(
                "agent_query_error",
                trace_id=trace_id,
                error=str(e),
                error_type=type(e).__name__,
                processing_time_ms=(time.time() - start_time) * 1000,
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal server error occurred"
            )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Agent Service Health Check",
    description="Check the health status of the AI Agent service and its dependencies",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "semantic_cache": "connected",
                        "workflow": "ready"
                    }
                }
            }
        },
        503: {
            "description": "Service is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "semantic_cache": "disconnected",
                        "error": "Cache backend unavailable"
                    }
                }
            }
        }
    }
)
async def agent_health_check():
    """
    Health check endpoint for the AI Agent service.
    
    Verifies that the agent service and its dependencies are operational:
    - Semantic cache connectivity
    - Workflow readiness
    
    Returns:
        dict: Health status information
    """
    try:
        # Check semantic cache
        cache_healthy = semantic_cache.redis_client is not None and semantic_cache.pg_pool is not None
        
        # Check workflow
        workflow_healthy = agent_workflow.graph is not None
        
        if cache_healthy and workflow_healthy:
            return {
                "status": "healthy",
                "semantic_cache": "connected",
                "workflow": "ready"
            }
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "semantic_cache": "connected" if cache_healthy else "disconnected",
                    "workflow": "ready" if workflow_healthy else "not_ready"
                }
            )
            
    except Exception as e:
        logger.error(
            "agent_health_check_error",
            error=str(e),
            exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )
