"""
Integration tests for Code Generation Agent with Syntax Validator.

Tests the complete flow of code generation including syntax validation
and retry logic with real validator integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.code_gen_agent import CodeGenAgent
from app.schemas.agent import DocumentationResult


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_end_to_end_python_code_generation(mock_openai_client):
    """Test complete flow of Python code generation with syntax validation."""
    # Create agent
    agent = CodeGenAgent(client=mock_openai_client, model="gpt-4", max_retries=2)
    
    # Mock LLM response with valid Python code
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """```python
def calculate_fibonacci(n: int) -> int:
    '''Calculate the nth Fibonacci number.'''
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)
```"""
    mock_response.usage.total_tokens = 120
    
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    # Generate code
    result = await agent.generate_code(
        prompt="Create a recursive Fibonacci function in Python",
        framework="Python",
        trace_id="integration-test-1"
    )
    
    # Verify result
    assert result.syntax_valid is True
    assert len(result.validation_errors) == 0
    assert "def calculate_fibonacci" in result.code
    assert result.language == "Python"
    assert result.tokens_used == 120


@pytest.mark.asyncio
async def test_end_to_end_typescript_code_generation(mock_openai_client):
    """Test complete flow of TypeScript code generation with syntax validation."""
    # Create agent
    agent = CodeGenAgent(client=mock_openai_client, model="gpt-4", max_retries=2)
    
    # Mock LLM response with valid TypeScript code
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """```typescript
interface User {
    id: number;
    name: string;
    email: string;
}

class UserService {
    private users: User[] = [];
    
    addUser(user: User): void {
        this.users.push(user);
    }
    
    getUserById(id: number): User | undefined {
        return this.users.find(u => u.id === id);
    }
}
```"""
    mock_response.usage.total_tokens = 180
    
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    # Generate code
    result = await agent.generate_code(
        prompt="Create a TypeScript UserService class",
        framework="TypeScript",
        trace_id="integration-test-2"
    )
    
    # Verify result
    assert result.syntax_valid is True
    assert len(result.validation_errors) == 0
    assert "class UserService" in result.code
    assert "interface User" in result.code
    assert result.language == "TypeScript"


@pytest.mark.asyncio
async def test_end_to_end_with_documentation_context(mock_openai_client):
    """Test code generation with documentation context integration."""
    # Create agent
    agent = CodeGenAgent(client=mock_openai_client, model="gpt-4", max_retries=2)
    
    # Create documentation context
    doc_context = [
        DocumentationResult(
            content="@Controller() decorator defines a basic controller. Example: @Controller('cats')",
            score=0.95,
            metadata={"section": "Controllers"},
            source="https://docs.nestjs.com/controllers",
            framework="NestJS"
        ),
        DocumentationResult(
            content="@Get() decorator creates a GET endpoint. Example: @Get(':id')",
            score=0.92,
            metadata={"section": "Controllers"},
            source="https://docs.nestjs.com/controllers",
            framework="NestJS"
        )
    ]
    
    # Mock LLM response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """```typescript
import { Controller, Get, Param } from '@nestjs/common';

@Controller('users')
export class UsersController {
    @Get()
    findAll() {
        return [];
    }
    
    @Get(':id')
    findOne(@Param('id') id: string) {
        return { id };
    }
}
```"""
    mock_response.usage.total_tokens = 200
    
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    # Generate code
    result = await agent.generate_code(
        prompt="Create a NestJS controller for users",
        documentation_context=doc_context,
        framework="NestJS",
        trace_id="integration-test-3"
    )
    
    # Verify result
    assert result.syntax_valid is True
    assert result.framework == "NestJS"
    assert len(result.documentation_sources) == 2
    assert "@Controller" in result.code
    assert "@Get" in result.code


@pytest.mark.asyncio
async def test_syntax_validation_retry_flow(mock_openai_client):
    """Test that syntax validation triggers retry and eventually succeeds."""
    # Create agent
    agent = CodeGenAgent(client=mock_openai_client, model="gpt-4", max_retries=2)
    
    # First attempt: invalid Python code (missing closing parenthesis)
    invalid_response = MagicMock()
    invalid_response.choices = [MagicMock()]
    invalid_response.choices[0].message.content = """def broken_function(x:
    return x * 2"""
    invalid_response.usage.total_tokens = 50
    
    # Second attempt: valid Python code
    valid_response = MagicMock()
    valid_response.choices = [MagicMock()]
    valid_response.choices[0].message.content = """def fixed_function(x: int) -> int:
    return x * 2"""
    valid_response.usage.total_tokens = 60
    
    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=[invalid_response, valid_response]
    )
    
    # Generate code
    result = await agent.generate_code(
        prompt="Create a function that doubles a number",
        framework="Python",
        trace_id="integration-test-retry"
    )
    
    # Verify retry happened and succeeded
    assert result.syntax_valid is True
    assert result.tokens_used == 110  # 50 + 60
    assert "def fixed_function" in result.code
    assert mock_openai_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_multiple_language_support(mock_openai_client):
    """Test that agent supports multiple programming languages."""
    agent = CodeGenAgent(client=mock_openai_client, model="gpt-4", max_retries=2)
    
    # Test Python
    assert agent._detect_language("Python", "test") == "Python"
    assert agent._detect_language("FastAPI", "test") == "Python"
    assert agent._detect_language("Django", "test") == "Python"
    
    # Test JavaScript
    assert agent._detect_language("React", "test") == "JavaScript"
    assert agent._detect_language("Vue.js", "test") == "JavaScript"
    assert agent._detect_language("Express.js", "test") == "JavaScript"
    
    # Test TypeScript
    assert agent._detect_language("NestJS", "test") == "TypeScript"
    assert agent._detect_language("Angular", "test") == "TypeScript"
    
    # Test Java
    assert agent._detect_language("Spring Boot", "test") == "Java"
    
    # Test C#
    assert agent._detect_language(".NET Core", "test") == "C#"
