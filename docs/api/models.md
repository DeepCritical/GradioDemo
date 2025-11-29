# Models API Reference

This page documents the Pydantic models used throughout DeepCritical.

## Evidence

**Module**: `src.utils.models`

**Purpose**: Represents evidence from search results.

```python
class Evidence(BaseModel):
    citation: Citation
    content: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**Fields**:
- `citation`: Citation information (title, URL, date, authors)
- `content`: Evidence text content
- `relevance_score`: Relevance score (0.0-1.0)
- `metadata`: Additional metadata dictionary

## Citation

**Module**: `src.utils.models`

**Purpose**: Citation information for evidence.

```python
class Citation(BaseModel):
    title: str
    url: str
    date: str | None = None
    authors: list[str] = Field(default_factory=list)
```

**Fields**:
- `title`: Article/trial title
- `url`: Source URL
- `date`: Publication date (optional)
- `authors`: List of authors (optional)

## KnowledgeGapOutput

**Module**: `src.utils.models`

**Purpose**: Output from knowledge gap evaluation.

```python
class KnowledgeGapOutput(BaseModel):
    research_complete: bool
    outstanding_gaps: list[str] = Field(default_factory=list)
```

**Fields**:
- `research_complete`: Boolean indicating if research is complete
- `outstanding_gaps`: List of remaining knowledge gaps

## AgentSelectionPlan

**Module**: `src.utils.models`

**Purpose**: Plan for tool/agent selection.

```python
class AgentSelectionPlan(BaseModel):
    tasks: list[AgentTask] = Field(default_factory=list)
```

**Fields**:
- `tasks`: List of agent tasks to execute

## AgentTask

**Module**: `src.utils.models`

**Purpose**: Individual agent task.

```python
class AgentTask(BaseModel):
    agent_name: str
    query: str
    context: dict[str, Any] = Field(default_factory=dict)
```

**Fields**:
- `agent_name`: Name of agent to use
- `query`: Task query
- `context`: Additional context dictionary

## ReportDraft

**Module**: `src.utils.models`

**Purpose**: Draft structure for long-form reports.

```python
class ReportDraft(BaseModel):
    title: str
    sections: list[ReportSection] = Field(default_factory=list)
    references: list[Citation] = Field(default_factory=list)
```

**Fields**:
- `title`: Report title
- `sections`: List of report sections
- `references`: List of citations

## ReportSection

**Module**: `src.utils.models`

**Purpose**: Individual section in a report draft.

```python
class ReportSection(BaseModel):
    title: str
    content: str
    order: int
```

**Fields**:
- `title`: Section title
- `content`: Section content
- `order`: Section order number

## ParsedQuery

**Module**: `src.utils.models`

**Purpose**: Parsed and improved query.

```python
class ParsedQuery(BaseModel):
    original_query: str
    improved_query: str
    research_mode: Literal["iterative", "deep"]
    key_entities: list[str] = Field(default_factory=list)
    research_questions: list[str] = Field(default_factory=list)
```

**Fields**:
- `original_query`: Original query string
- `improved_query`: Refined query string
- `research_mode`: Research mode ("iterative" or "deep")
- `key_entities`: List of key entities
- `research_questions`: List of research questions

## Conversation

**Module**: `src.utils.models`

**Purpose**: Conversation history with iterations.

```python
class Conversation(BaseModel):
    iterations: list[IterationData] = Field(default_factory=list)
```

**Fields**:
- `iterations`: List of iteration data

## IterationData

**Module**: `src.utils.models`

**Purpose**: Data for a single iteration.

```python
class IterationData(BaseModel):
    iteration: int
    observations: str | None = None
    knowledge_gaps: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    findings: str | None = None
    thoughts: str | None = None
```

**Fields**:
- `iteration`: Iteration number
- `observations`: Generated observations
- `knowledge_gaps`: Identified knowledge gaps
- `tool_calls`: Tool calls made
- `findings`: Findings from tools
- `thoughts`: Agent thoughts

## AgentEvent

**Module**: `src.utils.models`

**Purpose**: Event emitted during research execution.

```python
class AgentEvent(BaseModel):
    type: str
    iteration: int | None = None
    data: dict[str, Any] = Field(default_factory=dict)
```

**Fields**:
- `type`: Event type (e.g., "started", "search_complete", "complete")
- `iteration`: Iteration number (optional)
- `data`: Event data dictionary

## BudgetStatus

**Module**: `src.utils.models`

**Purpose**: Current budget status.

```python
class BudgetStatus(BaseModel):
    tokens_used: int
    tokens_limit: int
    time_elapsed_seconds: float
    time_limit_seconds: float
    iterations: int
    iterations_limit: int
```

**Fields**:
- `tokens_used`: Tokens used so far
- `tokens_limit`: Token limit
- `time_elapsed_seconds`: Elapsed time in seconds
- `time_limit_seconds`: Time limit in seconds
- `iterations`: Current iteration count
- `iterations_limit`: Iteration limit

## See Also

- [Architecture - Agents](../architecture/agents.md) - How models are used
- [Configuration](../configuration/index.md) - Model configuration







