# Contributing to The DETERMINATOR

Thank you for your interest in contributing to The DETERMINATOR! This guide will help you get started.

> **Note on Project Names**: "The DETERMINATOR" is the product name, "DeepCritical" is the organization/project name, and "determinator" is the Python package name.

## Git Workflow

- `main`: Production-ready (GitHub)
- `dev`: Development integration (GitHub)
- Use feature branches: `yourname-dev`
- **NEVER** push directly to `main` or `dev` on HuggingFace
- GitHub is source of truth; HuggingFace is for deployment

## Repository Information

- **GitHub Repository**: [`DeepCritical/GradioDemo`](https://github.com/DeepCritical/GradioDemo) (source of truth, PRs, code review)
- **HuggingFace Space**: [`DataQuests/DeepCritical`](https://huggingface.co/spaces/DataQuests/DeepCritical) (deployment/demo)
- **Package Name**: `determinator` (Python package name in `pyproject.toml`)

### Dual Repository Setup

This project uses a dual repository setup:

- **GitHub (`DeepCritical/GradioDemo`)**: Source of truth for code, PRs, and code review
- **HuggingFace (`DataQuests/DeepCritical`)**: Deployment target for the Gradio demo

#### Remote Configuration

When cloning, set up remotes as follows:

```bash
# Clone from GitHub
git clone https://github.com/DeepCritical/GradioDemo.git
cd GradioDemo

# Add HuggingFace remote (optional, for deployment)
git remote add huggingface-upstream https://huggingface.co/spaces/DataQuests/DeepCritical
```

**Important**: Never push directly to `main` or `dev` on HuggingFace. Always work through GitHub PRs. GitHub is the source of truth; HuggingFace is for deployment/demo only.

## Package Manager

This project uses [`uv`](https://github.com/astral-sh/uv) as the package manager. All commands should be prefixed with `uv run` to ensure they run in the correct environment.

### Installation

```bash
# Install uv if you haven't already (recommended: standalone installer)
# Unix/macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell):
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Alternative: pipx install uv
# Or: pip install uv

# Sync all dependencies including dev extras
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

## Development Commands

```bash
# Installation
uv sync --all-extras              # Install all dependencies including dev
uv run pre-commit install          # Install pre-commit hooks

# Code Quality Checks (run all before committing)
uv run ruff check src tests       # Lint with ruff
uv run ruff format src tests      # Format with ruff
uv run mypy src                   # Type checking
uv run pytest --cov=src --cov-report=term-missing tests/unit/ -v -m "not openai" -p no:logfire  # Tests with coverage

# Testing Commands
uv run pytest tests/unit/ -v -m "not openai" -p no:logfire              # Run unit tests (excludes OpenAI tests)
uv run pytest tests/ -v -m "huggingface" -p no:logfire                 # Run HuggingFace tests
uv run pytest tests/ -v -p no:logfire                                  # Run all tests
uv run pytest --cov=src --cov-report=term-missing tests/unit/ -v -m "not openai" -p no:logfire  # Tests with terminal coverage
uv run pytest --cov=src --cov-report=html -p no:logfire                # Generate HTML coverage report (opens htmlcov/index.html)

# Documentation Commands
uv run mkdocs build                # Build documentation
uv run mkdocs serve                # Serve documentation locally (http://127.0.0.1:8000)
```

### Test Markers

The project uses pytest markers to categorize tests. See [Testing Guidelines](testing.md) for details:

- `unit`: Unit tests (mocked, fast)
- `integration`: Integration tests (real APIs)
- `slow`: Slow tests
- `openai`: Tests requiring OpenAI API key
- `huggingface`: Tests requiring HuggingFace API key
- `embedding_provider`: Tests requiring API-based embedding providers
- `local_embeddings`: Tests using local embeddings

**Note**: The `-p no:logfire` flag disables the logfire plugin to avoid conflicts during testing.

## Getting Started

1. **Fork the repository** on GitHub: [`DeepCritical/GradioDemo`](https://github.com/DeepCritical/GradioDemo)

2. **Clone your fork**:

   ```bash
   git clone https://github.com/yourusername/GradioDemo.git
   cd GradioDemo
   ```

3. **Install dependencies**:

   ```bash
   uv sync --all-extras
   uv run pre-commit install
   ```

4. **Create a feature branch**:

   ```bash
   git checkout -b yourname-feature-name
   ```

5. **Make your changes** following the guidelines below

6. **Run checks**:

   ```bash
   uv run ruff check src tests
   uv run mypy src
   uv run pytest --cov=src --cov-report=term-missing tests/unit/ -v -m "not openai" -p no:logfire
   ```

7. **Commit and push**:

   ```bash
   git commit -m "Description of changes"
   git push origin yourname-feature-name
   ```

8. **Create a pull request** on GitHub

## Development Guidelines

### Code Style

- Follow [Code Style Guidelines](code-style.md)
- All code must pass `mypy --strict`
- Use `ruff` for linting and formatting
- Line length: 100 characters

### Error Handling

- Follow [Error Handling Guidelines](error-handling.md)
- Always chain exceptions: `raise SearchError(...) from e`
- Use structured logging with `structlog`
- Never silently swallow exceptions

### Testing

- Follow [Testing Guidelines](testing.md)
- Write tests before implementation (TDD)
- Aim for >80% coverage on critical paths
- Use markers: `unit`, `integration`, `slow`

### Implementation Patterns

- Follow [Implementation Patterns](implementation-patterns.md)
- Use factory functions for agent/tool creation
- Implement protocols for extensibility
- Use singleton pattern with `@lru_cache(maxsize=1)`

### Prompt Engineering

- Follow [Prompt Engineering Guidelines](prompt-engineering.md)
- Always validate citations
- Use diverse evidence selection
- Never trust LLM-generated citations without validation

### Code Quality

- Follow [Code Quality Guidelines](code-quality.md)
- Google-style docstrings for all public functions
- Explain WHY, not WHAT in comments
- Mark critical sections: `# CRITICAL: ...`

## MCP Integration

### MCP Tools

- Functions in `src/mcp_tools.py` for Claude Desktop
- Full type hints required
- Google-style docstrings with Args/Returns sections
- Formatted string returns (markdown)

### Gradio MCP Server

- Enable with `mcp_server=True` in `demo.launch()`
- Endpoint: `/gradio_api/mcp/`
- Use `ssr_mode=False` to fix hydration issues in HF Spaces

## Common Pitfalls

1. **Blocking the event loop**: Never use sync I/O in async functions
2. **Missing type hints**: All functions must have complete type annotations
3. **Hallucinated citations**: Always validate references
4. **Global mutable state**: Use ContextVar or pass via parameters
5. **Import errors**: Lazy-load optional dependencies (magentic, modal, embeddings)
6. **Rate limiting**: Always implement for external APIs
7. **Error chaining**: Always use `from e` when raising exceptions

## Key Principles

1. **Type Safety First**: All code must pass `mypy --strict`
2. **Async Everything**: All I/O must be async
3. **Test-Driven**: Write tests before implementation
4. **No Hallucinations**: Validate all citations
5. **Graceful Degradation**: Support free tier (HF Inference) when no API keys
6. **Lazy Loading**: Don't require optional dependencies at import time
7. **Structured Logging**: Use structlog, never print()
8. **Error Chaining**: Always preserve exception context

## Pull Request Process

1. Ensure all checks pass: `uv run ruff check src tests && uv run mypy src && uv run pytest --cov=src --cov-report=term-missing tests/unit/ -v -m "not openai" -p no:logfire`
2. Update documentation if needed
3. Add tests for new features
4. Update CHANGELOG if applicable
5. Request review from maintainers
6. Address review feedback
7. Wait for approval before merging

## Project Structure

- `src/`: Main source code
- `tests/`: Test files (`unit/` and `integration/`)
- `docs/`: Documentation source files (MkDocs)
- `examples/`: Example usage scripts
- `pyproject.toml`: Project configuration and dependencies
- `.pre-commit-config.yaml`: Pre-commit hook configuration

## Questions?

- Open an issue on [GitHub](https://github.com/DeepCritical/GradioDemo)
- Check existing [documentation](https://deepcritical.github.io/GradioDemo/)
- Review code examples in the codebase

Thank you for contributing to The DETERMINATOR!
