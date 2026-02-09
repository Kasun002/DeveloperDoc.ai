"""
Unit tests for AI Agent Pydantic schemas.

Tests model validation, serialization, and edge cases for agent schemas.
"""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.agent import (
    AgentRequest,
    AgentResponse,
    CachedResponse,
    CodeGenerationResult,
    DocumentationResult,
    ResponseMetadata,
    RoutingStrategy,
    WorkflowState,
)


class TestAgentRequest:
    """Test cases for AgentRequest schema."""

    def test_valid_agent_request(self):
        """Test creating a valid agent request."""
        request = AgentRequest(
            prompt="Create a NestJS controller",
            context={"framework": "NestJS"},
            max_iterations=3,
        )
        assert request.prompt == "Create a NestJS controller"
        assert request.context == {"framework": "NestJS"}
        assert request.max_iterations == 3
        assert request.trace_id is not None  # Auto-generated

    def test_agent_request_with_trace_id(self):
        """Test agent request with explicit trace_id."""
        trace_id = str(uuid.uuid4())
        request = AgentRequest(prompt="Test prompt", trace_id=trace_id)
        assert request.trace_id == trace_id

    def test_agent_request_prompt_too_short(self):
        """Test that empty prompt is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AgentRequest(prompt="")
        assert "prompt" in str(exc_info.value)

    def test_agent_request_prompt_too_long(self):
        """Test that prompt exceeding max length is rejected."""
        long_prompt = "a" * 10001
        with pytest.raises(ValidationError) as exc_info:
            AgentRequest(prompt=long_prompt)
        assert "prompt" in str(exc_info.value)

    def test_agent_request_max_iterations_validation(self):
        """Test max_iterations bounds validation."""
        # Test below minimum
        with pytest.raises(ValidationError):
            AgentRequest(prompt="Test", max_iterations=0)

        # Test above maximum
        with pytest.raises(ValidationError):
            AgentRequest(prompt="Test", max_iterations=11)

        # Test valid boundaries
        request_min = AgentRequest(prompt="Test", max_iterations=1)
        assert request_min.max_iterations == 1

        request_max = AgentRequest(prompt="Test", max_iterations=10)
        assert request_max.max_iterations == 10

    def test_agent_request_default_values(self):
        """Test default values for optional fields."""
        request = AgentRequest(prompt="Test prompt")
        assert request.context is None
        assert request.trace_id is not None
        assert request.max_iterations == 3

    def test_agent_request_serialization(self):
        """Test serializing AgentRequest to JSON."""
        request = AgentRequest(
            prompt="Test prompt",
            context={"key": "value"},
            trace_id="test-trace-id",
            max_iterations=5,
        )
        json_data = request.model_dump()
        assert json_data["prompt"] == "Test prompt"
        assert json_data["context"] == {"key": "value"}
        assert json_data["trace_id"] == "test-trace-id"
        assert json_data["max_iterations"] == 5

    def test_agent_request_deserialization(self):
        """Test deserializing AgentRequest from JSON."""
        json_data = {
            "prompt": "Test prompt",
            "context": {"framework": "React"},
            "trace_id": "test-trace-id",
            "max_iterations": 2,
        }
        request = AgentRequest(**json_data)
        assert request.prompt == "Test prompt"
        assert request.context == {"framework": "React"}
        assert request.trace_id == "test-trace-id"
        assert request.max_iterations == 2

    def test_agent_request_missing_required_field(self):
        """Test that missing required field raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AgentRequest()
        assert "prompt" in str(exc_info.value)

    def test_agent_request_invalid_type(self):
        """Test that invalid field types are rejected."""
        with pytest.raises(ValidationError):
            AgentRequest(prompt=123)  # prompt should be string

        with pytest.raises(ValidationError):
            AgentRequest(prompt="Test", max_iterations="invalid")  # should be int


class TestResponseMetadata:
    """Test cases for ResponseMetadata schema."""

    def test_valid_response_metadata(self):
        """Test creating valid response metadata."""
        metadata = ResponseMetadata(
            trace_id="test-trace-id",
            cache_hit=False,
            processing_time_ms=1234.56,
            tokens_used=500,
            agents_invoked=["supervisor", "code_gen"],
            workflow_iterations=1,
        )
        assert metadata.trace_id == "test-trace-id"
        assert metadata.cache_hit is False
        assert metadata.processing_time_ms == 1234.56
        assert metadata.tokens_used == 500
        assert metadata.agents_invoked == ["supervisor", "code_gen"]
        assert metadata.workflow_iterations == 1

    def test_response_metadata_serialization(self):
        """Test serializing ResponseMetadata to JSON."""
        metadata = ResponseMetadata(
            trace_id="test-trace-id",
            cache_hit=True,
            processing_time_ms=500.25,
            tokens_used=250,
            agents_invoked=["supervisor"],
            workflow_iterations=2,
        )
        json_data = metadata.model_dump()
        assert json_data["trace_id"] == "test-trace-id"
        assert json_data["cache_hit"] is True
        assert json_data["processing_time_ms"] == 500.25
        assert json_data["tokens_used"] == 250
        assert json_data["agents_invoked"] == ["supervisor"]
        assert json_data["workflow_iterations"] == 2

    def test_response_metadata_missing_required_fields(self):
        """Test that missing required fields raise validation errors."""
        with pytest.raises(ValidationError) as exc_info:
            ResponseMetadata(trace_id="test")
        # Should fail because other required fields are missing
        error_str = str(exc_info.value)
        assert any(
            field in error_str
            for field in ["cache_hit", "processing_time_ms", "tokens_used"]
        )


class TestAgentResponse:
    """Test cases for AgentResponse schema."""

    def test_valid_agent_response(self):
        """Test creating a valid agent response."""
        metadata = ResponseMetadata(
            trace_id="test-trace-id",
            cache_hit=False,
            processing_time_ms=1234.56,
            tokens_used=500,
            agents_invoked=["supervisor"],
            workflow_iterations=1,
        )
        response = AgentResponse(result="Generated code here", metadata=metadata)
        assert response.result == "Generated code here"
        assert response.metadata.trace_id == "test-trace-id"

    def test_agent_response_serialization(self):
        """Test serializing AgentResponse to JSON."""
        metadata = ResponseMetadata(
            trace_id="test-trace-id",
            cache_hit=False,
            processing_time_ms=1234.56,
            tokens_used=500,
            agents_invoked=["supervisor", "code_gen"],
            workflow_iterations=1,
        )
        response = AgentResponse(result="Generated code", metadata=metadata)
        json_data = response.model_dump()
        assert json_data["result"] == "Generated code"
        assert json_data["metadata"]["trace_id"] == "test-trace-id"
        assert json_data["metadata"]["cache_hit"] is False

    def test_agent_response_deserialization(self):
        """Test deserializing AgentResponse from JSON."""
        json_data = {
            "result": "Generated code",
            "metadata": {
                "trace_id": "test-trace-id",
                "cache_hit": True,
                "processing_time_ms": 500.0,
                "tokens_used": 200,
                "agents_invoked": ["supervisor"],
                "workflow_iterations": 1,
            },
        }
        response = AgentResponse(**json_data)
        assert response.result == "Generated code"
        assert response.metadata.trace_id == "test-trace-id"
        assert response.metadata.cache_hit is True


class TestDocumentationResult:
    """Test cases for DocumentationResult schema."""

    def test_valid_documentation_result(self):
        """Test creating a valid documentation result."""
        result = DocumentationResult(
            content="NestJS controller documentation",
            score=0.92,
            metadata={"section": "Controllers"},
            source="https://docs.nestjs.com/controllers",
            framework="NestJS",
        )
        assert result.content == "NestJS controller documentation"
        assert result.score == 0.92
        assert result.framework == "NestJS"

    def test_documentation_result_score_validation(self):
        """Test score bounds validation."""
        # Test below minimum
        with pytest.raises(ValidationError):
            DocumentationResult(
                content="Test",
                score=-0.1,
                source="test",
                framework="NestJS",
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            DocumentationResult(
                content="Test",
                score=1.1,
                source="test",
                framework="NestJS",
            )

        # Test valid boundaries
        result_min = DocumentationResult(
            content="Test", score=0.0, source="test", framework="NestJS"
        )
        assert result_min.score == 0.0

        result_max = DocumentationResult(
            content="Test", score=1.0, source="test", framework="NestJS"
        )
        assert result_max.score == 1.0

    def test_documentation_result_default_metadata(self):
        """Test default empty metadata dict."""
        result = DocumentationResult(
            content="Test content",
            score=0.8,
            source="test-source",
            framework="React",
        )
        assert result.metadata == {}

    def test_documentation_result_serialization(self):
        """Test serializing DocumentationResult to JSON."""
        result = DocumentationResult(
            content="Test documentation",
            score=0.85,
            metadata={"version": "10.x"},
            source="https://example.com",
            framework="FastAPI",
        )
        json_data = result.model_dump()
        assert json_data["content"] == "Test documentation"
        assert json_data["score"] == 0.85
        assert json_data["metadata"] == {"version": "10.x"}
        assert json_data["source"] == "https://example.com"
        assert json_data["framework"] == "FastAPI"

    def test_documentation_result_deserialization(self):
        """Test deserializing DocumentationResult from JSON."""
        json_data = {
            "content": "Documentation content",
            "score": 0.95,
            "metadata": {"section": "Getting Started"},
            "source": "https://docs.example.com",
            "framework": "Django",
        }
        result = DocumentationResult(**json_data)
        assert result.content == "Documentation content"
        assert result.score == 0.95
        assert result.framework == "Django"


class TestCodeGenerationResult:
    """Test cases for CodeGenerationResult schema."""

    def test_valid_code_generation_result(self):
        """Test creating a valid code generation result."""
        result = CodeGenerationResult(
            code="@Controller()\nclass TestController {}",
            language="TypeScript",
            framework="NestJS",
            syntax_valid=True,
            validation_errors=[],
            tokens_used=350,
            documentation_sources=["https://docs.nestjs.com"],
        )
        assert result.code == "@Controller()\nclass TestController {}"
        assert result.language == "TypeScript"
        assert result.framework == "NestJS"
        assert result.syntax_valid is True
        assert result.validation_errors == []
        assert result.tokens_used == 350

    def test_code_generation_result_with_errors(self):
        """Test code generation result with validation errors."""
        result = CodeGenerationResult(
            code="invalid code",
            language="Python",
            syntax_valid=False,
            validation_errors=["SyntaxError: invalid syntax"],
            tokens_used=100,
        )
        assert result.syntax_valid is False
        assert len(result.validation_errors) == 1
        assert result.framework is None

    def test_code_generation_result_default_values(self):
        """Test default values for optional fields."""
        result = CodeGenerationResult(
            code="print('hello')",
            language="Python",
            syntax_valid=True,
            tokens_used=50,
        )
        assert result.framework is None
        assert result.validation_errors == []
        assert result.documentation_sources == []

    def test_code_generation_result_serialization(self):
        """Test serializing CodeGenerationResult to JSON."""
        result = CodeGenerationResult(
            code="def hello(): pass",
            language="Python",
            framework="FastAPI",
            syntax_valid=True,
            validation_errors=[],
            tokens_used=100,
            documentation_sources=["https://fastapi.tiangolo.com"],
        )
        json_data = result.model_dump()
        assert json_data["code"] == "def hello(): pass"
        assert json_data["language"] == "Python"
        assert json_data["framework"] == "FastAPI"
        assert json_data["syntax_valid"] is True
        assert json_data["tokens_used"] == 100

    def test_code_generation_result_deserialization(self):
        """Test deserializing CodeGenerationResult from JSON."""
        json_data = {
            "code": "const x = 1;",
            "language": "JavaScript",
            "framework": "React",
            "syntax_valid": True,
            "validation_errors": [],
            "tokens_used": 75,
            "documentation_sources": ["https://react.dev"],
        }
        result = CodeGenerationResult(**json_data)
        assert result.code == "const x = 1;"
        assert result.language == "JavaScript"
        assert result.framework == "React"
        assert result.syntax_valid is True


class TestCachedResponse:
    """Test cases for CachedResponse schema."""

    def test_valid_cached_response(self):
        """Test creating a valid cached response."""
        now = datetime.now(timezone.utc)
        response = CachedResponse(
            response="Cached result",
            embedding=[0.1, 0.2, 0.3],
            similarity_score=0.97,
            cached_at=now,
            ttl=3600,
        )
        assert response.response == "Cached result"
        assert response.embedding == [0.1, 0.2, 0.3]
        assert response.similarity_score == 0.97
        assert response.cached_at == now
        assert response.ttl == 3600

    def test_cached_response_serialization(self):
        """Test serializing CachedResponse to JSON."""
        now = datetime.now(timezone.utc)
        response = CachedResponse(
            response="Test response",
            embedding=[0.5, 0.6],
            similarity_score=0.95,
            cached_at=now,
            ttl=1800,
        )
        json_data = response.model_dump()
        assert json_data["response"] == "Test response"
        assert json_data["embedding"] == [0.5, 0.6]
        assert json_data["similarity_score"] == 0.95
        assert json_data["ttl"] == 1800

    def test_cached_response_deserialization(self):
        """Test deserializing CachedResponse from JSON."""
        now = datetime.now(timezone.utc)
        json_data = {
            "response": "Cached data",
            "embedding": [0.1, 0.2, 0.3, 0.4],
            "similarity_score": 0.98,
            "cached_at": now.isoformat(),
            "ttl": 7200,
        }
        response = CachedResponse(**json_data)
        assert response.response == "Cached data"
        assert response.embedding == [0.1, 0.2, 0.3, 0.4]
        assert response.similarity_score == 0.98
        assert response.ttl == 7200

    def test_cached_response_with_large_embedding(self):
        """Test cached response with realistic embedding size (1536 dimensions)."""
        now = datetime.now(timezone.utc)
        embedding = [0.1] * 1536  # text-embedding-3-small dimension
        response = CachedResponse(
            response="Test",
            embedding=embedding,
            similarity_score=0.96,
            cached_at=now,
            ttl=3600,
        )
        assert len(response.embedding) == 1536


class TestRoutingStrategy:
    """Test cases for RoutingStrategy enum."""

    def test_routing_strategy_values(self):
        """Test all routing strategy enum values."""
        assert RoutingStrategy.SEARCH_ONLY == "search_only"
        assert RoutingStrategy.CODE_ONLY == "code_only"
        assert RoutingStrategy.SEARCH_THEN_CODE == "search_then_code"
        assert RoutingStrategy.PARALLEL == "parallel"

    def test_routing_strategy_membership(self):
        """Test routing strategy enum membership."""
        assert "search_only" in [s.value for s in RoutingStrategy]
        assert "code_only" in [s.value for s in RoutingStrategy]
        assert "search_then_code" in [s.value for s in RoutingStrategy]
        assert "parallel" in [s.value for s in RoutingStrategy]


class TestWorkflowState:
    """Test cases for WorkflowState TypedDict."""

    def test_workflow_state_creation(self):
        """Test creating a workflow state dict."""
        state: WorkflowState = {
            "prompt": "Test prompt",
            "routing_strategy": RoutingStrategy.SEARCH_THEN_CODE,
            "documentation_results": None,
            "generated_code": None,
            "framework": "NestJS",
            "iteration_count": 0,
            "max_iterations": 3,
            "trace_id": "test-trace-id",
            "errors": [],
        }
        assert state["prompt"] == "Test prompt"
        assert state["routing_strategy"] == RoutingStrategy.SEARCH_THEN_CODE
        assert state["framework"] == "NestJS"
        assert state["iteration_count"] == 0
        assert state["max_iterations"] == 3

    def test_workflow_state_partial(self):
        """Test creating a partial workflow state (total=False)."""
        # WorkflowState has total=False, so partial dicts are valid
        state: WorkflowState = {
            "prompt": "Test",
            "trace_id": "test-id",
        }
        assert state["prompt"] == "Test"
        assert state["trace_id"] == "test-id"
