# Agents API Reference

This page documents the API for DeepCritical agents.

## KnowledgeGapAgent

**Module**: `src.agents.knowledge_gap`

**Purpose**: Evaluates research state and identifies knowledge gaps.

### Methods

#### `evaluate`

<!--codeinclude-->
[KnowledgeGapAgent.evaluate](../src/agents/knowledge_gap.py) start_line:66 end_line:74
<!--/codeinclude-->

Evaluates research completeness and identifies outstanding knowledge gaps.

**Parameters**:
- `query`: Research query string
- `background_context`: Background context for the query (default: "")
- `conversation_history`: History of actions, findings, and thoughts as string (default: "")
- `iteration`: Current iteration number (default: 0)
- `time_elapsed_minutes`: Elapsed time in minutes (default: 0.0)
- `max_time_minutes`: Maximum time limit in minutes (default: 10)

**Returns**: `KnowledgeGapOutput` with:
- `research_complete`: Boolean indicating if research is complete
- `outstanding_gaps`: List of remaining knowledge gaps

## ToolSelectorAgent

**Module**: `src.agents.tool_selector`

**Purpose**: Selects appropriate tools for addressing knowledge gaps.

### Methods

#### `select_tools`

<!--codeinclude-->
[ToolSelectorAgent.select_tools](../src/agents/tool_selector.py) start_line:78 end_line:84
<!--/codeinclude-->

Selects tools for addressing a knowledge gap.

**Parameters**:
- `gap`: The knowledge gap to address
- `query`: Research query string
- `background_context`: Optional background context (default: "")
- `conversation_history`: History of actions, findings, and thoughts as string (default: "")

**Returns**: `AgentSelectionPlan` with list of `AgentTask` objects.

## WriterAgent

**Module**: `src.agents.writer`

**Purpose**: Generates final reports from research findings.

### Methods

#### `write_report`

<!--codeinclude-->
[WriterAgent.write_report](../src/agents/writer.py) start_line:67 end_line:73
<!--/codeinclude-->

Generates a markdown report from research findings.

**Parameters**:
- `query`: Research query string
- `findings`: Research findings to include in report
- `output_length`: Optional description of desired output length (default: "")
- `output_instructions`: Optional additional instructions for report generation (default: "")

**Returns**: Markdown string with numbered citations.

## LongWriterAgent

**Module**: `src.agents.long_writer`

**Purpose**: Long-form report generation with section-by-section writing.

### Methods

#### `write_next_section`

<!--codeinclude-->
[LongWriterAgent.write_next_section](../src/agents/long_writer.py) start_line:94 end_line:100
<!--/codeinclude-->

Writes the next section of a long-form report.

**Parameters**:
- `original_query`: The original research query
- `report_draft`: Current report draft as string (all sections written so far)
- `next_section_title`: Title of the section to write
- `next_section_draft`: Draft content for the next section

**Returns**: `LongWriterOutput` with formatted section and references.

#### `write_report`

<!--codeinclude-->
[LongWriterAgent.write_report](../src/agents/long_writer.py) start_line:263 end_line:268
<!--/codeinclude-->

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

<!--codeinclude-->
[ProofreaderAgent.proofread](../src/agents/proofreader.py) start_line:72 end_line:76
<!--/codeinclude-->

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

<!--codeinclude-->
[ThinkingAgent.generate_observations](../src/agents/thinking.py) start_line:70 end_line:76
<!--/codeinclude-->

Generates observations from conversation history.

**Parameters**:
- `query`: Research query string
- `background_context`: Optional background context (default: "")
- `conversation_history`: History of actions, findings, and thoughts as string (default: "")
- `iteration`: Current iteration number (default: 1)

**Returns**: Observation string.

## InputParserAgent

**Module**: `src.agents.input_parser`

**Purpose**: Parses and improves user queries, detects research mode.

### Methods

#### `parse`

<!--codeinclude-->
[InputParserAgent.parse](../src/agents/input_parser.py) start_line:82 end_line:82
<!--/codeinclude-->

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

<!--codeinclude-->
[Factory Functions](../src/agent_factory/agents.py) start_line:30 end_line:50
<!--/codeinclude-->

**Parameters**:
- `model`: Optional Pydantic AI model. If None, uses `get_model()` from settings.
- `oauth_token`: Optional OAuth token from HuggingFace login (takes priority over env vars)

**Returns**: Agent instance.

## See Also

- [Architecture - Agents](../architecture/agents.md) - Architecture overview
- [Models API](models.md) - Data models used by agents

