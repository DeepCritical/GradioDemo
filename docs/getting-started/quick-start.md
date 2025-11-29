# Quick Start Guide

Get up and running with DeepCritical in minutes.

## Start the Application

```bash
uv run gradio run src/app.py
```

Open your browser to `http://localhost:7860`.

## First Research Query

1. **Enter a Research Question**

   Type your research question in the chat interface, for example:
   - "What are the latest treatments for Alzheimer's disease?"
   - "Review the evidence for metformin in cancer prevention"
   - "What clinical trials are investigating COVID-19 vaccines?"

2. **Submit the Query**

   Click "Submit" or press Enter. The system will:
   - Generate observations about your query
   - Identify knowledge gaps
   - Search multiple sources (PubMed, ClinicalTrials.gov, Europe PMC)
   - Evaluate evidence quality
   - Synthesize findings into a report

3. **Review Results**

   Watch the real-time progress in the chat interface:
   - Search operations and results
   - Evidence evaluation
   - Report generation
   - Final research report with citations

## Authentication

### HuggingFace OAuth (Recommended)

1. Click "Sign in with HuggingFace" at the top of the app
2. Authorize the application
3. Your HuggingFace API token will be automatically used
4. No need to manually enter API keys

### Manual API Key

1. Open the Settings accordion
2. Enter your API key:
   - OpenAI API key
   - Anthropic API key
   - HuggingFace API key
3. Click "Save Settings"
4. Manual keys take priority over OAuth tokens

## Understanding the Interface

### Chat Interface

- **Input**: Enter your research questions here
- **Messages**: View conversation history and research progress
- **Streaming**: Real-time updates as research progresses

### Status Indicators

- **Searching**: Active search operations
- **Evaluating**: Evidence quality assessment
- **Synthesizing**: Report generation
- **Complete**: Research finished

### Settings

- **API Keys**: Configure LLM providers
- **Research Mode**: Choose iterative or deep research
- **Budget Limits**: Set token, time, and iteration limits

## Example Queries

### Simple Query

```
What are the side effects of metformin?
```

### Complex Query

```
Review the evidence for using metformin as an anti-aging intervention, 
including clinical trials, mechanisms of action, and safety profile.
```

### Clinical Trial Query

```
What are the active clinical trials investigating Alzheimer's disease treatments?
```

## Next Steps

- Learn about [MCP Integration](mcp-integration.md) to use DeepCritical from Claude Desktop
- Explore [Examples](examples.md) for more use cases
- Read the [Configuration Guide](../configuration/index.md) for advanced settings
- Check out the [Architecture Documentation](../architecture/graph-orchestration.md) to understand how it works










