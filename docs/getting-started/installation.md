# Installation

This guide will help you install and set up DeepCritical on your system.

## Prerequisites

- Python 3.11 or higher
- `uv` package manager (recommended) or `pip`
- At least one LLM API key (OpenAI, Anthropic, or HuggingFace)

## Installation Steps

### 1. Install uv (Recommended)

`uv` is a fast Python package installer and resolver. Install it with:

```bash
pip install uv
```

### 2. Clone the Repository

```bash
git clone https://github.com/DeepCritical/GradioDemo.git
cd GradioDemo
```

### 3. Install Dependencies

Using `uv` (recommended):

```bash
uv sync
```

Using `pip`:

```bash
pip install -e .
```

### 4. Install Optional Dependencies

For embeddings support (local sentence-transformers):

```bash
uv sync --extra embeddings
```

For Modal sandbox execution:

```bash
uv sync --extra modal
```

For Magentic orchestration:

```bash
uv sync --extra magentic
```

Install all extras:

```bash
uv sync --all-extras
```

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Required: At least one LLM provider
LLM_PROVIDER=openai  # or "anthropic" or "huggingface"
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Other services
NCBI_API_KEY=your_ncbi_api_key_here  # For higher PubMed rate limits
MODAL_TOKEN_ID=your_modal_token_id
MODAL_TOKEN_SECRET=your_modal_token_secret
```

See the [Configuration Guide](../configuration/index.md) for all available options.

### 6. Verify Installation

Run the application:

```bash
uv run gradio run src/app.py
```

Open your browser to `http://localhost:7860` to verify the installation.

## Development Setup

For development, install dev dependencies:

```bash
uv sync --all-extras --dev
```

Install pre-commit hooks:

```bash
uv run pre-commit install
```

## Troubleshooting

### Common Issues

**Import Errors**:
- Ensure you've installed all required dependencies
- Check that Python 3.11+ is being used

**API Key Errors**:
- Verify your `.env` file is in the project root
- Check that API keys are correctly formatted
- Ensure at least one LLM provider is configured

**Module Not Found**:
- Run `uv sync` or `pip install -e .` again
- Check that you're in the correct virtual environment

**Port Already in Use**:
- Change the port in `src/app.py` or use environment variable
- Kill the process using port 7860

## Next Steps

- Read the [Quick Start Guide](quick-start.md)
- Learn about [MCP Integration](mcp-integration.md)
- Explore [Examples](examples.md)








