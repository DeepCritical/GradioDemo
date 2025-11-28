---
title: DeepCritical
emoji: 🧬
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: "6.0.1"
python_version: "3.11"
app_file: src/app.py
pinned: false
license: mit
tags:
  - mcp-in-action-track-enterprise
  - mcp-hackathon
  - drug-repurposing
  - biomedical-ai
  - pydantic-ai
  - llamaindex
  - modal
---

# DeepCritical

## Intro

## Features

- **Multi-Source Search**: PubMed, ClinicalTrials.gov, bioRxiv/medRxiv
- **MCP Integration**: Use our tools from Claude Desktop or any MCP client
- **Modal Sandbox**: Secure execution of AI-generated statistical code
- **LlamaIndex RAG**: Semantic search and evidence synthesis
- **HuggingfaceInference**: 
- **HuggingfaceMCP Custom Config To Use Community Tools**:
- **Strongly Typed Composable Graphs**:
- **Specialized Research Teams of Agents**: 

## Quick Start

### 1. Environment Setup

```bash
# Install uv if you haven't already
pip install uv

# Sync dependencies
uv sync
```

### 2. Run the UI

```bash
# Start the Gradio app
uv run gradio run src/app.py
```

Open your browser to `http://localhost:7860`.

### 3. Connect via MCP

This application exposes a Model Context Protocol (MCP) server, allowing you to use its search tools directly from Claude Desktop or other MCP clients.

**MCP Server URL**: `http://localhost:7860/gradio_api/mcp/`

**Claude Desktop Configuration**:
Add this to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "deepcritical": {
      "url": "http://localhost:7860/gradio_api/mcp/"
    }
  }
}
```

**Available Tools**:
- `search_pubmed`: Search peer-reviewed biomedical literature.
- `search_clinical_trials`: Search ClinicalTrials.gov.
- `search_biorxiv`: Search bioRxiv/medRxiv preprints.
- `search_all`: Search all sources simultaneously.
- `analyze_hypothesis`: Secure statistical analysis using Modal sandboxes.


## Deep Research Flows 

- iterativeResearch
- deepResearch
- researchTeam

### Iterative Research

sequenceDiagram
    participant IterativeFlow
    participant ThinkingAgent
    participant KnowledgeGapAgent
    participant ToolSelector
    participant ToolExecutor
    participant JudgeHandler
    participant WriterAgent

    IterativeFlow->>IterativeFlow: run(query)
    
    loop Until complete or max_iterations
        IterativeFlow->>ThinkingAgent: generate_observations()
        ThinkingAgent-->>IterativeFlow: observations
        
        IterativeFlow->>KnowledgeGapAgent: evaluate_gaps()
        KnowledgeGapAgent-->>IterativeFlow: KnowledgeGapOutput
        
        alt Research complete
            IterativeFlow->>WriterAgent: create_final_report()
            WriterAgent-->>IterativeFlow: final_report
        else Gaps remain
            IterativeFlow->>ToolSelector: select_agents(gap)
            ToolSelector-->>IterativeFlow: AgentSelectionPlan
            
            IterativeFlow->>ToolExecutor: execute_tool_tasks()
            ToolExecutor-->>IterativeFlow: ToolAgentOutput[]
            
            IterativeFlow->>JudgeHandler: assess_evidence()
            JudgeHandler-->>IterativeFlow: should_continue
        end
    end


### Deep Research

sequenceDiagram
    actor User
    participant GraphOrchestrator
    participant InputParser
    participant GraphBuilder
    participant GraphExecutor
    participant Agent
    participant BudgetTracker
    participant WorkflowState

    User->>GraphOrchestrator: run(query)
    GraphOrchestrator->>InputParser: detect_research_mode(query)
    InputParser-->>GraphOrchestrator: mode (iterative/deep)
    GraphOrchestrator->>GraphBuilder: build_graph(mode)
    GraphBuilder-->>GraphOrchestrator: ResearchGraph
    GraphOrchestrator->>WorkflowState: init_workflow_state()
    GraphOrchestrator->>BudgetTracker: create_budget()
    GraphOrchestrator->>GraphExecutor: _execute_graph(graph)
    
    loop For each node in graph
        GraphExecutor->>Agent: execute_node(agent_node)
        Agent->>Agent: process_input
        Agent-->>GraphExecutor: result
        GraphExecutor->>WorkflowState: update_state(result)
        GraphExecutor->>BudgetTracker: add_tokens(used)
        GraphExecutor->>BudgetTracker: check_budget()
        alt Budget exceeded
            GraphExecutor->>GraphOrchestrator: emit(error_event)
        else Continue
            GraphExecutor->>GraphOrchestrator: emit(progress_event)
        end
    end
    
    GraphOrchestrator->>User: AsyncGenerator[AgentEvent]

### Research Team
Critical Deep Research Agent

## Development

### Run Tests

```bash
uv run pytest
```

### Run Checks

```bash
make check
```

## Architecture

DeepCritical uses a Vertical Slice Architecture:

1.  **Search Slice**: Retrieving evidence from PubMed, ClinicalTrials.gov, and bioRxiv.
2.  **Judge Slice**: Evaluating evidence quality using LLMs.
3.  **Orchestrator Slice**: Managing the research loop and UI.

Built with:
- **PydanticAI**: For robust agent interactions.
- **Gradio**: For the streaming user interface.
- **PubMed, ClinicalTrials.gov, bioRxiv**: For biomedical data.
- **MCP**: For universal tool access.
- **Modal**: For secure code execution.

## Team

- The-Obstacle-Is-The-Way
- MarioAderman
- Josephrp

## Links

- [GitHub Repository](https://github.com/The-Obstacle-Is-The-Way/DeepCritical-1)