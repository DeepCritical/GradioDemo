# Models API Reference

This page documents the Pydantic models used throughout DeepCritical.

## Evidence

**Module**: `src.utils.models`

**Purpose**: Represents evidence from search results.

<!--codeinclude-->
[Evidence Model](../src/utils/models.py) start_line:33 end_line:44
<!--/codeinclude-->

**Fields**:
- `citation`: Citation information (title, URL, date, authors)
- `content`: Evidence text content
- `relevance_score`: Relevance score (0.0-1.0)
- `metadata`: Additional metadata dictionary

## Citation

**Module**: `src.utils.models`

**Purpose**: Citation information for evidence.

<!--codeinclude-->
[Citation Model](../src/utils/models.py) start_line:12 end_line:30
<!--/codeinclude-->

**Fields**:
- `title`: Article/trial title
- `url`: Source URL
- `date`: Publication date (optional)
- `authors`: List of authors (optional)

## KnowledgeGapOutput

**Module**: `src.utils.models`

**Purpose**: Output from knowledge gap evaluation.

<!--codeinclude-->
[KnowledgeGapOutput Model](../src/utils/models.py) start_line:494 end_line:504
<!--/codeinclude-->

**Fields**:
- `research_complete`: Boolean indicating if research is complete
- `outstanding_gaps`: List of remaining knowledge gaps

## AgentSelectionPlan

**Module**: `src.utils.models`

**Purpose**: Plan for tool/agent selection.

<!--codeinclude-->
[AgentSelectionPlan Model](../src/utils/models.py) start_line:521 end_line:526
<!--/codeinclude-->

**Fields**:
- `tasks`: List of agent tasks to execute

## AgentTask

**Module**: `src.utils.models`

**Purpose**: Individual agent task.

<!--codeinclude-->
[AgentTask Model](../src/utils/models.py) start_line:507 end_line:518
<!--/codeinclude-->

**Fields**:
- `agent_name`: Name of agent to use
- `query`: Task query
- `context`: Additional context dictionary

## ReportDraft

**Module**: `src.utils.models`

**Purpose**: Draft structure for long-form reports.

<!--codeinclude-->
[ReportDraft Model](../src/utils/models.py) start_line:538 end_line:545
<!--/codeinclude-->

**Fields**:
- `title`: Report title
- `sections`: List of report sections
- `references`: List of citations

## ReportSection

**Module**: `src.utils.models`

**Purpose**: Individual section in a report draft.

<!--codeinclude-->
[ReportDraftSection Model](../src/utils/models.py) start_line:529 end_line:535
<!--/codeinclude-->

**Fields**:
- `title`: Section title
- `content`: Section content
- `order`: Section order number

## ParsedQuery

**Module**: `src.utils.models`

**Purpose**: Parsed and improved query.

<!--codeinclude-->
[ParsedQuery Model](../src/utils/models.py) start_line:557 end_line:572
<!--/codeinclude-->

**Fields**:
- `original_query`: Original query string
- `improved_query`: Refined query string
- `research_mode`: Research mode ("iterative" or "deep")
- `key_entities`: List of key entities
- `research_questions`: List of research questions

## Conversation

**Module**: `src.utils.models`

**Purpose**: Conversation history with iterations.

<!--codeinclude-->
[Conversation Model](../src/utils/models.py) start_line:331 end_line:337
<!--/codeinclude-->

**Fields**:
- `iterations`: List of iteration data

## IterationData

**Module**: `src.utils.models`

**Purpose**: Data for a single iteration.

<!--codeinclude-->
[IterationData Model](../src/utils/models.py) start_line:315 end_line:328
<!--/codeinclude-->

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

<!--codeinclude-->
[AgentEvent Model](../src/utils/models.py) start_line:104 end_line:125
<!--/codeinclude-->

**Fields**:
- `type`: Event type (e.g., "started", "search_complete", "complete")
- `iteration`: Iteration number (optional)
- `data`: Event data dictionary

## BudgetStatus

**Module**: `src.utils.models`

**Purpose**: Current budget status.

<!--codeinclude-->
[BudgetStatus Model](../src/middleware/budget_tracker.py) start_line:15 end_line:25
<!--/codeinclude-->

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
