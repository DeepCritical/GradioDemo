# Architecture Overview

DeepCritical is a deep research agent system that uses iterative search-and-judge loops to comprehensively answer research questions. The system supports multiple orchestration patterns, graph-based execution, parallel research workflows, and long-running task management with real-time streaming.

## Core Architecture

### Orchestration Patterns

1. **Graph Orchestrator** (`src/orchestrator/graph_orchestrator.py`):
   - Graph-based execution using Pydantic AI agents as nodes
   - Supports both iterative and deep research patterns
   - Node types: Agent, State, Decision, Parallel
   - Edge types: Sequential, Conditional, Parallel
   - Conditional routing based on knowledge gaps, budget, and iterations
   - Parallel execution for concurrent research loops
   - Event streaming via `AsyncGenerator[AgentEvent]` for real-time UI updates
   - Fallback to agent chains when graph execution is disabled

2. **Deep Research Flow** (`src/orchestrator/research_flow.py`):
   - **Pattern**: Planner → Parallel Iterative Loops (one per section) → Synthesis
   - Uses `PlannerAgent` to break query into report sections
   - Runs `IterativeResearchFlow` instances in parallel per section via `WorkflowManager`
   - Synthesizes results using `LongWriterAgent` or `ProofreaderAgent`
   - Supports both graph execution (`use_graph=True`) and agent chains (`use_graph=False`)
   - Budget tracking per section and globally
   - State synchronization across parallel loops

3. **Iterative Research Flow** (`src/orchestrator/research_flow.py`):
   - **Pattern**: Generate observations → Evaluate gaps → Select tools → Execute → Judge → Continue/Complete
   - Uses `KnowledgeGapAgent`, `ToolSelectorAgent`, `ThinkingAgent`, `WriterAgent`
   - `JudgeHandler` assesses evidence sufficiency
   - Iterates until research complete or constraints met (iterations, time, tokens)
   - Supports graph execution and agent chains

4. **Magentic Orchestrator** (`src/orchestrator_magentic.py`):
   - Multi-agent coordination using `agent-framework-core`
   - ChatAgent pattern with internal LLMs per agent
   - Uses `MagenticBuilder` with participants: searcher, hypothesizer, judge, reporter
   - Manager orchestrates agents via `OpenAIChatClient`
   - Requires OpenAI API key (function calling support)
   - Event-driven: converts Magentic events to `AgentEvent` for UI streaming
   - Supports long-running workflows with max rounds and stall/reset handling

5. **Hierarchical Orchestrator** (`src/orchestrator_hierarchical.py`):
   - Uses `SubIterationMiddleware` with `ResearchTeam` and `LLMSubIterationJudge`
   - Adapts Magentic ChatAgent to `SubIterationTeam` protocol
   - Event-driven via `asyncio.Queue` for coordination
   - Supports sub-iteration patterns for complex research tasks

6. **Legacy Simple Mode** (`src/legacy_orchestrator.py`):
   - Linear search-judge-synthesize loop
   - Uses `SearchHandlerProtocol` and `JudgeHandlerProtocol`
   - Generator-based design yielding `AgentEvent` objects
   - Backward compatibility for simple use cases

## Long-Running Task Support

The system is designed for long-running research tasks with comprehensive state management and streaming:

1. **Event Streaming**:
   - All orchestrators yield `AgentEvent` objects via `AsyncGenerator`
   - Real-time UI updates through Gradio chat interface
   - Event types: `started`, `searching`, `search_complete`, `judging`, `judge_complete`, `looping`, `synthesizing`, `hypothesizing`, `complete`, `error`
   - Metadata includes iteration numbers, tool names, result counts, durations

2. **Budget Tracking** (`src/middleware/budget_tracker.py`):
   - Per-loop and global budget management
   - Tracks: tokens, time (seconds), iterations
   - Budget enforcement at decision nodes
   - Token estimation (~4 chars per token)
   - Early termination when budgets exceeded
   - Budget summaries for monitoring

3. **Workflow Manager** (`src/middleware/workflow_manager.py`):
   - Coordinates parallel research loops
   - Tracks loop status: `pending`, `running`, `completed`, `failed`, `cancelled`
   - Synchronizes evidence between loops and global state
   - Handles errors per loop (doesn't fail all if one fails)
   - Supports loop cancellation and timeout handling
   - Evidence deduplication across parallel loops

4. **State Management** (`src/middleware/state_machine.py`):
   - Thread-safe isolation using `ContextVar` for concurrent requests
   - `WorkflowState` tracks: evidence, conversation history, embedding service
   - Evidence deduplication by URL
   - Semantic search via embedding service
   - State persistence across long-running workflows
   - Supports both iterative and deep research patterns

5. **Gradio UI** (`src/app.py`):
   - Real-time streaming of research progress
   - Accordion-based UI for pending/done operations
   - OAuth integration (HuggingFace)
   - Multiple backend support (API keys, free tier)
   - Handles long-running tasks with progress indicators
   - Event accumulation for pending operations

## Graph Architecture

The graph orchestrator (`src/orchestrator/graph_orchestrator.py`) implements a flexible graph-based execution model:

**Node Types**:

- **Agent Nodes**: Execute Pydantic AI agents (e.g., `KnowledgeGapAgent`, `ToolSelectorAgent`)
- **State Nodes**: Update or read workflow state (evidence, conversation)
- **Decision Nodes**: Make routing decisions (research complete?, budget exceeded?)
- **Parallel Nodes**: Execute multiple nodes concurrently (parallel research loops)

**Edge Types**:

- **Sequential Edges**: Always traversed (no condition)
- **Conditional Edges**: Traversed based on condition (e.g., if research complete → writer, else → tool selector)
- **Parallel Edges**: Used for parallel execution branches

**Graph Patterns**:

- **Iterative Graph**: `[Input] → [Thinking] → [Knowledge Gap] → [Decision: Complete?] → [Tool Selector] or [Writer]`
- **Deep Research Graph**: `[Input] → [Planner] → [Parallel Iterative Loops] → [Synthesizer]`

**Execution Flow**:

1. Graph construction from nodes and edges
2. Graph validation (no cycles, all nodes reachable)
3. Graph execution from entry node
4. Node execution based on type
5. Edge evaluation for next node(s)
6. Parallel execution via `asyncio.gather()`
7. State updates at state nodes
8. Event streaming for UI

## Key Components

- **Orchestrators**: Multiple orchestration patterns (`src/orchestrator/`, `src/orchestrator_*.py`)
- **Research Flows**: Iterative and deep research patterns (`src/orchestrator/research_flow.py`)
- **Graph Builder**: Graph construction utilities (`src/agent_factory/graph_builder.py`)
- **Agents**: Pydantic AI agents (`src/agents/`, `src/agent_factory/agents.py`)
- **Search Tools**: PubMed, ClinicalTrials.gov, Europe PMC, RAG (`src/tools/`)
- **Judge Handler**: LLM-based evidence assessment (`src/agent_factory/judges.py`)
- **Embeddings**: Semantic search & deduplication (`src/services/embeddings.py`)
- **Statistical Analyzer**: Modal sandbox execution (`src/services/statistical_analyzer.py`)
- **Middleware**: State management, budget tracking, workflow coordination (`src/middleware/`)
- **MCP Tools**: Claude Desktop integration (`src/mcp_tools.py`)
- **Gradio UI**: Web interface with MCP server and streaming (`src/app.py`)

## Research Team & Parallel Execution

The system supports complex research workflows through:

1. **WorkflowManager**: Coordinates multiple parallel research loops
   - Creates and tracks `ResearchLoop` instances
   - Runs loops in parallel via `asyncio.gather()`
   - Synchronizes evidence to global state
   - Handles loop failures gracefully

2. **Deep Research Pattern**: Breaks complex queries into sections
   - Planner creates report outline with sections
   - Each section runs as independent iterative research loop
   - Loops execute in parallel
   - Evidence shared across loops via global state
   - Final synthesis combines all section results

3. **State Synchronization**: Thread-safe evidence sharing
   - Evidence deduplication by URL
   - Global state accessible to all loops
   - Semantic search across all collected evidence
   - Conversation history tracking per iteration

## Configuration & Modes

- **Orchestrator Factory** (`src/orchestrator_factory.py`):
  - Auto-detects mode: "advanced" if OpenAI key available, else "simple"
  - Supports explicit mode selection: "simple", "magentic", "advanced"
  - Lazy imports for optional dependencies

- **Research Modes**:
  - `iterative`: Single research loop
  - `deep`: Multi-section parallel research
  - `auto`: Auto-detect based on query complexity

- **Execution Modes**:
  - `use_graph=True`: Graph-based execution (parallel, conditional routing)
  - `use_graph=False`: Agent chains (sequential, backward compatible)







