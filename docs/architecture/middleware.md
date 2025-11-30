# Middleware Architecture

DeepCritical uses middleware for state management, budget tracking, and workflow coordination.

## State Management

### WorkflowState

**File**: `src/middleware/state_machine.py`

**Purpose**: Thread-safe state management for research workflows

**Implementation**: Uses `ContextVar` for thread-safe isolation

**State Components**:
- `evidence: list[Evidence]`: Collected evidence from searches
- `conversation: Conversation`: Iteration history (gaps, tool calls, findings, thoughts)
- `embedding_service: Any`: Embedding service for semantic search

**Methods**:
- `add_evidence(evidence: Evidence)`: Adds evidence with URL-based deduplication
- `async search_related(query: str, top_k: int = 5) -> list[Evidence]`: Semantic search

**Initialization**:
```python
from src.middleware.state_machine import init_workflow_state

init_workflow_state(embedding_service)
```

**Access**:
```python
from src.middleware.state_machine import get_workflow_state

state = get_workflow_state()  # Auto-initializes if missing
```

## Workflow Manager

**File**: `src/middleware/workflow_manager.py`

**Purpose**: Coordinates parallel research loops

**Methods**:
- `add_loop(loop: ResearchLoop)`: Add a research loop to manage
- `async run_loops_parallel() -> list[ResearchLoop]`: Run all loops in parallel
- `update_loop_status(loop_id: str, status: str)`: Update loop status
- `sync_loop_evidence_to_state()`: Synchronize evidence from loops to global state

**Features**:
- Uses `asyncio.gather()` for parallel execution
- Handles errors per loop (doesn't fail all if one fails)
- Tracks loop status: `pending`, `running`, `completed`, `failed`, `cancelled`
- Evidence deduplication across parallel loops

**Usage**:
```python
from src.middleware.workflow_manager import WorkflowManager

manager = WorkflowManager()
manager.add_loop(loop1)
manager.add_loop(loop2)
completed_loops = await manager.run_loops_parallel()
```

## Budget Tracker

**File**: `src/middleware/budget_tracker.py`

**Purpose**: Tracks and enforces resource limits

**Budget Components**:
- **Tokens**: LLM token usage
- **Time**: Elapsed time in seconds
- **Iterations**: Number of iterations

**Methods**:
- `create_budget(token_limit, time_limit_seconds, iterations_limit) -> BudgetStatus`
- `add_tokens(tokens: int)`: Add token usage
- `start_timer()`: Start time tracking
- `update_timer()`: Update elapsed time
- `increment_iteration()`: Increment iteration count
- `check_budget() -> BudgetStatus`: Check current budget status
- `can_continue() -> bool`: Check if research can continue

**Token Estimation**:
- `estimate_tokens(text: str) -> int`: ~4 chars per token
- `estimate_llm_call_tokens(prompt: str, response: str) -> int`: Estimate LLM call tokens

**Usage**:
```python
from src.middleware.budget_tracker import BudgetTracker

tracker = BudgetTracker()
budget = tracker.create_budget(
    token_limit=100000,
    time_limit_seconds=600,
    iterations_limit=10
)
tracker.start_timer()
# ... research operations ...
if not tracker.can_continue():
    # Budget exceeded, stop research
    pass
```

## Models

All middleware models are defined in `src/utils/models.py`:

- `IterationData`: Data for a single iteration
- `Conversation`: Conversation history with iterations
- `ResearchLoop`: Research loop state and configuration
- `BudgetStatus`: Current budget status

## Thread Safety

All middleware components use `ContextVar` for thread-safe isolation:

- Each request/thread has its own workflow state
- No global mutable state
- Safe for concurrent requests

## See Also

- [Orchestrators](orchestrators.md) - How middleware is used in orchestration
- [API Reference - Orchestrators](../api/orchestrators.md) - API documentation
- [Contributing - Code Style](../contributing/code-style.md) - Development guidelines















<<<<<<< Updated upstream





=======
>>>>>>> Stashed changes
