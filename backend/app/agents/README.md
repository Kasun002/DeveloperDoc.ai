# AI Agents

This directory contains the specialized agents for the AI Agent System.

## Agents

### 1. Documentation Search Agent
**File**: `documentation_search_agent.py`

Performs semantic search across framework documentation using pgvector with HNSW indexing, applies cross-encoder re-ranking, and implements self-correction for low-confidence results.

**Key Features**:
- Semantic search with pgvector
- Cross-encoder re-ranking
- Self-correction for low confidence
- Tool-level caching
- Support for 9+ frameworks

**Usage**:
```python
from app.agents.documentation_search_agent import documentation_search_agent

results = await documentation_search_agent.search_docs(
    query="How to create a controller in NestJS",
    frameworks=["NestJS"],
    top_k=10
)
```

### 2. Code Generation Agent
**File**: `code_gen_agent.py`

Generates syntactically correct, framework-compliant code using LLM with optional documentation context.

**Key Features**:
- Multi-framework support (9 frameworks)
- Framework-specific prompts
- Documentation context integration
- Syntax validation with retry logic
- Multi-language support (5 languages)

**Usage**:
```python
from app.agents.code_gen_agent import code_gen_agent

result = await code_gen_agent.generate_code(
    prompt="Create a NestJS controller for users",
    documentation_context=doc_results,
    framework="NestJS",
    trace_id="request-123"
)
```

### 3. Syntax Validator
**File**: `syntax_validator.py`

Multi-language syntax validator for validating generated code.

**Supported Languages**:
- Python (using `ast` module)
- JavaScript (balanced delimiters + patterns)
- TypeScript (JavaScript + TS-specific checks)
- Java (balanced delimiters + class/method validation)
- C# (balanced delimiters + class/method validation)

**Usage**:
```python
from app.agents.syntax_validator import SyntaxValidator

validator = SyntaxValidator()
result = validator.validate_syntax(code, "Python")

if result["valid"]:
    print("Code is valid!")
else:
    print(f"Errors: {result['errors']}")
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AI Agent System                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Documentation Search Agent                   │   │
│  │  - Semantic search with pgvector                    │   │
│  │  - Cross-encoder re-ranking                         │   │
│  │  - Self-correction                                  │   │
│  │  - Tool-level caching                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          │ Documentation Context             │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Code Generation Agent                        │   │
│  │  - Framework-specific prompts                       │   │
│  │  - Documentation context integration                │   │
│  │  - Syntax validation                                │   │
│  │  - Retry logic                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          │ Generated Code                    │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Syntax Validator                             │   │
│  │  - Multi-language validation                        │   │
│  │  - Balanced delimiter checking                      │   │
│  │  - Error reporting                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Supported Frameworks

1. **NestJS** (TypeScript) - Backend framework
2. **React** (JavaScript/TypeScript) - Frontend library
3. **FastAPI** (Python) - Backend framework
4. **Spring Boot** (Java) - Backend framework
5. **.NET Core** (C#) - Backend framework
6. **Vue.js** (JavaScript/TypeScript) - Frontend framework
7. **Angular** (TypeScript) - Frontend framework
8. **Django** (Python) - Backend framework
9. **Express.js** (JavaScript/TypeScript) - Backend framework

## Testing

### Run All Agent Tests
```bash
pytest tests/test_*agent*.py tests/test_syntax_validator.py -v
```

### Run Specific Agent Tests
```bash
# Documentation Search Agent
pytest tests/test_documentation_search_agent.py -v

# Code Generation Agent
pytest tests/test_code_gen_agent.py -v

# Syntax Validator
pytest tests/test_syntax_validator.py -v

# Integration Tests
pytest tests/test_code_gen_integration.py -v
```

## Documentation

- [Code Generation Agent Documentation](../../docs/code_gen_agent.md)
- [Task 9 Implementation Summary](../../docs/task_9_implementation_summary.md)
- [Requirements Document](../../../.kiro/specs/ai-agent/requirements.md)
- [Design Document](../../../.kiro/specs/ai-agent/design.md)

## Future Agents

The following agents are planned for future implementation:

- **Supervisor Agent** (Task 10) - Routes requests to specialized agents
- **Validation Agent** - Validates generated code quality and security
- **Test Generation Agent** - Generates unit tests for code
- **Optimization Agent** - Suggests performance optimizations

## Contributing

When adding new agents:

1. Create agent class in this directory
2. Implement required methods and interfaces
3. Add comprehensive unit tests
4. Add integration tests
5. Update this README
6. Add documentation in `docs/` directory
