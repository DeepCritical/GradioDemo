# The DETERMINATOR

**Deep Research Agent for Medical Inquiry**

The DETERMINATOR is a deep research agent system that uses iterative search-and-judge loops to comprehensively investigate research questions. The system supports multiple orchestration patterns, graph-based execution, parallel research workflows, and long-running task management with real-time streaming.

**Important**: The DETERMINATOR functions as a medical peer junior researcher that assists with research by gathering and synthesizing evidence. It cannot answer medical questions or provide medical advice.

## Features

- **Multi-Source Search**: PubMed, ClinicalTrials.gov, Europe PMC (includes bioRxiv/medRxiv)
- **MCP Integration**: Use our tools from Claude Desktop or any MCP client
- **HuggingFace OAuth**: Sign in with your HuggingFace account to automatically use your API token
- **Modal Sandbox**: Secure execution of AI-generated statistical code
- **LlamaIndex RAG**: Semantic search and evidence synthesis
- **HuggingFace Inference**: Free tier support with automatic fallback
- **Strongly Typed Composable Graphs**: Graph-based orchestration with Pydantic AI
- **Specialized Research Teams of Agents**: Multi-agent coordination for complex research tasks

## Quick Start

```bash
# Install uv if you haven't already
pip install uv

# Sync dependencies
uv sync

# Start the Gradio app
uv run gradio run src/app.py
```

Open your browser to `http://localhost:7860`.

For detailed installation and setup instructions, see the [Getting Started Guide](getting-started/installation.md).

## Architecture

The DETERMINATOR uses a Vertical Slice Architecture:

1. **Search Slice**: Retrieving evidence from PubMed, ClinicalTrials.gov, and Europe PMC
2. **Judge Slice**: Evaluating evidence quality using LLMs
3. **Orchestrator Slice**: Managing the research loop and UI

The system supports three main research patterns:

- **Iterative Research**: Single research loop with search-judge-synthesize cycles
- **Deep Research**: Multi-section parallel research with planning and synthesis
- **Research Team**: Multi-agent coordination using Magentic framework

Learn more about the [Architecture](overview/architecture.md).

## Documentation

- [Overview](overview/architecture.md) - System architecture and design
- [Getting Started](getting-started/installation.md) - Installation and setup
- [Configuration](configuration/index.md) - Configuration guide
- [API Reference](api/agents.md) - API documentation
- [Contributing](contributing.md) - Development guidelines

## Links

- [GitHub Repository](https://github.com/DeepCritical/GradioDemo)
- [HuggingFace Space](https://huggingface.co/spaces/DataQuests/DeepCritical)

