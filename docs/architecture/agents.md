# Agents Architecture

DeepCritical uses Pydantic AI agents for all AI-powered operations. All agents follow a consistent pattern and use structured output types.

## Agent Pattern

All agents use the Pydantic AI `Agent` class with the following structure:

- **System Prompt**: Module-level constant with date injection
- **Agent Class**: `__init__(model: Any | None = None)`
- **Main Method**: Async method (e.g., `async def evaluate()`, `async def write_report()`)
- **Factory Function**: `def create_agent_name(model: Any | None = None) -> AgentName`

## Model Initialization

Agents use `get_model()` from `src/agent_factory/judges.py` if no model is provided. This supports:

- OpenAI models
- Anthropic models
- HuggingFace Inference API models

The model selection is based on the configured `LLM_PROVIDER` in settings.

## Error Handling

Agents return fallback values on failure rather than raising exceptions:

- `KnowledgeGapOutput(research_complete=False, outstanding_gaps=[...])`
- Empty strings for text outputs
- Default structured outputs

All errors are logged with context using structlog.

## Input Validation

All agents validate inputs:

- Check that queries/inputs are not empty
- Truncate very long inputs with warnings
- Handle None values gracefully

## Output Types

Agents use structured output types from `src/utils/models.py`:

- `KnowledgeGapOutput`: Research completeness evaluation
- `AgentSelectionPlan`: Tool selection plan
- `ReportDraft`: Long-form report structure
- `ParsedQuery`: Query parsing and mode detection

For text output (writer agents), agents return `str` directly.

## Agent Types

### Knowledge Gap Agent

**File**: `src/agents/knowledge_gap.py`

**Purpose**: Evaluates research state and identifies knowledge gaps.

**Output**: `KnowledgeGapOutput` with:
- `research_complete`: Boolean indicating if research is complete
- `outstanding_gaps`: List of remaining knowledge gaps

**Methods**:
- `async def evaluate(query, background_context, conversation_history, iteration, time_elapsed_minutes, max_time_minutes) -> KnowledgeGapOutput`

### Tool Selector Agent

**File**: `src/agents/tool_selector.py`

**Purpose**: Selects appropriate tools for addressing knowledge gaps.

**Output**: `AgentSelectionPlan` with list of `AgentTask` objects.

**Available Agents**:
- `WebSearchAgent`: General web search for fresh information
- `SiteCrawlerAgent`: Research specific entities/companies
- `RAGAgent`: Semantic search within collected evidence

### Writer Agent

**File**: `src/agents/writer.py`

**Purpose**: Generates final reports from research findings.

**Output**: Markdown string with numbered citations.

**Methods**:
- `async def write_report(query, findings, output_length, output_instructions) -> str`

**Features**:
- Validates inputs
- Truncates very long findings (max 50000 chars) with warning
- Retry logic for transient failures (3 retries)
- Citation validation before returning

### Long Writer Agent

**File**: `src/agents/long_writer.py`

**Purpose**: Long-form report generation with section-by-section writing.

**Input/Output**: Uses `ReportDraft` models.

**Methods**:
- `async def write_next_section(query, draft, section_title, section_content) -> LongWriterOutput`
- `async def write_report(query, report_title, report_draft) -> str`

**Features**:
- Writes sections iteratively
- Aggregates references across sections
- Reformats section headings and references
- Deduplicates and renumbers references

### Proofreader Agent

**File**: `src/agents/proofreader.py`

**Purpose**: Proofreads and polishes report drafts.

**Input**: `ReportDraft`
**Output**: Polished markdown string

**Methods**:
- `async def proofread(query, report_title, report_draft) -> str`

**Features**:
- Removes duplicate content across sections
- Adds executive summary if multiple sections
- Preserves all references and citations
- Improves flow and readability

### Thinking Agent

**File**: `src/agents/thinking.py`

**Purpose**: Generates observations from conversation history.

**Output**: Observation string

**Methods**:
- `async def generate_observations(query, background_context, conversation_history) -> str`

### Input Parser Agent

**File**: `src/agents/input_parser.py`

**Purpose**: Parses and improves user queries, detects research mode.

**Output**: `ParsedQuery` with:
- `original_query`: Original query string
- `improved_query`: Refined query string
- `research_mode`: "iterative" or "deep"
- `key_entities`: List of key entities
- `research_questions`: List of research questions

## Factory Functions

All agents have factory functions in `src/agent_factory/agents.py`:

```python
def create_knowledge_gap_agent(model: Any | None = None) -> KnowledgeGapAgent
def create_tool_selector_agent(model: Any | None = None) -> ToolSelectorAgent
def create_writer_agent(model: Any | None = None) -> WriterAgent
# ... etc
```

Factory functions:
- Use `get_model()` if no model provided
- Raise `ConfigurationError` if creation fails
- Log agent creation

## See Also

- [Orchestrators](orchestrators.md) - How agents are orchestrated
- [API Reference - Agents](../api/agents.md) - API documentation
- [Contributing - Code Style](../contributing/code-style.md) - Development guidelines














