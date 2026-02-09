"""
Supervisor Agent for intelligent routing of user prompts to specialized agents.

This module implements the Supervisor Agent that analyzes incoming prompts and
delegates work to specialized agents (Documentation Search Agent and Code Generation
Agent) based on the prompt's intent and requirements.
"""

import uuid
from typing import Optional

from openai import AsyncOpenAI
import openai

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.telemetry import get_tracer, add_span_attributes
from app.schemas.agent import AgentResponse, ResponseMetadata, RoutingStrategy
from app.utils.retry import llm_api_retry

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class SupervisorAgent:
    """
    Supervisor agent for analyzing prompts and routing to specialized agents.
    
    This agent analyzes incoming user prompts to determine the appropriate routing
    strategy (search-only, code-only, or search-then-code) and delegates work to
    specialized agents. It uses LLM with structured output to classify prompt intent
    and logs all routing decisions for observability.
    
    Attributes:
        client: AsyncOpenAI client for LLM API calls
        model: LLM model name (default: gpt-4)
    """
    
    def __init__(
        self,
        client: Optional[AsyncOpenAI] = None,
        model: str = "gpt-4"
    ):
        """
        Initialize the Supervisor Agent.
        
        Args:
            client: AsyncOpenAI client instance (creates new if None)
            model: LLM model name (default: gpt-4)
        """
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = model
    
    async def analyze_and_route(
        self,
        prompt: str,
        trace_id: str
    ) -> AgentResponse:
        """
        Analyze prompt and route to appropriate agents.
        
        This is the main entry point for the supervisor agent. It determines the
        routing strategy, invokes the appropriate specialized agents, and returns
        the final response with comprehensive metadata.
        
        Args:
            prompt: User's input prompt
            trace_id: Unique identifier for request tracing
            
        Returns:
            AgentResponse: Final response with result and metadata
            
        Raises:
            ValueError: If prompt is empty
            ConnectionError: If LLM API call fails
            
        Example:
            >>> supervisor = SupervisorAgent()
            >>> response = await supervisor.analyze_and_route(
            ...     "Create a NestJS controller for user authentication",
            ...     trace_id="550e8400-e29b-41d4-a716-446655440000"
            ... )
            >>> print(response.result)
            >>> print(response.metadata.routing_strategy)
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        logger.info(
            "supervisor_agent_started",
            trace_id=trace_id,
            prompt_length=len(prompt)
        )
        
        # Determine routing strategy
        routing_strategy = await self.determine_routing_strategy(prompt, trace_id)
        
        logger.info(
            "routing_decision_made",
            trace_id=trace_id,
            routing_strategy=routing_strategy.value,
            prompt_preview=prompt[:100]  # Log first 100 chars for context
        )
        
        # TODO: Implement actual agent invocation based on routing strategy
        # This will be implemented in Task 11 (LangGraph workflow orchestration)
        # For now, return a placeholder response
        
        result = f"[Supervisor Agent] Routing strategy determined: {routing_strategy.value}\n"
        result += f"Prompt: {prompt}\n"
        result += "Note: Full agent orchestration will be implemented in Task 11"
        
        # Create response metadata
        metadata = ResponseMetadata(
            trace_id=trace_id,
            cache_hit=False,
            processing_time_ms=0.0,  # Will be calculated in actual implementation
            tokens_used=0,  # Will be tracked in actual implementation
            agents_invoked=["supervisor"],
            workflow_iterations=0
        )
        
        return AgentResponse(
            result=result,
            metadata=metadata
        )
    
    async def determine_routing_strategy(
        self,
        prompt: str,
        trace_id: Optional[str] = None
    ) -> RoutingStrategy:
        """
        Determine which agents to invoke based on prompt analysis.
        
        Uses LLM with structured output to classify the prompt intent and determine
        the appropriate routing strategy. The LLM analyzes whether the prompt requires:
        - Documentation search only (SEARCH_ONLY)
        - Code generation only (CODE_ONLY)
        - Both search and code generation (SEARCH_THEN_CODE)
        
        Args:
            prompt: User's input prompt
            trace_id: Optional unique identifier for request tracing
            
        Returns:
            RoutingStrategy: Enum indicating the routing decision
            
        Raises:
            ValueError: If prompt is empty
            ConnectionError: If LLM API call fails after retries
            
        Example:
            >>> supervisor = SupervisorAgent()
            >>> strategy = await supervisor.determine_routing_strategy(
            ...     "How do I create a controller in NestJS?"
            ... )
            >>> print(strategy)
            RoutingStrategy.SEARCH_ONLY
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        if trace_id is None:
            trace_id = str(uuid.uuid4())
        
        # Start OpenTelemetry span for routing decision
        with tracer.start_as_current_span("supervisor_determine_routing") as span:
            add_span_attributes(
                span,
                trace_id=trace_id,
                prompt_length=len(prompt),
                agent_type="supervisor"
            )
            
            logger.info(
                "determining_routing_strategy",
                trace_id=trace_id,
                prompt_length=len(prompt)
            )
        
        # Build system prompt for routing classification
        system_prompt = """You are a routing classifier for an AI agent system. Your job is to analyze user prompts and determine the appropriate routing strategy.

Available routing strategies:
1. SEARCH_ONLY: User is asking questions about documentation, seeking information, or wants to learn about a framework/concept
2. CODE_ONLY: User explicitly wants code generation without needing documentation context (e.g., simple code tasks, refactoring)
3. SEARCH_THEN_CODE: User wants code generation that requires framework documentation context (e.g., framework-specific implementations)

Guidelines:
- If the prompt contains questions like "how to", "what is", "explain", "documentation" → SEARCH_ONLY
- If the prompt explicitly asks for code generation with framework-specific requirements → SEARCH_THEN_CODE
- If the prompt asks for simple code without framework context → CODE_ONLY
- When in doubt between CODE_ONLY and SEARCH_THEN_CODE, prefer SEARCH_THEN_CODE for better results

Respond with ONLY one of these exact values: SEARCH_ONLY, CODE_ONLY, or SEARCH_THEN_CODE"""
        
        user_prompt = f"""Analyze this prompt and determine the routing strategy:

Prompt: {prompt}

Routing strategy:"""
        
        try:
            # Call LLM for classification with retry logic
            @llm_api_retry
            async def _call_llm():
                return await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0,  # Deterministic for classification
                    max_tokens=50
                )
            
            response = await _call_llm()
            
            classification = response.choices[0].message.content.strip().upper()
            tokens_used = response.usage.total_tokens
            
            # Add span attributes for LLM call
            add_span_attributes(
                span,
                tokens_used=tokens_used,
                classification=classification,
                model=self.model
            )
            
            logger.info(
                "llm_classification_received",
                trace_id=trace_id,
                classification=classification,
                tokens_used=tokens_used
            )
            
            # Parse classification to RoutingStrategy enum
            if "SEARCH_ONLY" in classification or "SEARCH ONLY" in classification:
                strategy = RoutingStrategy.SEARCH_ONLY
            elif "CODE_ONLY" in classification or "CODE ONLY" in classification:
                strategy = RoutingStrategy.CODE_ONLY
            elif "SEARCH_THEN_CODE" in classification or "SEARCH THEN CODE" in classification:
                strategy = RoutingStrategy.SEARCH_THEN_CODE
            else:
                # Default to SEARCH_THEN_CODE for safety (provides most context)
                logger.warning(
                    "classification_parse_failed",
                    trace_id=trace_id,
                    classification=classification,
                    fallback="SEARCH_THEN_CODE"
                )
                strategy = RoutingStrategy.SEARCH_THEN_CODE
            
            # Add final routing strategy to span
            add_span_attributes(span, routing_strategy=strategy.value)
            
            logger.info(
                "routing_strategy_determined",
                trace_id=trace_id,
                strategy=strategy.value,
                tokens_used=tokens_used
            )
            
            return strategy
            
        except (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError) as e:
            # LLM API specific errors - log with trace_id and return error
            logger.error(
                "llm_api_error",
                trace_id=trace_id,
                error_type=type(e).__name__,
                error=str(e),
                operation="routing_strategy_determination",
                exc_info=True
            )
            raise ConnectionError(
                f"LLM API failed after retries (trace_id: {trace_id}): {type(e).__name__} - {str(e)}"
            )
        except Exception as e:
            # Unexpected errors - log with trace_id
            logger.error(
                "unexpected_error",
                trace_id=trace_id,
                error_type=type(e).__name__,
                error=str(e),
                operation="routing_strategy_determination",
                exc_info=True
            )
            raise ConnectionError(
                f"Failed to determine routing strategy (trace_id: {trace_id}): {str(e)}"
            )
    
    def get_agent_info(self) -> dict:
        """
        Get information about the agent configuration.
        
        Returns:
            dict: Agent configuration including model and supported strategies
        """
        return {
            "agent_type": "supervisor",
            "model": self.model,
            "supported_strategies": [
                "SEARCH_ONLY",
                "CODE_ONLY",
                "SEARCH_THEN_CODE",
                "PARALLEL"
            ]
        }


# Global supervisor agent instance
supervisor_agent = SupervisorAgent()


async def get_supervisor_agent() -> SupervisorAgent:
    """
    Dependency injection function for FastAPI endpoints.
    
    Returns:
        SupervisorAgent: Global supervisor agent instance
    """
    return supervisor_agent
