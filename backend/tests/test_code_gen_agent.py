"""
Unit tests for Code Generation Agent.

Tests the CodeGenAgent class including code generation, syntax validation,
framework-specific prompts, and documentation context incorporation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.code_gen_agent import CodeGenAgent
from app.schemas.agent import CodeGenerationResult, DocumentationResult


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = AsyncMock()
    return client


@pytest.fixture
def code_gen_agent(mock_openai_client):
    """Create a CodeGenAgent instance with mocked client."""
    return CodeGenAgent(client=mock_openai_client, model="gpt-4", max_retries=2)


@pytest.mark.asyncio
async def test_generate_code_success(code_gen_agent, mock_openai_client):
    """Test successful code generation with valid syntax."""
    # Mock LLM response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """```python
def hello_world():
    print("Hello, World!")
```"""
    mock_response.usage.total_tokens = 100
    
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    # Generate code
    result = await code_gen_agent.generate_code(
        prompt="Create a hello world function",
        framework="Python",
        trace_id="test-trace-123"
    )
    
    # Assertions
    assert isinstance(result, CodeGenerationResult)
    assert result.syntax_valid is True
    assert len(result.validation_errors) == 0
    assert "def hello_world" in result.code
    assert result.language == "Python"
    assert result.tokens_used == 100


@pytest.mark.asyncio
async def test_generate_code_with_documentation_context(code_gen_agent, mock_openai_client):
    """Test code generation with documentation context."""
    # Create documentation context
    doc_context = [
        DocumentationResult(
            content="@Controller() decorator is used to define a controller in NestJS",
            score=0.95,
            metadata={"section": "Controllers"},
            source="https://docs.nestjs.com/controllers",
            framework="NestJS"
        )
    ]
    
    # Mock LLM response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """```typescript
@Controller('users')
export class UsersController {
  @Get()
  findAll() {
    return [];
  }
}
```"""
    mock_response.usage.total_tokens = 150
    
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    # Generate code
    result = await code_gen_agent.generate_code(
        prompt="Create a NestJS controller for users",
        documentation_context=doc_context,
        framework="NestJS",
        trace_id="test-trace-456"
    )
    
    # Assertions
    assert isinstance(result, CodeGenerationResult)
    assert result.framework == "NestJS"
    assert len(result.documentation_sources) == 1
    assert result.documentation_sources[0] == "https://docs.nestjs.com/controllers"
    assert "@Controller" in result.code


@pytest.mark.asyncio
async def test_generate_code_empty_prompt(code_gen_agent):
    """Test that empty prompt raises ValueError."""
    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        await code_gen_agent.generate_code(prompt="")


@pytest.mark.asyncio
async def test_generate_code_syntax_error_retry(code_gen_agent, mock_openai_client):
    """Test that syntax errors trigger retry logic."""
    # First attempt returns invalid code
    invalid_response = MagicMock()
    invalid_response.choices = [MagicMock()]
    invalid_response.choices[0].message.content = "def broken_function(\n    pass"  # Missing closing paren
    invalid_response.usage.total_tokens = 50
    
    # Second attempt returns valid code
    valid_response = MagicMock()
    valid_response.choices = [MagicMock()]
    valid_response.choices[0].message.content = """def fixed_function():
    pass"""
    valid_response.usage.total_tokens = 60
    
    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=[invalid_response, valid_response]
    )
    
    # Generate code
    result = await code_gen_agent.generate_code(
        prompt="Create a simple function",
        framework="Python",
        trace_id="test-trace-789"
    )
    
    # Assertions
    assert result.syntax_valid is True
    assert result.tokens_used == 110  # 50 + 60
    assert mock_openai_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_generate_code_max_retries_exceeded(code_gen_agent, mock_openai_client):
    """Test that max retries returns code with errors."""
    # All attempts return invalid code
    invalid_response = MagicMock()
    invalid_response.choices = [MagicMock()]
    invalid_response.choices[0].message.content = "def broken(\n    pass"  # Invalid syntax
    invalid_response.usage.total_tokens = 50
    
    mock_openai_client.chat.completions.create = AsyncMock(
        return_value=invalid_response
    )
    
    # Generate code (should fail after max_retries + 1 attempts)
    result = await code_gen_agent.generate_code(
        prompt="Create a function",
        framework="Python",
        trace_id="test-trace-fail"
    )
    
    # Assertions
    assert result.syntax_valid is False
    assert len(result.validation_errors) > 0
    assert mock_openai_client.chat.completions.create.call_count == 3  # max_retries=2 means 3 total attempts


@pytest.mark.asyncio
async def test_detect_language_from_framework(code_gen_agent):
    """Test language detection from framework."""
    assert code_gen_agent._detect_language("NestJS", "create controller") == "TypeScript"
    assert code_gen_agent._detect_language("React", "create component") == "JavaScript"
    assert code_gen_agent._detect_language("FastAPI", "create endpoint") == "Python"
    assert code_gen_agent._detect_language("Spring Boot", "create controller") == "Java"
    assert code_gen_agent._detect_language(".NET Core", "create controller") == "C#"


@pytest.mark.asyncio
async def test_detect_language_from_prompt(code_gen_agent):
    """Test language detection from prompt when framework is not specified."""
    assert code_gen_agent._detect_language(None, "Create a Python function") == "Python"
    assert code_gen_agent._detect_language(None, "Create a TypeScript interface") == "TypeScript"
    assert code_gen_agent._detect_language(None, "Create a React component") == "JavaScript"
    assert code_gen_agent._detect_language(None, "Create a Java class") == "Java"


def test_extract_code_from_markdown(code_gen_agent):
    """Test extraction of code from markdown code blocks."""
    # Code with markdown
    markdown_code = """```python
def hello():
    print("Hello")
```"""
    extracted = code_gen_agent._extract_code_from_markdown(markdown_code)
    assert "```" not in extracted
    assert "def hello():" in extracted
    
    # Code without markdown
    plain_code = "def hello():\n    print('Hello')"
    extracted = code_gen_agent._extract_code_from_markdown(plain_code)
    assert extracted == plain_code


def test_build_system_prompt_with_framework(code_gen_agent):
    """Test system prompt building with framework."""
    prompt = code_gen_agent._build_system_prompt("NestJS", None)
    assert "NestJS" in prompt
    assert "@Controller" in prompt
    assert "TypeScript" in prompt


def test_build_system_prompt_with_documentation(code_gen_agent):
    """Test system prompt building with documentation context."""
    doc_context = [
        DocumentationResult(
            content="Example content",
            score=0.9,
            metadata={},
            source="https://example.com",
            framework="React"
        )
    ]
    prompt = code_gen_agent._build_system_prompt("React", doc_context)
    assert "documentation" in prompt.lower()


def test_build_user_prompt_with_context(code_gen_agent):
    """Test user prompt building with documentation context."""
    doc_context = [
        DocumentationResult(
            content="Example documentation content",
            score=0.9,
            metadata={},
            source="https://example.com",
            framework="FastAPI"
        )
    ]
    
    user_prompt = code_gen_agent._build_user_prompt(
        "Create an endpoint",
        doc_context
    )
    
    assert "Example documentation content" in user_prompt
    assert "Create an endpoint" in user_prompt
    assert "FastAPI" in user_prompt


def test_get_agent_info(code_gen_agent):
    """Test agent info retrieval."""
    info = code_gen_agent.get_agent_info()
    
    assert info["agent_type"] == "code_generation"
    assert info["model"] == "gpt-4"
    assert info["max_retries"] == 2
    assert "NestJS" in info["supported_frameworks"]
    assert "React" in info["supported_frameworks"]
    assert "FastAPI" in info["supported_frameworks"]


@pytest.mark.asyncio
async def test_generate_code_connection_error(code_gen_agent, mock_openai_client):
    """Test that connection errors are raised after retries."""
    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=ConnectionError("API unavailable")
    )
    
    with pytest.raises(ConnectionError, match="Code generation failed after"):
        await code_gen_agent.generate_code(
            prompt="Create a function",
            framework="Python",
            trace_id="test-trace-error"
        )
    
    # Should retry max_retries + 1 times
    assert mock_openai_client.chat.completions.create.call_count == 3
