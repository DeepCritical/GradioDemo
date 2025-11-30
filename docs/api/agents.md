# Agents API Reference

This page documents the API for DeepCritical agents.

## KnowledgeGapAgent

**Module**: `src.agents.knowledge_gap`

**Purpose**: Evaluates research state and identifies knowledge gaps.

### Methods

#### `evaluate`

```python
async def evaluate(
    self,
    query: str,
    background_context: str,
    conversation_history: Conversation,
    iteration: int,
    time_elapsed_minutes: float,
    max_time_minutes: float
) -> KnowledgeGapOutput
```

Evaluates research completeness and identifies outstanding knowledge gaps.

**Parameters**:
- `query`: Research query string
- `background_context`: Background context for the query
- `conversation_history`: Conversation history with previous iterations
- `iteration`: Current iteration number
- `time_elapsed_minutes`: Elapsed time in minutes
- `max_time_minutes`: Maximum time limit in minutes

**Returns**: `KnowledgeGapOutput` with:
- `research_complete`: Boolean indicating if research is complete
- `outstanding_gaps`: List of remaining knowledge gaps

## ToolSelectorAgent

**Module**: `src.agents.tool_selector`

**Purpose**: Selects appropriate tools for addressing knowledge gaps.

### Methods

#### `select_tools`

```python
async def select_tools(
    self,
    query: str,
    knowledge_gaps: list[str],
    available_tools: list[str]
) -> AgentSelectionPlan
```

Selects tools for addressing knowledge gaps.

**Parameters**:
- `query`: Research query string
- `knowledge_gaps`: List of knowledge gaps to address
- `available_tools`: List of available tool names

**Returns**: `AgentSelectionPlan` with list of `AgentTask` objects.

## WriterAgent

**Module**: `src.agents.writer`

**Purpose**: Generates final reports from research findings.

### Methods

#### `write_report`

```python
async def write_report(
    self,
    query: str,
    findings: str,
    output_length: str = "medium",
    output_instructions: str | None = None
) -> str
```

Generates a markdown report from research findings.

**Parameters**:
- `query`: Research query string
- `findings`: Research findings to include in report
- `output_length`: Desired output length ("short", "medium", "long")
- `output_instructions`: Additional instructions for report generation

**Returns**: Markdown string with numbered citations.

## LongWriterAgent

**Module**: `src.agents.long_writer`

**Purpose**: Long-form report generation with section-by-section writing.

### Methods

#### `write_next_section`

```python
async def write_next_section(
    self,
    query: str,
    draft: ReportDraft,
    section_title: str,
    section_content: str
) -> LongWriterOutput
```

Writes the next section of a long-form report.

**Parameters**:
- `query`: Research query string
- `draft`: Current report draft
- `section_title`: Title of the section to write
- `section_content`: Content/guidance for the section

**Returns**: `LongWriterOutput` with updated draft.

#### `write_report`

```python
async def write_report(
    self,
    query: str,
    report_title: str,
    report_draft: ReportDraft
) -> str
```

Generates final report from draft.

**Parameters**:
- `query`: Research query string
- `report_title`: Title of the report
- `report_draft`: Complete report draft

**Returns**: Final markdown report string.

## ProofreaderAgent

**Module**: `src.agents.proofreader`

**Purpose**: Proofreads and polishes report drafts.

### Methods

#### `proofread`

```python
async def proofread(
    self,
    query: str,
    report_title: str,
    report_draft: ReportDraft
) -> str
```

Proofreads and polishes a report draft.

**Parameters**:
- `query`: Research query string
- `report_title`: Title of the report
- `report_draft`: Report draft to proofread

**Returns**: Polished markdown string.

## ThinkingAgent

**Module**: `src.agents.thinking`

**Purpose**: Generates observations from conversation history.

### Methods

#### `generate_observations`

```python
async def generate_observations(
    self,
    query: str,
    background_context: str,
    conversation_history: Conversation
) -> str
```

Generates observations from conversation history.

**Parameters**:
- `query`: Research query string
- `background_context`: Background context
- `conversation_history`: Conversation history

**Returns**: Observation string.

## InputParserAgent

**Module**: `src.agents.input_parser`

**Purpose**: Parses and improves user queries, detects research mode.

### Methods

#### `parse_query`

```python
async def parse_query(
    self,
    query: str
) -> ParsedQuery
```

Parses and improves a user query.

**Parameters**:
- `query`: Original query string

**Returns**: `ParsedQuery` with:
- `original_query`: Original query string
- `improved_query`: Refined query string
- `research_mode`: "iterative" or "deep"
- `key_entities`: List of key entities
- `research_questions`: List of research questions

## Factory Functions

All agents have factory functions in `src.agent_factory.agents`:

```python
def create_knowledge_gap_agent(model: Any | None = None) -> KnowledgeGapAgent
def create_tool_selector_agent(model: Any | None = None) -> ToolSelectorAgent
def create_writer_agent(model: Any | None = None) -> WriterAgent
def create_long_writer_agent(model: Any | None = None) -> LongWriterAgent
def create_proofreader_agent(model: Any | None = None) -> ProofreaderAgent
def create_thinking_agent(model: Any | None = None) -> ThinkingAgent
def create_input_parser_agent(model: Any | None = None) -> InputParserAgent
```

**Parameters**:
- `model`: Optional Pydantic AI model. If None, uses `get_model()` from settings.

**Returns**: Agent instance.

## See Also

- [Architecture - Agents](../architecture/agents.md) - Architecture overview
- [Models API](models.md) - Data models used by agents




















