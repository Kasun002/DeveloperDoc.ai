"""
Unit tests for LangGraph workflow orchestration.

Tests workflow state management, node execution, conditional routing,
and cycle support.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.agent import (
    CodeGenerationResult,
    DocumentationResult,
    RoutingStrategy,
    WorkflowState,
)
from app.workflows.agent_workflow import AgentWorkflow


@pytest.fixture
def mock_supervisor():
    """Mock supervisor agent."""
    supervisor = MagicMock()
    supervisor.determine_routing_strategy = AsyncMock(
        return_value=RoutingStrategy.SEARCH_THEN_CODE
    )
    return supervisor


@pytest.fixture
def mock_search_agent():
    """Mock documentation search agent."""
    search_agent = MagicMock()
    search_agent.search_docs = AsyncMock(
        return_value=[
            DocumentationResult(
                content="Test documentation content",
                score=0.92,
                metadata={"section": "Controllers"},
                source="https://docs.test.com",
                framework="NestJS"
            )
        ]
    )
    return search_agent


@pytest.fixture
def mock_code_gen_agent():
    """Mock code generation agent."""
    code_gen_agent = MagicMock()
    code_gen_agent.generate_code = AsyncMock(
        return_value=CodeGenerationResult(
            code="@Controller('test')\nexport class TestController {}",
            language="TypeScript",
            framework="NestJS",
            syntax_valid=True,
            validation_errors=[],
            tokens_used=100,
            documentation_sources=["https://docs.test.com"]
        )
    )
    return code_gen_agent


@pytest.fixture
def workflow(mock_supervisor, mock_search_agent, mock_code_gen_agent):
    """Create workflow with mocked agents."""
    return AgentWorkflow(
        supervisor=mock_supervisor,
        search_agent=mock_search_agent,
        code_gen_agent=mock_code_gen_agent
    )


class TestWorkflowNodes:
    """Test individual workflow nodes."""
    
    def test_supervisor_node_success(self, workflow):
        """Test supervisor node successfully determines routing strategy."""
        state: WorkflowState = {
            "prompt": "Create a NestJS controller",
            "routing_strategy": None,
            "documentation_results": None,
            "generated_code": None,
            "framework": None,
            "iteration_count": 0,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        result_state = workflow.supervisor_node(state)
        
        assert result_state["routing_strategy"] == RoutingStrategy.SEARCH_THEN_CODE
        assert len(result_state["errors"]) == 0
    
    def test_supervisor_node_missing_prompt(self, workflow):
        """Test supervisor node handles missing prompt."""
        state: WorkflowState = {
            "prompt": "",
            "routing_strategy": None,
            "documentation_results": None,
            "generated_code": None,
            "framework": None,
            "iteration_count": 0,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        result_state = workflow.supervisor_node(state)
        
        assert len(result_state["errors"]) > 0
        assert "Missing required field: prompt" in result_state["errors"][0]
    
    def test_search_node_success(self, workflow):
        """Test search node successfully retrieves documentation."""
        state: WorkflowState = {
            "prompt": "NestJS controller",
            "routing_strategy": RoutingStrategy.SEARCH_THEN_CODE,
            "documentation_results": None,
            "generated_code": None,
            "framework": "NestJS",
            "iteration_count": 0,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        result_state = workflow.search_node(state)
        
        assert result_state["documentation_results"] is not None
        assert len(result_state["documentation_results"]) > 0
        assert result_state["documentation_results"][0].framework == "NestJS"
    
    def test_search_node_missing_prompt(self, workflow):
        """Test search node handles missing prompt."""
        state: WorkflowState = {
            "prompt": "",
            "routing_strategy": RoutingStrategy.SEARCH_ONLY,
            "documentation_results": None,
            "generated_code": None,
            "framework": None,
            "iteration_count": 0,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        result_state = workflow.search_node(state)
        
        assert result_state["documentation_results"] == []
        assert len(result_state["errors"]) > 0
    
    def test_code_gen_node_success(self, workflow):
        """Test code generation node successfully generates code."""
        state: WorkflowState = {
            "prompt": "Create a NestJS controller",
            "routing_strategy": RoutingStrategy.SEARCH_THEN_CODE,
            "documentation_results": [
                DocumentationResult(
                    content="Test doc",
                    score=0.9,
                    metadata={},
                    source="test.com",
                    framework="NestJS"
                )
            ],
            "generated_code": None,
            "framework": "NestJS",
            "iteration_count": 0,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        result_state = workflow.code_gen_node(state)
        
        assert result_state["generated_code"] is not None
        assert "@Controller" in result_state["generated_code"]
        assert result_state["code_generation_result"].syntax_valid is True
    
    def test_code_gen_node_missing_prompt(self, workflow):
        """Test code generation node handles missing prompt."""
        state: WorkflowState = {
            "prompt": "",
            "routing_strategy": RoutingStrategy.CODE_ONLY,
            "documentation_results": None,
            "generated_code": None,
            "framework": None,
            "iteration_count": 0,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        result_state = workflow.code_gen_node(state)
        
        assert result_state["generated_code"] is None
        assert len(result_state["errors"]) > 0
    
    def test_validate_node_increments_iteration(self, workflow):
        """Test validation node increments iteration count."""
        state: WorkflowState = {
            "prompt": "test",
            "routing_strategy": RoutingStrategy.SEARCH_THEN_CODE,
            "documentation_results": None,
            "generated_code": "test code",
            "framework": None,
            "iteration_count": 0,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        result_state = workflow.validate_node(state)
        
        assert result_state["iteration_count"] == 1
    
    def test_validate_node_sets_default_max_iterations(self, workflow):
        """Test validation node sets default max_iterations if missing."""
        state: WorkflowState = {
            "prompt": "test",
            "routing_strategy": RoutingStrategy.CODE_ONLY,
            "documentation_results": None,
            "generated_code": "test code",
            "framework": None,
            "iteration_count": 0,
            "trace_id": "test-trace-id",
            "errors": []
        }
        # Remove max_iterations
        if "max_iterations" in state:
            del state["max_iterations"]
        
        result_state = workflow.validate_node(state)
        
        assert result_state["max_iterations"] == 3


class TestConditionalRouting:
    """Test conditional routing logic."""
    
    def test_route_after_supervisor_search_only(self, workflow):
        """Test routing to search for SEARCH_ONLY strategy."""
        state: WorkflowState = {
            "prompt": "test",
            "routing_strategy": RoutingStrategy.SEARCH_ONLY,
            "documentation_results": None,
            "generated_code": None,
            "framework": None,
            "iteration_count": 0,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        next_node = workflow.route_after_supervisor(state)
        
        assert next_node == "search"
    
    def test_route_after_supervisor_code_only(self, workflow):
        """Test routing to code for CODE_ONLY strategy."""
        state: WorkflowState = {
            "prompt": "test",
            "routing_strategy": RoutingStrategy.CODE_ONLY,
            "documentation_results": None,
            "generated_code": None,
            "framework": None,
            "iteration_count": 0,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        next_node = workflow.route_after_supervisor(state)
        
        assert next_node == "code"
    
    def test_route_after_supervisor_search_then_code(self, workflow):
        """Test routing to search for SEARCH_THEN_CODE strategy."""
        state: WorkflowState = {
            "prompt": "test",
            "routing_strategy": RoutingStrategy.SEARCH_THEN_CODE,
            "documentation_results": None,
            "generated_code": None,
            "framework": None,
            "iteration_count": 0,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        next_node = workflow.route_after_supervisor(state)
        
        assert next_node == "search"
    
    def test_route_after_supervisor_no_strategy(self, workflow):
        """Test routing ends when no strategy is set."""
        state: WorkflowState = {
            "prompt": "test",
            "routing_strategy": None,
            "documentation_results": None,
            "generated_code": None,
            "framework": None,
            "iteration_count": 0,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        next_node = workflow.route_after_supervisor(state)
        
        assert next_node == "end"


class TestCycleSupport:
    """Test workflow cycle support."""
    
    def test_should_retry_max_iterations_reached(self, workflow):
        """Test workflow ends when max iterations reached."""
        state: WorkflowState = {
            "prompt": "test",
            "routing_strategy": RoutingStrategy.SEARCH_THEN_CODE,
            "documentation_results": None,
            "generated_code": "test code",
            "framework": None,
            "iteration_count": 3,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        decision = workflow.should_retry(state)
        
        assert decision == "done"
    
    def test_should_retry_syntax_errors_under_max(self, workflow):
        """Test workflow retries when syntax errors and under max iterations."""
        state: WorkflowState = {
            "prompt": "test",
            "routing_strategy": RoutingStrategy.SEARCH_THEN_CODE,
            "documentation_results": None,
            "generated_code": "test code",
            "code_generation_result": CodeGenerationResult(
                code="invalid code",
                language="Python",
                framework=None,
                syntax_valid=False,
                validation_errors=["Syntax error on line 1"],
                tokens_used=50,
                documentation_sources=[]
            ),
            "framework": None,
            "iteration_count": 1,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        decision = workflow.should_retry(state)
        
        assert decision == "retry"
    
    def test_should_retry_syntax_valid(self, workflow):
        """Test workflow ends when code is syntactically valid."""
        state: WorkflowState = {
            "prompt": "test",
            "routing_strategy": RoutingStrategy.SEARCH_THEN_CODE,
            "documentation_results": None,
            "generated_code": "test code",
            "code_generation_result": CodeGenerationResult(
                code="valid code",
                language="Python",
                framework=None,
                syntax_valid=True,
                validation_errors=[],
                tokens_used=50,
                documentation_sources=[]
            ),
            "framework": None,
            "iteration_count": 1,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        decision = workflow.should_retry(state)
        
        assert decision == "done"
    
    def test_should_retry_search_only(self, workflow):
        """Test workflow ends for SEARCH_ONLY strategy."""
        state: WorkflowState = {
            "prompt": "test",
            "routing_strategy": RoutingStrategy.SEARCH_ONLY,
            "documentation_results": [
                DocumentationResult(
                    content="test",
                    score=0.9,
                    metadata={},
                    source="test.com",
                    framework="NestJS"
                )
            ],
            "generated_code": None,
            "framework": None,
            "iteration_count": 1,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        decision = workflow.should_retry(state)
        
        assert decision == "done"


class TestStateManagement:
    """Test state persistence and validation."""
    
    def test_state_persists_across_nodes(self, workflow):
        """Test state data persists across node transitions."""
        initial_state: WorkflowState = {
            "prompt": "Create a NestJS controller",
            "routing_strategy": None,
            "documentation_results": None,
            "generated_code": None,
            "framework": "NestJS",
            "iteration_count": 0,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        # Execute supervisor node
        state_after_supervisor = workflow.supervisor_node(initial_state)
        
        # Verify state persisted
        assert state_after_supervisor["prompt"] == initial_state["prompt"]
        assert state_after_supervisor["framework"] == initial_state["framework"]
        assert state_after_supervisor["trace_id"] == initial_state["trace_id"]
        assert state_after_supervisor["routing_strategy"] is not None
        
        # Execute search node
        state_after_search = workflow.search_node(state_after_supervisor)
        
        # Verify state persisted
        assert state_after_search["prompt"] == initial_state["prompt"]
        assert state_after_search["framework"] == initial_state["framework"]
        assert state_after_search["routing_strategy"] == state_after_supervisor["routing_strategy"]
        assert state_after_search["documentation_results"] is not None
    
    def test_errors_accumulate_in_state(self, workflow):
        """Test errors accumulate in state across nodes."""
        state: WorkflowState = {
            "prompt": "",  # Invalid prompt
            "routing_strategy": None,
            "documentation_results": None,
            "generated_code": None,
            "framework": None,
            "iteration_count": 0,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": []
        }
        
        # Execute nodes with invalid state
        state = workflow.supervisor_node(state)
        assert len(state["errors"]) > 0
        
        error_count = len(state["errors"])
        state = workflow.search_node(state)
        assert len(state["errors"]) > error_count  # More errors accumulated


@pytest.mark.asyncio
async def test_workflow_execute_end_to_end(workflow):
    """Test complete workflow execution."""
    response = await workflow.execute(
        prompt="Create a NestJS controller for user authentication",
        trace_id="test-trace-id",
        context={"framework": "NestJS"},
        max_iterations=3
    )
    
    assert response.result is not None
    assert response.metadata.trace_id == "test-trace-id"
    assert response.metadata.cache_hit is False
    assert "supervisor" in response.metadata.agents_invoked
    assert response.metadata.workflow_iterations >= 0


@pytest.mark.asyncio
async def test_workflow_execute_with_error(workflow):
    """Test workflow execution handles errors gracefully."""
    # Make supervisor raise an error
    workflow.supervisor.determine_routing_strategy = AsyncMock(
        side_effect=Exception("Test error")
    )
    
    response = await workflow.execute(
        prompt="Test prompt",
        trace_id="test-trace-id",
        max_iterations=3
    )
    
    assert "Error" in response.result or "error" in response.result.lower()
    assert response.metadata.trace_id == "test-trace-id"
