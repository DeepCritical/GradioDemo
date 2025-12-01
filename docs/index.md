# The DETERMINATOR

**Generalist Deep Research Agent - Stops at Nothing Until Finding Precise Answers**

The DETERMINATOR is a powerful generalist deep research agent system that uses iterative search-and-judge loops to comprehensively investigate any research question. It stops at nothing until finding precise answers, only stopping at configured limits (budget, time, iterations).

**Key Features**:
- **Generalist**: Handles queries from any domain (medical, technical, business, scientific, etc.)
- **Automatic Source Selection**: Automatically determines if medical knowledge sources (PubMed, ClinicalTrials.gov) are needed
- **Multi-Source Search**: Web search, PubMed, ClinicalTrials.gov, Europe PMC, RAG
- **Iterative Refinement**: Continues searching and refining until precise answers are found
- **Evidence Synthesis**: Comprehensive reports with proper citations

**Important**: The DETERMINATOR is a research tool that synthesizes evidence. It cannot provide medical advice or answer medical questions directly.

## Features

- **Generalist Research**: Handles any research question from any domain
- **Automatic Medical Detection**: Automatically determines if medical knowledge sources are needed
- **Multi-Source Search**: Web search, PubMed, ClinicalTrials.gov, Europe PMC (includes bioRxiv/medRxiv), RAG
- **Iterative Until Precise**: Stops at nothing until finding precise answers (only stops at configured limits)
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

1. **Search Slice**: Retrieving evidence from multiple sources (web, PubMed, ClinicalTrials.gov, Europe PMC, RAG) based on query analysis
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
- [Contributing](contributing/index.md) - Development guidelines

## Links

- [GitHub Repository](https://github.com/DeepCritical/GradioDemo)
- [HuggingFace Space](https://huggingface.co/spaces/DataQuests/DeepCritical)

