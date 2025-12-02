# Quick Start

Get started with DeepCritical in minutes.

## Installation

```bash
# Install uv if you haven't already (recommended: standalone installer)
# Unix/macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell):
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Alternative: pipx install uv
# Or: pip install uv

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

### 1. Authentication (REQUIRED)

**Authentication is mandatory** - you must authenticate before using the application. The app will display an error message if you try to use it without authentication.

**HuggingFace OAuth Login** (Recommended):
- Click the "Sign in with HuggingFace" button at the top of the app
- Your HuggingFace API token will be automatically used for AI inference
- No need to manually enter API keys when logged in

**Manual API Key** (Alternative):
- Set environment variable `HF_TOKEN` or `HUGGINGFACE_API_KEY` before starting the app
- The app will automatically use these tokens if OAuth login is not available
- Supports HuggingFace API keys only (OpenAI/Anthropic keys are not used in the current implementation)

### 2. Start a Research Query

1. Enter your research question in the chat interface
   - **Text Input**: Type your question directly
   - **Image Input**: Click the 📷 icon to upload images (OCR will extract text)
   - **Audio Input**: Click the 🎤 icon to record or upload audio (STT will transcribe to text)
2. Click "Submit" or press Enter
3. Watch the real-time progress as the system:
   - Generates observations
   - Identifies knowledge gaps
   - Searches multiple sources
   - Evaluates evidence
   - Synthesizes findings
4. Review the final research report
   - **Audio Output**: If enabled, the final response will include audio synthesis (TTS)

**Multimodal Features**:
- Configure image/audio input and output in the sidebar settings
- Image OCR and audio STT/TTS can be enabled/disabled independently
- TTS voice and speed can be customized in the Audio Output settings

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
- `search_neo4j`: Search Neo4j knowledge graph for papers and disease relationships
- `search_all`: Search all sources simultaneously
- `analyze_hypothesis`: Secure statistical analysis using Modal sandboxes

**Note**: The application automatically uses all available search tools (Neo4j, PubMed, ClinicalTrials.gov, Europe PMC, Web search, RAG) based on query analysis. Neo4j knowledge graph search is included by default for biomedical queries.

## Next Steps

- Read the [Installation Guide](../getting-started/installation.md) for detailed setup
- Learn about [Configuration](../configuration/index.md)
- Explore the [Architecture](../architecture/graph_orchestration.md)
- Check out [Examples](../getting-started/examples.md)

