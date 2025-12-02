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

<!--codeinclude-->
[IterativeResearchFlow Initialization](../src/orchestrator/research_flow.py) start_line:57 end_line:80
<!--/codeinclude-->

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

<!--codeinclude-->
[DeepResearchFlow Initialization](../src/orchestrator/research_flow.py) start_line:709 end_line:728
<!--/codeinclude-->

## Graph Orchestrator

**File**: `src/orchestrator/graph_orchestrator.py`

**Purpose**: Graph-based execution using Pydantic AI agents as nodes

**Features**:
- Uses graph execution (`use_graph=True`) or agent chains (`use_graph=False`) as fallback
- Routes based on research mode (iterative/deep/auto)
- Streams `AgentEvent` objects for UI
- Uses `GraphExecutionContext` to manage execution state

**Node Types**:
- **Agent Nodes**: Execute Pydantic AI agents
- **State Nodes**: Update or read workflow state
- **Decision Nodes**: Make routing decisions
- **Parallel Nodes**: Execute multiple nodes concurrently

**Edge Types**:
- **Sequential Edges**: Always traversed
- **Conditional Edges**: Traversed based on condition
- **Parallel Edges**: Used for parallel execution branches

**Special Node Handling**:

The `GraphOrchestrator` has special handling for certain nodes:

- **`execute_tools` node**: State node that uses `search_handler` to execute searches and add evidence to workflow state
- **`parallel_loops` node**: Parallel node that executes `IterativeResearchFlow` instances for each section in deep research mode
- **`synthesizer` node**: Agent node that calls `LongWriterAgent.write_report()` directly with `ReportDraft` instead of using `agent.run()`
- **`writer` node**: Agent node that calls `WriterAgent.write_report()` directly with findings instead of using `agent.run()`

**GraphExecutionContext**:

The orchestrator uses `GraphExecutionContext` to manage execution state:
- Tracks current node, visited nodes, and node results
- Manages workflow state and budget tracker
- Provides methods to store and retrieve node execution results

## Orchestrator Factory

**File**: `src/orchestrator_factory.py`

**Purpose**: Factory for creating orchestrators

**Modes**:
- **Simple**: Legacy orchestrator (backward compatible)
- **Advanced**: Magentic orchestrator (requires OpenAI API key)
- **Auto-detect**: Chooses based on API key availability

**Usage**:

<!--codeinclude-->
[Create Orchestrator](../src/orchestrator_factory.py) start_line:44 end_line:66
<!--/codeinclude-->

## Magentic Orchestrator

**File**: `src/orchestrator_magentic.py`

**Purpose**: Multi-agent coordination using Microsoft Agent Framework

**Features**:
- Uses `agent-framework-core`
- ChatAgent pattern with internal LLMs per agent
- `MagenticBuilder` with participants:
  - `searcher`: SearchAgent (wraps SearchHandler)
  - `hypothesizer`: HypothesisAgent (generates hypotheses)
  - `judge`: JudgeAgent (evaluates evidence)
  - `reporter`: ReportAgent (generates final report)
- Manager orchestrates agents via chat client (OpenAI or HuggingFace)
- Event-driven: converts Magentic events to `AgentEvent` for UI streaming via `_process_event()` method
- Supports max rounds, stall detection, and reset handling

**Event Processing**:

The orchestrator processes Magentic events and converts them to `AgentEvent`:
- `MagenticOrchestratorMessageEvent` → `AgentEvent` with type based on message content
- `MagenticAgentMessageEvent` → `AgentEvent` with type based on agent name
- `MagenticAgentDeltaEvent` → `AgentEvent` for streaming updates
- `MagenticFinalResultEvent` → `AgentEvent` with type "complete"

**Requirements**:
- `agent-framework-core` package
- OpenAI API key or HuggingFace authentication

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

<!--codeinclude-->
[Initialize Workflow State](../src/middleware/state_machine.py) start_line:98 end_line:112
<!--/codeinclude-->

## Event Streaming

All orchestrators yield `AgentEvent` objects:

**Event Types**:
- `started`: Research started
- `searching`: Search in progress
- `search_complete`: Search completed
- `judging`: Evidence evaluation in progress
- `judge_complete`: Evidence evaluation completed
- `looping`: Iteration in progress
- `hypothesizing`: Generating hypotheses
- `analyzing`: Statistical analysis in progress
- `analysis_complete`: Statistical analysis completed
- `synthesizing`: Synthesizing results
- `complete`: Research completed
- `error`: Error occurred
- `streaming`: Streaming update (delta events)

**Event Structure**:

<!--codeinclude-->
[AgentEvent Model](../src/utils/models.py) start_line:104 end_line:126
<!--/codeinclude-->

## See Also

- [Graph Orchestration](graph_orchestration.md) - Graph-based execution details
- [Workflow Diagrams](workflow-diagrams.md) - Detailed workflow diagrams
- [API Reference - Orchestrators](../api/orchestrators.md) - API documentation

