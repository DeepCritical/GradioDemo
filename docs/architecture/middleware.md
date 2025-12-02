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
- `add_evidence(new_evidence: list[Evidence]) -> int`: Adds evidence with URL-based deduplication. Returns the number of new items added (excluding duplicates).
- `async search_related(query: str, n_results: int = 5) -> list[Evidence]`: Semantic search for related evidence using embedding service

**Initialization**:

<!--codeinclude-->
[Initialize Workflow State](../src/middleware/state_machine.py) start_line:98 end_line:110
<!--/codeinclude-->

**Access**:

<!--codeinclude-->
[Get Workflow State](../src/middleware/state_machine.py) start_line:115 end_line:129
<!--/codeinclude-->

## Workflow Manager

**File**: `src/middleware/workflow_manager.py`

**Purpose**: Coordinates parallel research loops

**Methods**:
- `async add_loop(loop_id: str, query: str) -> ResearchLoop`: Add a new research loop to manage
- `async run_loops_parallel(loop_configs: list[dict], loop_func: Callable, judge_handler: Any | None = None, budget_tracker: Any | None = None) -> list[Any]`: Run multiple research loops in parallel. Takes configuration dicts and a loop function.
- `async update_loop_status(loop_id: str, status: LoopStatus, error: str | None = None)`: Update loop status
- `async sync_loop_evidence_to_state(loop_id: str)`: Synchronize evidence from a specific loop to global state

**Features**:
- Uses `asyncio.gather()` for parallel execution
- Handles errors per loop (doesn't fail all if one fails)
- Tracks loop status: `pending`, `running`, `completed`, `failed`, `cancelled`
- Evidence deduplication across parallel loops

**Usage**:
```python
from src.middleware.workflow_manager import WorkflowManager

manager = WorkflowManager()
await manager.add_loop("loop1", "Research query 1")
await manager.add_loop("loop2", "Research query 2")

async def run_research(config: dict) -> str:
    loop_id = config["loop_id"]
    query = config["query"]
    # ... research logic ...
    return "report"

results = await manager.run_loops_parallel(
    loop_configs=[
        {"loop_id": "loop1", "query": "Research query 1"},
        {"loop_id": "loop2", "query": "Research query 2"},
    ],
    loop_func=run_research,
)
```

## Budget Tracker

**File**: `src/middleware/budget_tracker.py`

**Purpose**: Tracks and enforces resource limits

**Budget Components**:
- **Tokens**: LLM token usage
- **Time**: Elapsed time in seconds
- **Iterations**: Number of iterations

**Methods**:
- `create_budget(loop_id: str, tokens_limit: int = 100000, time_limit_seconds: float = 600.0, iterations_limit: int = 10) -> BudgetStatus`: Create a budget for a specific loop
- `add_tokens(loop_id: str, tokens: int)`: Add token usage to a loop's budget
- `start_timer(loop_id: str)`: Start time tracking for a loop
- `update_timer(loop_id: str)`: Update elapsed time for a loop
- `increment_iteration(loop_id: str)`: Increment iteration count for a loop
- `check_budget(loop_id: str) -> tuple[bool, str]`: Check if a loop's budget has been exceeded. Returns (exceeded: bool, reason: str)
- `can_continue(loop_id: str) -> bool`: Check if a loop can continue based on budget

**Token Estimation**:
- `estimate_tokens(text: str) -> int`: ~4 chars per token
- `estimate_llm_call_tokens(prompt: str, response: str) -> int`: Estimate LLM call tokens

**Usage**:
```python
from src.middleware.budget_tracker import BudgetTracker

tracker = BudgetTracker()
budget = tracker.create_budget(
    loop_id="research_loop",
    tokens_limit=100000,
    time_limit_seconds=600,
    iterations_limit=10
)
tracker.start_timer("research_loop")
# ... research operations ...
tracker.add_tokens("research_loop", 5000)
tracker.update_timer("research_loop")
exceeded, reason = tracker.check_budget("research_loop")
if exceeded:
    # Budget exceeded, stop research
    pass
if not tracker.can_continue("research_loop"):
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
