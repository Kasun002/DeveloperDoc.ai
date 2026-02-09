"""
Integration tests for LangGraph workflow with real agent interactions.

These tests verify the complete workflow with actual agent implementations
(though they may use mocked external services like OpenAI).
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.agent import RoutingStrategy
from app.workflows.agent_workflow import AgentWorkflow


@pytest.mark.asyncio
@patch("app.agents.supervisor_agent.AsyncOpenAI")
@patch("app.agents.code_gen_agent.AsyncOpenAI")
async def test_search_only_workflow(mock_code_gen_openai, mock_supervisor_openai):
    """Test workflow with SEARCH_ONLY routing strategy."""
    # Mock supervisor to return SEARCH_ONLY
    mock_supervisor_response = AsyncMock()
    mock_supervisor_response.choices = [
        AsyncMock(message=AsyncMock(content="SEARCH_ONLY"))
    ]
    mock_supervisor_response.usage = AsyncMock(total_tokens=50)
    mock_supervisor_openai.return_value.chat.completions.create = AsyncMock(
        return_value=mock_supervisor_response
    )
    
    workflow = AgentWorkflow()
    
    response = await workflow.execute(
        prompt="What is a NestJS controller?",
        trace_id="test-search-only",
        max_iterations=3
    )
    
    assert response.result is not None
    assert response.metadata.trace_id == "test-search-only"
    assert "supervisor" in response.metadata.agents_invoked
    # For search-only, we might have documentation_search but not code_gen
    assert response.metadata.workflow_iterations >= 0


@pytest.mark.asyncio
@patch("app.agents.supervisor_agent.AsyncOpenAI")
@patch("app.agents.code_gen_agent.AsyncOpenAI")
async def test_code_only_workflow(mock_code_gen_openai, mock_supervisor_openai):
    """Test workflow with CODE_ONLY routing strategy."""
    # Mock supervisor to return CODE_ONLY
    mock_supervisor_response = AsyncMock()
    mock_supervisor_response.choices = [
        AsyncMock(message=AsyncMock(content="CODE_ONLY"))
    ]
    mock_supervisor_response.usage = AsyncMock(total_tokens=50)
    mock_supervisor_openai.return_value.chat.completions.create = AsyncMock(
        return_value=mock_supervisor_response
    )
    
    # Mock code generation
    mock_code_response = AsyncMock()
    mock_code_response.choices = [
        AsyncMock(message=AsyncMock(content="```python\ndef hello():\n    print('Hello')\n```"))
    ]
    mock_code_response.usage = AsyncMock(total_tokens=100)
    mock_code_gen_openai.return_value.chat.completions.create = AsyncMock(
        return_value=mock_code_response
    )
    
    workflow = AgentWorkflow()
    
    response = await workflow.execute(
        prompt="Write a simple hello world function",
        trace_id="test-code-only",
        max_iterations=3
    )
    
    assert response.result is not None
    assert response.metadata.trace_id == "test-code-only"
    assert "supervisor" in response.metadata.agents_invoked
    assert response.metadata.workflow_iterations >= 0


@pytest.mark.asyncio
@patch("app.agents.supervisor_agent.AsyncOpenAI")
@patch("app.agents.code_gen_agent.AsyncOpenAI")
async def test_search_then_code_workflow(mock_code_gen_openai, mock_supervisor_openai):
    """Test workflow with SEARCH_THEN_CODE routing strategy."""
    # Mock supervisor to return SEARCH_THEN_CODE
    mock_supervisor_response = AsyncMock()
    mock_supervisor_response.choices = [
        AsyncMock(message=AsyncMock(content="SEARCH_THEN_CODE"))
    ]
    mock_supervisor_response.usage = AsyncMock(total_tokens=50)
    mock_supervisor_openai.return_value.chat.completions.create = AsyncMock(
        return_value=mock_supervisor_response
    )
    
    # Mock code generation
    mock_code_response = AsyncMock()
    mock_code_response.choices = [
        AsyncMock(message=AsyncMock(content="```typescript\n@Controller('users')\nexport class UsersController {}\n```"))
    ]
    mock_code_response.usage = AsyncMock(total_tokens=150)
    mock_code_gen_openai.return_value.chat.completions.create = AsyncMock(
        return_value=mock_code_response
    )
    
    workflow = AgentWorkflow()
    
    response = await workflow.execute(
        prompt="Create a NestJS controller for user management",
        trace_id="test-search-then-code",
        context={"framework": "NestJS"},
        max_iterations=3
    )
    
    assert response.result is not None
    assert response.metadata.trace_id == "test-search-then-code"
    assert "supervisor" in response.metadata.agents_invoked
    assert response.metadata.workflow_iterations >= 0


@pytest.mark.asyncio
async def test_workflow_max_iterations_limit():
    """Test workflow respects max_iterations limit."""
    workflow = AgentWorkflow()
    
    # Set max_iterations to 1
    response = await workflow.execute(
        prompt="Test prompt",
        trace_id="test-max-iterations",
        max_iterations=1
    )
    
    assert response.result is not None
    assert response.metadata.workflow_iterations <= 1


@pytest.mark.asyncio
async def test_workflow_state_persistence():
    """Test that workflow state persists across node transitions."""
    workflow = AgentWorkflow()
    
    response = await workflow.execute(
        prompt="Create a FastAPI endpoint",
        trace_id="test-state-persistence",
        context={"framework": "FastAPI"},
        max_iterations=3
    )
    
    # Verify trace_id persisted throughout
    assert response.metadata.trace_id == "test-state-persistence"
    
    # Verify agents were invoked (state was maintained)
    assert len(response.metadata.agents_invoked) > 0
    assert "supervisor" in response.metadata.agents_invoked
