# Orchestrators API Reference

This page documents the API for DeepCritical orchestrators.

## IterativeResearchFlow

**Module**: `src.orchestrator.research_flow`

**Purpose**: Single-loop research with search-judge-synthesize cycles.

### Methods

#### `run`

<!--codeinclude-->
[IterativeResearchFlow.run](../src/orchestrator/research_flow.py) start_line:134 end_line:140
<!--/codeinclude-->

Runs iterative research flow.

**Parameters**:
- `query`: Research query string
- `background_context`: Background context (default: "")
- `output_length`: Optional description of desired output length (default: "")
- `output_instructions`: Optional additional instructions for report generation (default: "")
- `message_history`: Optional user conversation history in Pydantic AI `ModelMessage` format (default: None)

**Returns**: Final report string.

**Note**: The `message_history` parameter enables multi-turn conversations by providing context from previous interactions.

**Note**: `max_iterations`, `max_time_minutes`, and `token_budget` are constructor parameters, not `run()` parameters.

## DeepResearchFlow

**Module**: `src.orchestrator.research_flow`

**Purpose**: Multi-section parallel research with planning and synthesis.

### Methods

#### `run`

<!--codeinclude-->
[DeepResearchFlow.run](../src/orchestrator/research_flow.py) start_line:778 end_line:778
<!--/codeinclude-->

Runs deep research flow.

**Parameters**:
- `query`: Research query string
- `message_history`: Optional user conversation history in Pydantic AI `ModelMessage` format (default: None)

**Returns**: Final report string.

**Note**: The `message_history` parameter enables multi-turn conversations by providing context from previous interactions.

**Note**: `max_iterations_per_section`, `max_time_minutes`, and `token_budget` are constructor parameters, not `run()` parameters.

## GraphOrchestrator

**Module**: `src.orchestrator.graph_orchestrator`

**Purpose**: Graph-based execution using Pydantic AI agents as nodes.

### Methods

#### `run`

<!--codeinclude-->
[GraphOrchestrator.run](../src/orchestrator/graph_orchestrator.py) start_line:177 end_line:177
<!--/codeinclude-->

Runs graph-based research orchestration.

**Parameters**:
- `query`: Research query string
- `message_history`: Optional user conversation history in Pydantic AI `ModelMessage` format (default: None)

**Yields**: `AgentEvent` objects during graph execution.

**Note**: 
- `research_mode` and `use_graph` are constructor parameters, not `run()` parameters.
- The `message_history` parameter enables multi-turn conversations by providing context from previous interactions. Message history is stored in `GraphExecutionContext` and passed to agents during execution.

## Orchestrator Factory

**Module**: `src.orchestrator_factory`

**Purpose**: Factory for creating orchestrators.

### Functions

#### `create_orchestrator`

<!--codeinclude-->
[create_orchestrator](../src/orchestrator_factory.py) start_line:44 end_line:50
<!--/codeinclude-->

Creates an orchestrator instance.

**Parameters**:
- `search_handler`: Search handler protocol implementation (optional, required for simple mode)
- `judge_handler`: Judge handler protocol implementation (optional, required for simple mode)
- `config`: Configuration object (optional)
- `mode`: Orchestrator mode ("simple", "advanced", "magentic", "iterative", "deep", "auto", or None for auto-detect)
- `oauth_token`: Optional OAuth token from HuggingFace login (takes priority over env vars)

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

<!--codeinclude-->
[MagenticOrchestrator.run](../src/orchestrator_magentic.py) start_line:101 end_line:101
<!--/codeinclude-->

Runs Magentic orchestration.

**Parameters**:
- `query`: Research query string

**Yields**: `AgentEvent` objects converted from Magentic events.

**Note**: `max_rounds` and `max_stalls` are constructor parameters, not `run()` parameters.

**Requirements**:
- `agent-framework-core` package
- OpenAI API key

## See Also

- [Architecture - Orchestrators](../architecture/orchestrators.md) - Architecture overview
- [Graph Orchestration](../architecture/graph_orchestration.md) - Graph execution details
