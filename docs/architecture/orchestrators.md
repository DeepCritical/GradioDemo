# Orchestrators Architecture

DeepCritical supports multiple orchestration patterns for research workflows.

## Research Flows

### IterativeResearchFlow

**File**: `src/orchestrator/research_flow.py`

**Pattern**: Generate observations → Evaluate gaps → Select tools → Execute → Judge → Continue/Complete

**Agents Used**:
- `KnowledgeGapAgent`: Evaluates research completeness
- `ToolSelectorAgent`: Selects tools for addressing gaps
- `ThinkingAgent`: Generates observations
- `WriterAgent`: Creates final report
- `JudgeHandler`: Assesses evidence sufficiency

**Features**:
- Tracks iterations, time, budget
- Supports graph execution (`use_graph=True`) and agent chains (`use_graph=False`)
- Iterates until research complete or constraints met

**Usage**:
```python
from src.orchestrator.research_flow import IterativeResearchFlow

flow = IterativeResearchFlow(
    search_handler=search_handler,
    judge_handler=judge_handler,
    use_graph=False
)

async for event in flow.run(query):
    # Handle events
    pass
```

### DeepResearchFlow

**File**: `src/orchestrator/research_flow.py`

**Pattern**: Planner → Parallel iterative loops per section → Synthesizer

**Agents Used**:
- `PlannerAgent`: Breaks query into report sections
- `IterativeResearchFlow`: Per-section research (parallel)
- `LongWriterAgent` or `ProofreaderAgent`: Final synthesis

**Features**:
- Uses `WorkflowManager` for parallel execution
- Budget tracking per section and globally
- State synchronization across parallel loops
- Supports graph execution and agent chains

**Usage**:
```python
from src.orchestrator.research_flow import DeepResearchFlow

flow = DeepResearchFlow(
    search_handler=search_handler,
    judge_handler=judge_handler,
    use_graph=True
)

async for event in flow.run(query):
    # Handle events
    pass
```

## Graph Orchestrator

**File**: `src/orchestrator/graph_orchestrator.py`

**Purpose**: Graph-based execution using Pydantic AI agents as nodes

**Features**:
- Uses Pydantic AI Graphs (when available) or agent chains (fallback)
- Routes based on research mode (iterative/deep/auto)
- Streams `AgentEvent` objects for UI

**Node Types**:
- **Agent Nodes**: Execute Pydantic AI agents
- **State Nodes**: Update or read workflow state
- **Decision Nodes**: Make routing decisions
- **Parallel Nodes**: Execute multiple nodes concurrently

**Edge Types**:
- **Sequential Edges**: Always traversed
- **Conditional Edges**: Traversed based on condition
- **Parallel Edges**: Used for parallel execution branches

## Orchestrator Factory

**File**: `src/orchestrator_factory.py`

**Purpose**: Factory for creating orchestrators

**Modes**:
- **Simple**: Legacy orchestrator (backward compatible)
- **Advanced**: Magentic orchestrator (requires OpenAI API key)
- **Auto-detect**: Chooses based on API key availability

**Usage**:
```python
from src.orchestrator_factory import create_orchestrator

orchestrator = create_orchestrator(
    search_handler=search_handler,
    judge_handler=judge_handler,
    config={},
    mode="advanced"  # or "simple" or None for auto-detect
)
```

## Magentic Orchestrator

**File**: `src/orchestrator_magentic.py`

**Purpose**: Multi-agent coordination using Microsoft Agent Framework

**Features**:
- Uses `agent-framework-core`
- ChatAgent pattern with internal LLMs per agent
- `MagenticBuilder` with participants: searcher, hypothesizer, judge, reporter
- Manager orchestrates agents via `OpenAIChatClient`
- Requires OpenAI API key (function calling support)
- Event-driven: converts Magentic events to `AgentEvent` for UI streaming

**Requirements**:
- `agent-framework-core` package
- OpenAI API key

## Hierarchical Orchestrator

**File**: `src/orchestrator_hierarchical.py`

**Purpose**: Hierarchical orchestrator using middleware and sub-teams

**Features**:
- Uses `SubIterationMiddleware` with `ResearchTeam` and `LLMSubIterationJudge`
- Adapts Magentic ChatAgent to `SubIterationTeam` protocol
- Event-driven via `asyncio.Queue` for coordination
- Supports sub-iteration patterns for complex research tasks

## Legacy Simple Mode

**File**: `src/legacy_orchestrator.py`

**Purpose**: Linear search-judge-synthesize loop

**Features**:
- Uses `SearchHandlerProtocol` and `JudgeHandlerProtocol`
- Generator-based design yielding `AgentEvent` objects
- Backward compatibility for simple use cases

## State Initialization

All orchestrators must initialize workflow state:

```python
from src.middleware.state_machine import init_workflow_state
from src.services.embeddings import get_embedding_service

embedding_service = get_embedding_service()
init_workflow_state(embedding_service)
```

## Event Streaming

All orchestrators yield `AgentEvent` objects:

**Event Types**:
- `started`: Research started
- `search_complete`: Search completed
- `judge_complete`: Evidence evaluation completed
- `hypothesizing`: Generating hypotheses
- `synthesizing`: Synthesizing results
- `complete`: Research completed
- `error`: Error occurred

**Event Structure**:
```python
class AgentEvent:
    type: str
    iteration: int | None
    data: dict[str, Any]
```

## See Also

- [Graph Orchestration](graph-orchestration.md) - Graph-based execution details
- [Graph Orchestration (Detailed)](graph_orchestration.md) - Detailed graph architecture
- [Workflows](workflows.md) - Workflow diagrams and patterns
- [Workflow Diagrams](workflow-diagrams.md) - Detailed workflow diagrams
- [API Reference - Orchestrators](../api/orchestrators.md) - API documentation

