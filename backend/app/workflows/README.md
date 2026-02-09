# LangGraph Workflow Orchestration

This module implements the LangGraph workflow for orchestrating the AI Agent System's multi-agent architecture.

## Overview

The workflow manages the interaction between three specialized agents:
1. **Supervisor Agent**: Analyzes prompts and determines routing strategy
2. **Documentation Search Agent**: Performs semantic search across framework documentation
3. **Code Generation Agent**: Generates syntactically correct, framework-compliant code

## Architecture

### Workflow Graph

```
┌─────────────┐
│   Client    │
│   Request   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Supervisor  │──────┐
│    Node     │      │
└──────┬──────┘      │
       │             │
       ▼             │
  ┌────────┐         │
  │ Route? │         │
  └───┬────┘         │
      │              │
  ┌───┴────┬─────────┴──┐
  │        │            │
  ▼        ▼            ▼
Search   Code Gen     END
  │        │
  │        ▼
  │   ┌─────────┐
  │   │Validate │
  │   └────┬────┘
  │        │
  │    ┌───┴────┐
  │    │ Retry? │
  │    └───┬────┘
  │        │
  └────────┴──────► END
     (cycle)
```

### Workflow Nodes

#### 1. Supervisor Node
- **Purpose**: Analyze prompt and determine routing strategy
- **Input**: User prompt, trace_id
- **Output**: Routing strategy (SEARCH_ONLY, CODE_ONLY, SEARCH_THEN_CODE)
- **State Updates**: Sets `routing_strategy`

#### 2. Search Node
- **Purpose**: Perform semantic documentation search
- **Input**: Query, optional framework filter
- **Output**: List of documentation results with scores
- **State Updates**: Sets `documentation_results`

#### 3. Code Generation Node
- **Purpose**: Generate framework-compliant code
- **Input**: Prompt, optional documentation context
- **Output**: Generated code with validation status
- **State Updates**: Sets `generated_code`, `code_generation_result`

#### 4. Validation Node
- **Purpose**: Validate code and determine if retry is needed
- **Input**: Generated code, iteration count
- **Output**: Validation results
- **State Updates**: Increments `iteration_count`

### Conditional Routing

#### After Supervisor
- **SEARCH_ONLY** → Search Node → END
- **CODE_ONLY** → Code Gen Node → Validate Node → END
- **SEARCH_THEN_CODE** → Search Node → Code Gen Node → Validate Node

#### After Validation
- **Retry** (if syntax errors and iterations < max) → Search Node (cycle)
- **Done** (if valid or max iterations reached) → END

## State Management

### WorkflowState Schema

```python
class WorkflowState(TypedDict):
    prompt: str                                    # User's input prompt
    routing_strategy: RoutingStrategy              # Determined by supervisor
    documentation_results: Optional[List[...]]     # Search results
    generated_code: Optional[str]                  # Generated code
    framework: Optional[str]                       # Target framework
    iteration_count: int                           # Current iteration
    max_iterations: int                            # Maximum allowed iterations
    trace_id: str                                  # Request tracing ID
    errors: List[str]                              # Accumulated errors
```

### State Persistence

- State is automatically persisted by LangGraph between node transitions
- Each node receives the complete state and returns an updated state
- State validation ensures required fields are present at each node

### State Validation Rules

1. **Required Fields**: `prompt`, `trace_id`, `max_iterations`
2. **Defaults**: `max_iterations=3`, `iteration_count=0`, `errors=[]`
3. **Error Handling**: Errors accumulate in `errors` list without breaking workflow

## Cycle Support

The workflow supports iterative refinement through cycles:

### Cycle Trigger Conditions
1. **Syntax Errors**: Code has validation errors
2. **Under Max Iterations**: `iteration_count < max_iterations`

### Cycle Flow
```
Search → Code Gen → Validate → (if retry) → Search → ...
```

### Max Iterations
- Default: 3 iterations
- Configurable per request
- Prevents infinite loops

## Usage

### Basic Usage

```python
from app.workflows.agent_workflow import agent_workflow

# Execute workflow
response = await agent_workflow.execute(
    prompt="Create a NestJS controller for user authentication",
    trace_id="unique-trace-id",
    context={"framework": "NestJS"},
    max_iterations=3
)

print(response.result)
print(response.metadata.agents_invoked)
print(response.metadata.workflow_iterations)
```

### Custom Agent Configuration

```python
from app.workflows.agent_workflow import AgentWorkflow
from app.agents.supervisor_agent import SupervisorAgent
from app.agents.documentation_search_agent import DocumentationSearchAgent
from app.agents.code_gen_agent import CodeGenAgent

# Create custom agents
supervisor = SupervisorAgent(model="gpt-4")
search_agent = DocumentationSearchAgent()
code_gen_agent = CodeGenAgent(max_retries=3)

# Create workflow with custom agents
workflow = AgentWorkflow(
    supervisor=supervisor,
    search_agent=search_agent,
    code_gen_agent=code_gen_agent
)

# Execute
response = await workflow.execute(
    prompt="Your prompt here",
    trace_id="trace-id"
)
```

## Response Format

### AgentResponse

```python
{
    "result": "Generated code or search results",
    "metadata": {
        "trace_id": "unique-trace-id",
        "cache_hit": false,
        "processing_time_ms": 1234.56,
        "tokens_used": 500,
        "agents_invoked": ["supervisor", "documentation_search", "code_gen"],
        "workflow_iterations": 1
    }
}
```

## Testing

### Unit Tests
Located in `tests/test_agent_workflow.py`:
- Individual node testing
- Conditional routing logic
- Cycle support
- State management

### Integration Tests
Located in `tests/test_workflow_integration.py`:
- End-to-end workflow execution
- Different routing strategies
- Max iterations enforcement
- State persistence

### Running Tests

```bash
# Run all workflow tests
pytest tests/test_agent_workflow.py tests/test_workflow_integration.py -v

# Run specific test class
pytest tests/test_agent_workflow.py::TestWorkflowNodes -v

# Run with coverage
pytest tests/test_agent_workflow.py --cov=app.workflows
```

## Error Handling

### Error Accumulation
- Errors are collected in `state["errors"]` list
- Workflow continues even with errors in individual nodes
- Final response includes error information

### Graceful Degradation
- Node failures don't crash the entire workflow
- Missing data is handled with defaults
- Validation ensures state consistency

### Error Response Format

```python
{
    "result": "Workflow completed with errors:\n- Error 1\n- Error 2",
    "metadata": {
        "trace_id": "trace-id",
        "cache_hit": false,
        "processing_time_ms": 500.0,
        "tokens_used": 0,
        "agents_invoked": ["supervisor"],
        "workflow_iterations": 0
    }
}
```

## Performance Considerations

### Async Execution
- All agent calls use `asyncio.run()` for non-blocking execution
- Database operations are async
- LLM API calls are async

### Caching
- Semantic cache checked before workflow execution (in API layer)
- Tool-level cache for documentation search results
- Cache hits bypass workflow execution

### Optimization Tips
1. Set appropriate `max_iterations` based on use case
2. Use framework filters in search to reduce result set
3. Monitor `processing_time_ms` and `tokens_used` metrics
4. Enable caching for repeated queries

## Observability

### Logging
All nodes log:
- Entry and exit with trace_id
- State transitions
- Errors and warnings
- Performance metrics

### Tracing
- Each request has unique `trace_id`
- Trace_id propagates through all nodes
- Enables end-to-end request tracking

### Metrics
Response metadata includes:
- `processing_time_ms`: Total execution time
- `tokens_used`: LLM token consumption
- `agents_invoked`: Which agents were called
- `workflow_iterations`: Number of cycles

## Future Enhancements

1. **Parallel Execution**: Support for PARALLEL routing strategy
2. **Streaming Responses**: Stream results as they're generated
3. **Checkpointing**: Save and resume workflow state
4. **Dynamic Routing**: ML-based routing decisions
5. **Agent Composition**: Support for custom agent pipelines

## References

- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [Design Document](../../.kiro/specs/ai-agent/design.md)
- [Requirements Document](../../.kiro/specs/ai-agent/requirements.md)
