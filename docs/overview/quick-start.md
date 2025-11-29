# Quick Start

Get started with DeepCritical in minutes.

## Installation

```bash
# Install uv if you haven't already
pip install uv

# Sync dependencies
uv sync
```

## Run the UI

```bash
# Start the Gradio app
uv run gradio run src/app.py
```

Open your browser to `http://localhost:7860`.

## Basic Usage

### 1. Authentication (Optional)

**HuggingFace OAuth Login**:
- Click the "Sign in with HuggingFace" button at the top of the app
- Your HuggingFace API token will be automatically used for AI inference
- No need to manually enter API keys when logged in

**Manual API Key (BYOK)**:
- Provide your own API key in the Settings accordion
- Supports HuggingFace, OpenAI, or Anthropic API keys
- Manual keys take priority over OAuth tokens

### 2. Start a Research Query

1. Enter your research question in the chat interface
2. Click "Submit" or press Enter
3. Watch the real-time progress as the system:
   - Generates observations
   - Identifies knowledge gaps
   - Searches multiple sources
   - Evaluates evidence
   - Synthesizes findings
4. Review the final research report

### 3. MCP Integration (Optional)

Connect DeepCritical to Claude Desktop:

1. Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "deepcritical": {
      "url": "http://localhost:7860/gradio_api/mcp/"
    }
  }
}
```

2. Restart Claude Desktop
3. Use DeepCritical tools directly from Claude Desktop

## Available Tools

- `search_pubmed`: Search peer-reviewed biomedical literature
- `search_clinical_trials`: Search ClinicalTrials.gov
- `search_biorxiv`: Search bioRxiv/medRxiv preprints
- `search_all`: Search all sources simultaneously
- `analyze_hypothesis`: Secure statistical analysis using Modal sandboxes

## Next Steps

- Read the [Installation Guide](../getting-started/installation.md) for detailed setup
- Learn about [Configuration](../configuration/index.md)
- Explore the [Architecture](../architecture/graph-orchestration.md)
- Check out [Examples](../getting-started/examples.md)

