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
- `relevance`: Relevance score (0.0-1.0)
- `metadata`: Additional metadata dictionary

## Citation

**Module**: `src.utils.models`

**Purpose**: Citation information for evidence.

<!--codeinclude-->
[Citation Model](../src/utils/models.py) start_line:12 end_line:30
<!--/codeinclude-->

**Fields**:
- `source`: Source name (e.g., "pubmed", "clinicaltrials", "europepmc", "web", "rag")
- `title`: Article/trial title
- `url`: Source URL
- `date`: Publication date (YYYY-MM-DD or "Unknown")
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
- `gap`: The knowledge gap being addressed (optional)
- `agent`: Name of agent to use
- `query`: The specific query for the agent
- `entity_website`: The website of the entity being researched, if known (optional)

## ReportDraft

**Module**: `src.utils.models`

**Purpose**: Draft structure for long-form reports.

<!--codeinclude-->
[ReportDraft Model](../src/utils/models.py) start_line:538 end_line:545
<!--/codeinclude-->

**Fields**:
- `sections`: List of report sections

## ReportSection

**Module**: `src.utils.models`

**Purpose**: Individual section in a report draft.

<!--codeinclude-->
[ReportDraftSection Model](../src/utils/models.py) start_line:529 end_line:535
<!--/codeinclude-->

**Fields**:
- `section_title`: The title of the section
- `section_content`: The content of the section

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
- `history`: List of iteration data

## IterationData

**Module**: `src.utils.models`

**Purpose**: Data for a single iteration.

<!--codeinclude-->
[IterationData Model](../src/utils/models.py) start_line:315 end_line:328
<!--/codeinclude-->

**Fields**:
- `gap`: The gap addressed in the iteration
- `tool_calls`: The tool calls made
- `findings`: The findings collected from tool calls
- `thought`: The thinking done to reflect on the success of the iteration and next steps

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
- `tokens_used`: Total tokens used
- `tokens_limit`: Token budget limit
- `time_elapsed_seconds`: Time elapsed in seconds
- `time_limit_seconds`: Time budget limit (default: 600.0 seconds / 10 minutes)
- `iterations`: Number of iterations completed
- `iterations_limit`: Maximum iterations (default: 10)
- `iteration_tokens`: Tokens used per iteration (iteration number -> token count)

## See Also

- [Architecture - Agents](../architecture/agents.md) - How models are used
- [Configuration](../configuration/index.md) - Model configuration
