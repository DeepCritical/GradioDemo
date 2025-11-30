# Orchestrators API Reference

This page documents the API for DeepCritical orchestrators.

## IterativeResearchFlow

**Module**: `src.orchestrator.research_flow`

**Purpose**: Single-loop research with search-judge-synthesize cycles.

### Methods

#### `run`

```python
async def run(
    self,
    query: str,
    background_context: str = "",
    max_iterations: int | None = None,
    max_time_minutes: float | None = None,
    token_budget: int | None = None
) -> AsyncGenerator[AgentEvent, None]
```

Runs iterative research flow.

**Parameters**:
- `query`: Research query string
- `background_context`: Background context (default: "")
- `max_iterations`: Maximum iterations (default: from settings)
- `max_time_minutes`: Maximum time in minutes (default: from settings)
- `token_budget`: Token budget (default: from settings)

**Yields**: `AgentEvent` objects for:
- `started`: Research started
- `search_complete`: Search completed
- `judge_complete`: Evidence evaluation completed
- `synthesizing`: Generating report
- `complete`: Research completed
- `error`: Error occurred

## DeepResearchFlow

**Module**: `src.orchestrator.research_flow`

**Purpose**: Multi-section parallel research with planning and synthesis.

### Methods

#### `run`

```python
async def run(
    self,
    query: str,
    background_context: str = "",
    max_iterations_per_section: int | None = None,
    max_time_minutes: float | None = None,
    token_budget: int | None = None
) -> AsyncGenerator[AgentEvent, None]
```

Runs deep research flow.

**Parameters**:
- `query`: Research query string
- `background_context`: Background context (default: "")
- `max_iterations_per_section`: Maximum iterations per section (default: from settings)
- `max_time_minutes`: Maximum time in minutes (default: from settings)
- `token_budget`: Token budget (default: from settings)

**Yields**: `AgentEvent` objects for:
- `started`: Research started
- `planning`: Creating research plan
- `looping`: Running parallel research loops
- `synthesizing`: Synthesizing results
- `complete`: Research completed
- `error`: Error occurred

## GraphOrchestrator

**Module**: `src.orchestrator.graph_orchestrator`

**Purpose**: Graph-based execution using Pydantic AI agents as nodes.

### Methods

#### `run`

```python
async def run(
    self,
    query: str,
    research_mode: str = "auto",
    use_graph: bool = True
) -> AsyncGenerator[AgentEvent, None]
```

Runs graph-based research orchestration.

**Parameters**:
- `query`: Research query string
- `research_mode`: Research mode ("iterative", "deep", or "auto")
- `use_graph`: Whether to use graph execution (default: True)

**Yields**: `AgentEvent` objects during graph execution.

## Orchestrator Factory

**Module**: `src.orchestrator_factory`

**Purpose**: Factory for creating orchestrators.

### Functions

#### `create_orchestrator`

```python
def create_orchestrator(
    search_handler: SearchHandlerProtocol,
    judge_handler: JudgeHandlerProtocol,
    config: dict[str, Any],
    mode: str | None = None
) -> Any
```

Creates an orchestrator instance.

**Parameters**:
- `search_handler`: Search handler protocol implementation
- `judge_handler`: Judge handler protocol implementation
- `config`: Configuration dictionary
- `mode`: Orchestrator mode ("simple", "advanced", "magentic", or None for auto-detect)

**Returns**: Orchestrator instance.

**Raises**:
- `ValueError`: If requirements not met

**Modes**:
- `"simple"`: Legacy orchestrator
- `"advanced"` or `"magentic"`: Magentic orchestrator (requires OpenAI API key)
- `None`: Auto-detect based on API key availability

## MagenticOrchestrator

**Module**: `src.orchestrator_magentic`

**Purpose**: Multi-agent coordination using Microsoft Agent Framework.

### Methods

#### `run`

```python
async def run(
    self,
    query: str,
    max_rounds: int = 15,
    max_stalls: int = 3
) -> AsyncGenerator[AgentEvent, None]
```

Runs Magentic orchestration.

**Parameters**:
- `query`: Research query string
- `max_rounds`: Maximum rounds (default: 15)
- `max_stalls`: Maximum stalls before reset (default: 3)

**Yields**: `AgentEvent` objects converted from Magentic events.

**Requirements**:
- `agent-framework-core` package
- OpenAI API key

## See Also

- [Architecture - Orchestrators](../architecture/orchestrators.md) - Architecture overview
- [Graph Orchestration](../architecture/graph-orchestration.md) - Graph execution details















