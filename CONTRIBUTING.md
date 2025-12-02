# Contributing to The DETERMINATOR

Thank you for your interest in contributing to The DETERMINATOR! This guide will help you get started.

## Table of Contents

- [Git Workflow](#git-workflow)
- [Getting Started](#getting-started)
- [Development Commands](#development-commands)
- [MCP Integration](#mcp-integration)
- [Common Pitfalls](#common-pitfalls)
- [Key Principles](#key-principles)
- [Pull Request Process](#pull-request-process)

> **Note**: Additional sections (Code Style, Error Handling, Testing, Implementation Patterns, Code Quality, and Prompt Engineering) are available as separate pages in the [documentation](https://deepcritical.github.io/GradioDemo/contributing/).  
> **Note on Project Names**: "The DETERMINATOR" is the product name, "DeepCritical" is the organization/project name, and "determinator" is the Python package name.

## Repository Information

- **GitHub Repository**: [`DeepCritical/GradioDemo`](https://github.com/DeepCritical/GradioDemo) (source of truth, PRs, code review)
- **HuggingFace Space**: [`DataQuests/DeepCritical`](https://huggingface.co/spaces/DataQuests/DeepCritical) (deployment/demo)
- **Package Name**: `determinator` (Python package name in `pyproject.toml`)

## Git Workflow

- `main`: Production-ready (GitHub)
- `dev`: Development integration (GitHub)
- Use feature branches: `yourname-dev`
- **NEVER** push directly to `main` or `dev` on HuggingFace
- GitHub is source of truth; HuggingFace is for deployment

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

The project uses pytest markers to categorize tests. See [Testing Guidelines](docs/contributing/testing.md) for details:

- `unit`: Unit tests (mocked, fast)
- `integration`: Integration tests (real APIs)
- `slow`: Slow tests
- `openai`: Tests requiring OpenAI API key
- `huggingface`: Tests requiring HuggingFace API key
- `embedding_provider`: Tests requiring API-based embedding providers
- `local_embeddings`: Tests using local embeddings

**Note**: The `-p no:logfire` flag disables the logfire plugin to avoid conflicts during testing.

## Code Style & Conventions

### Type Safety

- **ALWAYS** use type hints for all function parameters and return types
- Use `mypy --strict` compliance (no `Any` unless absolutely necessary)
- Use `TYPE_CHECKING` imports for circular dependencies:

<!--codeinclude-->
[TYPE_CHECKING Import Pattern](../src/utils/citation_validator.py) start_line:8 end_line:11
<!--/codeinclude-->

### Pydantic Models

- All data exchange uses Pydantic models (`src/utils/models.py`)
- Models are frozen (`model_config = {"frozen": True}`) for immutability
- Use `Field()` with descriptions for all model fields
- Validate with `ge=`, `le=`, `min_length=`, `max_length=` constraints

### Async Patterns

- **ALL** I/O operations must be async (`async def`, `await`)
- Use `asyncio.gather()` for parallel operations
- CPU-bound work (embeddings, parsing) must use `run_in_executor()`:

```python
loop = asyncio.get_running_loop()
result = await loop.run_in_executor(None, cpu_bound_function, args)
```

- Never block the event loop with synchronous I/O

### Linting

- Ruff with 100-char line length
- Ignore rules documented in `pyproject.toml`:
  - `PLR0913`: Too many arguments (agents need many params)
  - `PLR0912`: Too many branches (complex orchestrator logic)
  - `PLR0911`: Too many return statements (complex agent logic)
  - `PLR2004`: Magic values (statistical constants)
  - `PLW0603`: Global statement (singleton pattern)
  - `PLC0415`: Lazy imports for optional dependencies

### Pre-commit

- Pre-commit hooks run automatically on commit
- Must pass: lint + typecheck + test-cov
- Install hooks with: `uv run pre-commit install`
- Note: `uv sync --all-extras` installs the pre-commit package, but you must run `uv run pre-commit install` separately to set up the git hooks

## Error Handling & Logging

### Exception Hierarchy

Use custom exception hierarchy (`src/utils/exceptions.py`):

<!--codeinclude-->
[Exception Hierarchy](../src/utils/exceptions.py) start_line:4 end_line:31
<!--/codeinclude-->

### Error Handling Rules

- Always chain exceptions: `raise SearchError(...) from e`
- Log errors with context using `structlog`:

```python
logger.error("Operation failed", error=str(e), context=value)
```

- Never silently swallow exceptions
- Provide actionable error messages

### Logging

- Use `structlog` for all logging (NOT `print` or `logging`)
- Import: `import structlog; logger = structlog.get_logger()`
- Log with structured data: `logger.info("event", key=value)`
- Use appropriate levels: DEBUG, INFO, WARNING, ERROR

### Logging Examples

```python
logger.info("Starting search", query=query, tools=[t.name for t in tools])
logger.warning("Search tool failed", tool=tool.name, error=str(result))
logger.error("Assessment failed", error=str(e))
```

### Error Chaining

Always preserve exception context:

```python
try:
    result = await api_call()
except httpx.HTTPError as e:
    raise SearchError(f"API call failed: {e}") from e
```

## Testing Requirements

### Test Structure

- Unit tests in `tests/unit/` (mocked, fast)
- Integration tests in `tests/integration/` (real APIs, marked `@pytest.mark.integration`)
- Use markers: `unit`, `integration`, `slow`

### Mocking

- Use `respx` for httpx mocking
- Use `pytest-mock` for general mocking
- Mock LLM calls in unit tests (use `MockJudgeHandler`)
- Fixtures in `tests/conftest.py`: `mock_httpx_client`, `mock_llm_response`

### TDD Workflow

1. Write failing test in `tests/unit/`
2. Implement in `src/`
3. Ensure test passes
4. Run checks: `uv run ruff check src tests && uv run mypy src && uv run pytest --cov=src --cov-report=term-missing tests/unit/ -v -m "not openai" -p no:logfire`

### Test Examples

```python
@pytest.mark.unit
async def test_pubmed_search(mock_httpx_client):
    tool = PubMedTool()
    results = await tool.search("metformin", max_results=5)
    assert len(results) > 0
    assert all(isinstance(r, Evidence) for r in results)

@pytest.mark.integration
async def test_real_pubmed_search():
    tool = PubMedTool()
    results = await tool.search("metformin", max_results=3)
    assert len(results) <= 3
```

### Test Coverage

- Run `uv run pytest --cov=src --cov-report=term-missing tests/unit/ -v -m "not openai" -p no:logfire` for coverage report
- Run `uv run pytest --cov=src --cov-report=html -p no:logfire` for HTML coverage report (opens `htmlcov/index.html`)
- Aim for >80% coverage on critical paths
- Exclude: `__init__.py`, `TYPE_CHECKING` blocks

## Implementation Patterns

### Search Tools

All tools implement `SearchTool` protocol (`src/tools/base.py`):

- Must have `name` property
- Must implement `async def search(query, max_results) -> list[Evidence]`
- Use `@retry` decorator from tenacity for resilience
- Rate limiting: Implement `_rate_limit()` for APIs with limits (e.g., PubMed)
- Error handling: Raise `SearchError` or `RateLimitError` on failures

Example pattern:

```python
class MySearchTool:
    @property
    def name(self) -> str:
        return "mytool"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(...))
    async def search(self, query: str, max_results: int = 10) -> list[Evidence]:
        # Implementation
        return evidence_list
```

### Judge Handlers

- Implement `JudgeHandlerProtocol` (`async def assess(question, evidence) -> JudgeAssessment`)
- Use pydantic-ai `Agent` with `output_type=JudgeAssessment`
- System prompts in `src/prompts/judge.py`
- Support fallback handlers: `MockJudgeHandler`, `HFInferenceJudgeHandler`
- Always return valid `JudgeAssessment` (never raise exceptions)

### Agent Factory Pattern

- Use factory functions for creating agents (`src/agent_factory/`)
- Lazy initialization for optional dependencies (e.g., embeddings, Modal)
- Check requirements before initialization:

<!--codeinclude-->
[Check Magentic Requirements](../src/utils/llm_factory.py) start_line:152 end_line:170
<!--/codeinclude-->

### State Management

- **Magentic Mode**: Use `ContextVar` for thread-safe state (`src/agents/state.py`)
- **Simple Mode**: Pass state via function parameters
- Never use global mutable state (except singletons via `@lru_cache`)

### Singleton Pattern

Use `@lru_cache(maxsize=1)` for singletons:

<!--codeinclude-->
[Singleton Pattern Example](../src/services/statistical_analyzer.py) start_line:252 end_line:255
<!--/codeinclude-->

- Lazy initialization to avoid requiring dependencies at import time

## Code Quality & Documentation

### Docstrings

- Google-style docstrings for all public functions
- Include Args, Returns, Raises sections
- Use type hints in docstrings only if needed for clarity

Example:

<!--codeinclude-->
[Search Method Docstring Example](../src/tools/pubmed.py) start_line:51 end_line:58
<!--/codeinclude-->

### Code Comments

- Explain WHY, not WHAT
- Document non-obvious patterns (e.g., why `requests` not `httpx` for ClinicalTrials)
- Mark critical sections: `# CRITICAL: ...`
- Document rate limiting rationale
- Explain async patterns when non-obvious

## Prompt Engineering & Citation Validation

### Judge Prompts

- System prompt in `src/prompts/judge.py`
- Format evidence with truncation (1500 chars per item)
- Handle empty evidence case separately
- Always request structured JSON output
- Use `format_user_prompt()` and `format_empty_evidence_prompt()` helpers

### Hypothesis Prompts

- Use diverse evidence selection (MMR algorithm)
- Sentence-aware truncation (`truncate_at_sentence()`)
- Format: Drug → Target → Pathway → Effect
- System prompt emphasizes mechanistic reasoning
- Use `format_hypothesis_prompt()` with embeddings for diversity

### Report Prompts

- Include full citation details for validation
- Use diverse evidence selection (n=20)
- **CRITICAL**: Emphasize citation validation rules
- Format hypotheses with support/contradiction counts
- System prompt includes explicit JSON structure requirements

### Citation Validation

- **ALWAYS** validate references before returning reports
- Use `validate_references()` from `src/utils/citation_validator.py`
- Remove hallucinated citations (URLs not in evidence)
- Log warnings for removed citations
- Never trust LLM-generated citations without validation

### Citation Validation Rules

1. Every reference URL must EXACTLY match a provided evidence URL
2. Do NOT invent, fabricate, or hallucinate any references
3. Do NOT modify paper titles, authors, dates, or URLs
4. If unsure about a citation, OMIT it rather than guess
5. Copy URLs exactly as provided - do not create similar-looking URLs

### Evidence Selection

- Use `select_diverse_evidence()` for MMR-based selection
- Balance relevance vs diversity (lambda=0.7 default)
- Sentence-aware truncation preserves meaning
- Limit evidence per prompt to avoid context overflow

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
