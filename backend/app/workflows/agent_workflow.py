"""
LangGraph workflow orchestration for AI Agent System.

This module implements the LangGraph workflow that orchestrates the supervisor,
documentation search, and code generation agents with support for cycles and
state management.
"""

import time
from typing import Any, Dict, List, Literal, Optional

from langgraph.graph import END, StateGraph
from langchain_core.messages import HumanMessage

from app.agents.code_gen_agent import CodeGenAgent, code_gen_agent
from app.agents.documentation_search_agent import (
    DocumentationSearchAgent,
    documentation_search_agent,
)
from app.agents.supervisor_agent import SupervisorAgent, supervisor_agent
from app.core.logging_config import get_logger
from app.core.telemetry import get_tracer, add_span_attributes
from app.schemas.agent import (
    AgentResponse,
    CodeGenerationResult,
    DocumentationResult,
    ResponseMetadata,
    RoutingStrategy,
    WorkflowState,
)

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class AgentWorkflow:
    """
    LangGraph workflow for orchestrating AI agents.
    
    This class manages the workflow graph that routes requests through
    supervisor, documentation search, and code generation agents with
    support for iterative cycles and state persistence.
    
    Attributes:
        supervisor: Supervisor agent for routing decisions
        search_agent: Documentation search agent
        code_gen_agent: Code generation agent
        graph: Compiled LangGraph workflow
    """
    
    def __init__(
        self,
        supervisor_instance: Optional[SupervisorAgent] = None,
        search_agent_instance: Optional[DocumentationSearchAgent] = None,
        code_gen_agent_instance: Optional[CodeGenAgent] = None,
    ):
        """
        Initialize the agent workflow.
        
        Args:
            supervisor_instance: Supervisor agent instance
            search_agent_instance: Documentation search agent instance
            code_gen_agent_instance: Code generation agent instance
        """
        self.supervisor = supervisor_instance or supervisor_agent
        self.search_agent = search_agent_instance or documentation_search_agent
        self.code_gen_agent = code_gen_agent_instance or code_gen_agent
        
        # Build the workflow graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> Any:
        """
        Build the LangGraph workflow with nodes and edges.
        
        Creates a state graph with supervisor, search, code generation,
        and validation nodes, connected with conditional edges for routing.
        
        Returns:
            Compiled LangGraph workflow
        """
        # Create state graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("supervisor", self.supervisor_node)
        workflow.add_node("search", self.search_node)
        workflow.add_node("code_gen", self.code_gen_node)
        workflow.add_node("validate", self.validate_node)
        
        # Set entry point
        workflow.set_entry_point("supervisor")
        
        # Add conditional edges from supervisor
        workflow.add_conditional_edges(
            "supervisor",
            self.route_after_supervisor,
            {
                "search": "search",
                "code": "code_gen",
                "end": END
            }
        )
        
        # Add edge from search to code generation
        workflow.add_edge("search", "code_gen")
        
        # Add edge from code generation to validation
        workflow.add_edge("code_gen", "validate")
        
        # Add conditional edges from validation
        workflow.add_conditional_edges(
            "validate",
            self.should_retry,
            {
                "retry": "search",  # Cycle back for more context
                "done": END
            }
        )
        
        # Compile the graph
        return workflow.compile()
    
    async def supervisor_node(self, state: WorkflowState) -> WorkflowState:
        """
        Supervisor node: Analyze prompt and determine routing strategy.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with routing strategy
        """
        trace_id = state.get("trace_id")
        
        # Validate required state fields
        if not state.get("prompt"):
            logger.error("supervisor_node_missing_prompt", trace_id=trace_id)
            state.setdefault("errors", []).append("Missing required field: prompt")
            return state
        
        logger.info(
            "agent_transition",
            trace_id=trace_id,
            agent="supervisor",
            iteration=state.get("iteration_count", 0),
            operation="routing_decision"
        )
        
        try:
            # Determine routing strategy
            routing_strategy = await self.supervisor.determine_routing_strategy(
                state["prompt"],
                trace_id
            )
            
            # Update state
            state["routing_strategy"] = routing_strategy
            
            logger.info(
                "supervisor_routing_decision",
                trace_id=trace_id,
                routing_strategy=routing_strategy.value,
                iteration=state.get("iteration_count", 0)
            )
            
        except Exception as e:
            logger.error(
                "supervisor_node_error",
                trace_id=trace_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            state.setdefault("errors", []).append(f"Supervisor error: {str(e)}")
        
        return state
    
    async def search_node(self, state: WorkflowState) -> WorkflowState:
        """
        Search node: Perform documentation search.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with documentation results
        """
        trace_id = state.get("trace_id")
        
        # Validate required state fields
        if not state.get("prompt"):
            logger.error("search_node_missing_prompt", trace_id=trace_id)
            state.setdefault("errors", []).append("Missing required field: prompt")
            state["documentation_results"] = []
            return state
        
        logger.info(
            "agent_transition",
            trace_id=trace_id,
            agent="documentation_search",
            iteration=state.get("iteration_count", 0),
            operation="search_docs"
        )
        
        search_start_time = time.time()
        
        try:
            # Extract framework from prompt or state
            framework = state.get("framework")
            frameworks = [framework] if framework else None
            
            # Perform documentation search
            results = await self.search_agent.search_docs(
                query=state["prompt"],
                frameworks=frameworks,
                top_k=10,
                min_score=0.7
            )
            
            search_latency_ms = (time.time() - search_start_time) * 1000
            
            # Update state
            state["documentation_results"] = results
            
            logger.info(
                "search_node_complete",
                trace_id=trace_id,
                result_count=len(results),
                max_score=max(r.score for r in results) if results else 0,
                tool_call_latency=search_latency_ms,
                frameworks=frameworks
            )
            
        except Exception as e:
            logger.error(
                "search_node_error",
                trace_id=trace_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            state.setdefault("errors", []).append(f"Search error: {str(e)}")
            state["documentation_results"] = []
        
        return state
    
    async def code_gen_node(self, state: WorkflowState) -> WorkflowState:
        """
        Code generation node: Generate code with optional documentation context.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with generated code
        """
        trace_id = state.get("trace_id")
        
        # Validate required state fields
        if not state.get("prompt"):
            logger.error("code_gen_node_missing_prompt", trace_id=trace_id)
            state.setdefault("errors", []).append("Missing required field: prompt")
            state["generated_code"] = None
            return state
        
        logger.info(
            "agent_transition",
            trace_id=trace_id,
            agent="code_gen",
            iteration=state.get("iteration_count", 0),
            operation="generate_code",
            has_documentation_context=bool(state.get("documentation_results"))
        )
        
        code_gen_start_time = time.time()
        
        try:
            # Get documentation context if available
            doc_context = state.get("documentation_results")
            framework = state.get("framework")
            
            # Generate code
            result = await self.code_gen_agent.generate_code(
                prompt=state["prompt"],
                documentation_context=doc_context,
                framework=framework,
                trace_id=trace_id
            )
            
            code_gen_latency_ms = (time.time() - code_gen_start_time) * 1000
            
            # Update state
            state["generated_code"] = result.code
            state["code_generation_result"] = result
            
            logger.info(
                "code_generation_complete",
                trace_id=trace_id,
                syntax_valid=result.syntax_valid,
                language=result.language,
                tokens_used=result.tokens_used,
                tool_call_latency=code_gen_latency_ms,
                framework=framework
            )
            
        except Exception as e:
            logger.error(
                "code_gen_node_error",
                trace_id=trace_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            state.setdefault("errors", []).append(f"Code generation error: {str(e)}")
            state["generated_code"] = None
        
        return state
    
    def validate_node(self, state: WorkflowState) -> WorkflowState:
        """
        Validation node: Validate generated code and determine if retry is needed.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with validation results
        """
        # Validate state consistency
        if not state.get("trace_id"):
            logger.warning("Missing trace_id in state")
        
        if not state.get("prompt"):
            logger.error("Missing required field: prompt")
            state.setdefault("errors", []).append("Missing required field: prompt")
            return state
        
        logger.info(
            "Validation node executing",
            extra={
                "trace_id": state.get("trace_id"),
                "iteration": state.get("iteration_count", 0)
            }
        )
        
        try:
            # Increment iteration count
            state["iteration_count"] = state.get("iteration_count", 0) + 1
            
            # Ensure max_iterations is set
            if "max_iterations" not in state:
                state["max_iterations"] = 3
                logger.warning(
                    "max_iterations not set, defaulting to 3",
                    extra={"trace_id": state.get("trace_id")}
                )
            
            # Check if code was generated
            if not state.get("generated_code"):
                logger.warning(
                    "No code generated, marking as complete",
                    extra={"trace_id": state.get("trace_id")}
                )
                return state
            
            # Check code generation result
            code_result = state.get("code_generation_result")
            if code_result and not code_result.syntax_valid:
                logger.warning(
                    "Code has syntax errors",
                    extra={
                        "trace_id": state.get("trace_id"),
                        "errors": code_result.validation_errors
                    }
                )
                # Mark for potential retry if under max iterations
            
            logger.info(
                "Validation complete",
                extra={
                    "trace_id": state.get("trace_id"),
                    "iteration_count": state["iteration_count"],
                    "syntax_valid": code_result.syntax_valid if code_result else False
                }
            )
            
        except Exception as e:
            logger.error(
                "Validation node error",
                extra={
                    "trace_id": state.get("trace_id"),
                    "error": str(e)
                },
                exc_info=True
            )
            state.setdefault("errors", []).append(f"Validation error: {str(e)}")
        
        return state
    
    def route_after_supervisor(
        self, state: WorkflowState
    ) -> Literal["search", "code", "end"]:
        """
        Determine next node after supervisor based on routing strategy.
        
        Args:
            state: Current workflow state
            
        Returns:
            Next node name: "search", "code", or "end"
        """
        routing_strategy = state.get("routing_strategy")
        
        if not routing_strategy:
            logger.warning(
                "No routing strategy set, ending workflow",
                extra={"trace_id": state.get("trace_id")}
            )
            return "end"
        
        # Route based on strategy
        if routing_strategy == RoutingStrategy.SEARCH_ONLY:
            return "search"
        elif routing_strategy == RoutingStrategy.CODE_ONLY:
            return "code"
        elif routing_strategy == RoutingStrategy.SEARCH_THEN_CODE:
            return "search"
        else:
            logger.warning(
                f"Unknown routing strategy: {routing_strategy}, defaulting to search",
                extra={"trace_id": state.get("trace_id")}
            )
            return "search"
    
    def should_retry(self, state: WorkflowState) -> Literal["retry", "done"]:
        """
        Determine if workflow should retry (cycle back) or complete.
        
        Checks iteration count and code quality to decide if another
        cycle through search and code generation would be beneficial.
        
        Args:
            state: Current workflow state
            
        Returns:
            "retry" to cycle back to search, "done" to end workflow
        """
        iteration_count = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 3)
        
        # Check if max iterations reached
        if iteration_count >= max_iterations:
            logger.info(
                "Max iterations reached, ending workflow",
                extra={
                    "trace_id": state.get("trace_id"),
                    "iteration_count": iteration_count,
                    "max_iterations": max_iterations
                }
            )
            return "done"
        
        # Check if code has syntax errors and we should retry
        code_result = state.get("code_generation_result")
        if code_result and not code_result.syntax_valid:
            # Only retry if we have iterations left
            if iteration_count < max_iterations:
                logger.info(
                    "Code has syntax errors, retrying with more context",
                    extra={
                        "trace_id": state.get("trace_id"),
                        "iteration_count": iteration_count,
                        "errors": code_result.validation_errors
                    }
                )
                return "retry"
        
        # Check if routing was search-only (no code generation needed)
        routing_strategy = state.get("routing_strategy")
        if routing_strategy == RoutingStrategy.SEARCH_ONLY:
            logger.info(
                "Search-only workflow complete",
                extra={"trace_id": state.get("trace_id")}
            )
            return "done"
        
        # Default: workflow complete
        logger.info(
            "Workflow complete",
            extra={
                "trace_id": state.get("trace_id"),
                "iteration_count": iteration_count
            }
        )
        return "done"
    
    async def execute(
        self,
        prompt: str,
        trace_id: str,
        context: Optional[Dict[str, Any]] = None,
        max_iterations: int = 3
    ) -> AgentResponse:
        """
        Execute the workflow for a given prompt.
        
        Args:
            prompt: User prompt
            trace_id: Unique identifier for tracing
            context: Optional context information
            max_iterations: Maximum workflow iterations (default: 3)
            
        Returns:
            AgentResponse with result and metadata
        """
        start_time = time.time()
        
        # Start OpenTelemetry span for workflow execution
        with tracer.start_as_current_span("workflow_execution") as span:
            add_span_attributes(
                span,
                trace_id=trace_id,
                prompt_length=len(prompt),
                max_iterations=max_iterations
            )
            
            logger.info(
                "workflow_execution_started",
                trace_id=trace_id,
                prompt_length=len(prompt),
                max_iterations=max_iterations,
                framework=context.get("framework") if context else None
            )
        
        # Initialize workflow state
        initial_state: WorkflowState = {
            "prompt": prompt,
            "routing_strategy": None,
            "documentation_results": None,
            "generated_code": None,
            "framework": context.get("framework") if context else None,
            "iteration_count": 0,
            "max_iterations": max_iterations,
            "trace_id": trace_id,
            "errors": []
        }
        
        try:
            # Execute workflow (use ainvoke for async nodes)
            final_state = await self.graph.ainvoke(initial_state)
            
            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Build result from final state
            result = self._build_result(final_state)
            
            # Track agents invoked
            agents_invoked = ["supervisor"]
            if final_state.get("documentation_results"):
                agents_invoked.append("documentation_search")
            if final_state.get("generated_code"):
                agents_invoked.append("code_gen")
            
            # Calculate total tokens used
            tokens_used = 0
            code_result = final_state.get("code_generation_result")
            if code_result:
                tokens_used += code_result.tokens_used
            
            # Add span attributes for workflow completion
            add_span_attributes(
                span,
                processing_time_ms=processing_time_ms,
                tokens_used=tokens_used,
                workflow_iterations=final_state.get("iteration_count", 0),
                agents_invoked=",".join(agents_invoked)
            )
            
            # Create response metadata
            metadata = ResponseMetadata(
                trace_id=trace_id,
                cache_hit=False,
                processing_time_ms=processing_time_ms,
                tokens_used=tokens_used,
                agents_invoked=agents_invoked,
                workflow_iterations=final_state.get("iteration_count", 0)
            )
            
            logger.info(
                "workflow_execution_complete",
                trace_id=trace_id,
                processing_time_ms=processing_time_ms,
                iterations=final_state.get("iteration_count", 0),
                agents_invoked=agents_invoked,
                tokens_used=tokens_used
            )
            
            return AgentResponse(result=result, metadata=metadata)
            
        except Exception as e:
            logger.error(
                "workflow_execution_error",
                trace_id=trace_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            
            # Return error response
            processing_time_ms = (time.time() - start_time) * 1000
            metadata = ResponseMetadata(
                trace_id=trace_id,
                cache_hit=False,
                processing_time_ms=processing_time_ms,
                tokens_used=0,
                agents_invoked=["supervisor"],
                workflow_iterations=0
            )
            
            return AgentResponse(
                result=f"Error executing workflow: {str(e)}",
                metadata=metadata
            )
    
    def _build_result(self, state: WorkflowState) -> str:
        """
        Build final result string from workflow state.
        
        Args:
            state: Final workflow state
            
        Returns:
            Formatted result string
        """
        routing_strategy = state.get("routing_strategy")
        
        # Handle search-only results
        if routing_strategy == RoutingStrategy.SEARCH_ONLY:
            doc_results = state.get("documentation_results", [])
            if doc_results:
                result = "Documentation Search Results:\n\n"
                for i, doc in enumerate(doc_results[:5], 1):
                    result += f"{i}. [{doc.framework}] (Score: {doc.score:.2f})\n"
                    result += f"   Source: {doc.source}\n"
                    result += f"   {doc.content[:200]}...\n\n"
                return result
            else:
                return "No documentation results found."
        
        # Handle code generation results
        generated_code = state.get("generated_code")
        if generated_code:
            code_result = state.get("code_generation_result")
            result = generated_code
            
            # Add metadata if available
            if code_result:
                result += f"\n\n--- Metadata ---\n"
                result += f"Language: {code_result.language}\n"
                result += f"Framework: {code_result.framework or 'N/A'}\n"
                result += f"Syntax Valid: {code_result.syntax_valid}\n"
                
                if code_result.documentation_sources:
                    result += f"\nDocumentation Sources:\n"
                    for source in code_result.documentation_sources[:3]:
                        result += f"  - {source}\n"
            
            return result
        
        # Handle errors
        errors = state.get("errors", [])
        if errors:
            return f"Workflow completed with errors:\n" + "\n".join(errors)
        
        return "Workflow completed but no result was generated."


# Global workflow instance
agent_workflow = AgentWorkflow()


def get_agent_workflow() -> AgentWorkflow:
    """
    Get the global agent workflow instance.
    
    Returns:
        AgentWorkflow: Global workflow instance
    """
    return agent_workflow
