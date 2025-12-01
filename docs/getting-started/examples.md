# Examples

This page provides examples of using DeepCritical for various research tasks.

## Basic Research Query

### Example 1: Drug Information

**Query**:
```
What are the latest treatments for Alzheimer's disease?
```

**What DeepCritical Does**:
1. Searches PubMed for recent papers
2. Searches ClinicalTrials.gov for active trials
3. Evaluates evidence quality
4. Synthesizes findings into a comprehensive report

### Example 2: Clinical Trial Search

**Query**:
```
What clinical trials are investigating metformin for cancer prevention?
```

**What DeepCritical Does**:
1. Searches ClinicalTrials.gov for relevant trials
2. Searches PubMed for supporting literature
3. Provides trial details and status
4. Summarizes findings

## Advanced Research Queries

### Example 3: Comprehensive Review

**Query**:
```
Review the evidence for using metformin as an anti-aging intervention, 
including clinical trials, mechanisms of action, and safety profile.
```

**What DeepCritical Does**:
1. Uses deep research mode (multi-section)
2. Searches multiple sources in parallel
3. Generates sections on:
   - Clinical trials
   - Mechanisms of action
   - Safety profile
4. Synthesizes comprehensive report

### Example 4: Hypothesis Testing

**Query**:
```
Test the hypothesis that regular exercise reduces Alzheimer's disease risk.
```

**What DeepCritical Does**:
1. Generates testable hypotheses
2. Searches for supporting/contradicting evidence
3. Performs statistical analysis (if Modal configured)
4. Provides verdict: SUPPORTED, REFUTED, or INCONCLUSIVE

## MCP Tool Examples

### Using search_pubmed

```
Search PubMed for "CRISPR gene editing cancer therapy"
```

### Using search_clinical_trials

```
Find active clinical trials for "diabetes type 2 treatment"
```

### Using search_all

```
Search all sources for "COVID-19 vaccine side effects"
```

### Using analyze_hypothesis

```
Analyze whether vitamin D supplementation reduces COVID-19 severity
```

## Code Examples

### Python API Usage

```python
from src.orchestrator_factory import create_orchestrator
from src.tools.search_handler import SearchHandler
from src.agent_factory.judges import create_judge_handler

# Create orchestrator
search_handler = SearchHandler()
judge_handler = create_judge_handler()
```

<!--codeinclude-->
[Create Orchestrator](../src/orchestrator_factory.py) start_line:44 end_line:66
<!--/codeinclude-->

```python
# Run research query
query = "What are the latest treatments for Alzheimer's disease?"
async for event in orchestrator.run(query):
    print(f"Event: {event.type} - {event.data}")
```

### Gradio UI Integration

```python
import gradio as gr
from src.app import create_research_interface

# Create interface
interface = create_research_interface()

# Launch
interface.launch(server_name="0.0.0.0", server_port=7860)
```

## Research Patterns

### Iterative Research

Single-loop research with search-judge-synthesize cycles:

```python
from src.orchestrator.research_flow import IterativeResearchFlow
```

<!--codeinclude-->
[IterativeResearchFlow Initialization](../src/orchestrator/research_flow.py) start_line:56 end_line:77
<!--/codeinclude-->

```python
async for event in flow.run(query):
    # Handle events
    pass
```

### Deep Research

Multi-section parallel research:

```python
from src.orchestrator.research_flow import DeepResearchFlow
```

<!--codeinclude-->
[DeepResearchFlow Initialization](../src/orchestrator/research_flow.py) start_line:674 end_line:697
<!--/codeinclude-->

```python
async for event in flow.run(query):
    # Handle events
    pass
```

## Configuration Examples

### Basic Configuration

```bash
# .env file
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
MAX_ITERATIONS=10
```

### Advanced Configuration

```bash
# .env file
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
EMBEDDING_PROVIDER=local
WEB_SEARCH_PROVIDER=duckduckgo
MAX_ITERATIONS=20
DEFAULT_TOKEN_LIMIT=200000
USE_GRAPH_EXECUTION=true
```

## Next Steps

- Read the [Configuration Guide](../configuration/index.md) for all options
- Explore the [Architecture Documentation](../architecture/graph-orchestration.md)
- Check out the [API Reference](../api/agents.md) for programmatic usage














