# Contributing to DeepCritical

Thank you for your interest in contributing to DeepCritical! This guide will help you get started.

## Table of Contents

- [Git Workflow](#git-workflow)
- [Getting Started](#getting-started)
- [Development Commands](#development-commands)
- [Code Style & Conventions](#code-style--conventions)
- [Type Safety](#type-safety)
- [Error Handling & Logging](#error-handling--logging)
- [Testing Requirements](#testing-requirements)
- [Implementation Patterns](#implementation-patterns)
- [Code Quality & Documentation](#code-quality--documentation)
- [Prompt Engineering & Citation Validation](#prompt-engineering--citation-validation)
- [MCP Integration](#mcp-integration)
- [Common Pitfalls](#common-pitfalls)
- [Key Principles](#key-principles)
- [Pull Request Process](#pull-request-process)

## Git Workflow

- `main`: Production-ready (GitHub)
- `dev`: Development integration (GitHub)
- Use feature branches: `yourname-dev`
- **NEVER** push directly to `main` or `dev` on HuggingFace
- GitHub is source of truth; HuggingFace is for deployment

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork**:

   ```bash
   git clone https://github.com/yourusername/GradioDemo.git
   cd GradioDemo
   ```

3. **Install dependencies**:

   ```bash
   make install
   ```

4. **Create a feature branch**:

   ```bash
   git checkout -b yourname-feature-name
   ```

5. **Make your changes** following the guidelines below
6. **Run checks**:

   ```bash
   make check
   ```

7. **Commit and push**:

   ```bash
   git commit -m "Description of changes"
   git push origin yourname-feature-name
   ```
8. **Create a pull request** on GitHub

## Development Commands

```bash
make install      # Install dependencies + pre-commit
make check        # Lint + typecheck + test (MUST PASS)
make test         # Run unit tests
make lint         # Run ruff
make format       # Format with ruff
make typecheck    # Run mypy
make test-cov     # Test with coverage
make docs-build  # Build documentation
make docs-serve  # Serve documentation locally
```

## Code Style & Conventions

### Type Safety

- **ALWAYS** use type hints for all function parameters and return types
- Use `mypy --strict` compliance (no `Any` unless absolutely necessary)
- Use `TYPE_CHECKING` imports for circular dependencies:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.services.embeddings import EmbeddingService
```

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

- Run `make check` before committing
- Must pass: lint + typecheck + test-cov
- Pre-commit hooks installed via `make install`
- **CRITICAL**: Make sure you run the full pre-commit checks before opening a PR (not draft), otherwise Obstacle is the Way will lose his mind

## Error Handling & Logging

### Exception Hierarchy

Use custom exception hierarchy (`src/utils/exceptions.py`):

- `DeepCriticalError` (base)
- `SearchError` → `RateLimitError`
- `JudgeError`
- `ConfigurationError`

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
4. Run `make check` (lint + typecheck + test)

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

- Run `make test-cov` for coverage report
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

```python
def check_magentic_requirements() -> None:
    if not settings.has_openai_key:
        raise ConfigurationError("Magentic requires OpenAI")
```

### State Management

- **Magentic Mode**: Use `ContextVar` for thread-safe state (`src/agents/state.py`)
- **Simple Mode**: Pass state via function parameters
- Never use global mutable state (except singletons via `@lru_cache`)

### Singleton Pattern

Use `@lru_cache(maxsize=1)` for singletons:

```python
@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
```

- Lazy initialization to avoid requiring dependencies at import time

## Code Quality & Documentation

### Docstrings

- Google-style docstrings for all public functions
- Include Args, Returns, Raises sections
- Use type hints in docstrings only if needed for clarity

Example:

```python
async def search(self, query: str, max_results: int = 10) -> list[Evidence]:
    """Search PubMed and return evidence.

    Args:
        query: The search query string
        max_results: Maximum number of results to return

    Returns:
        List of Evidence objects

    Raises:
        SearchError: If the search fails
        RateLimitError: If we hit rate limits
    """
```

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

1. Ensure all checks pass: `make check`
2. Update documentation if needed
3. Add tests for new features
4. Update CHANGELOG if applicable
5. Request review from maintainers
6. Address review feedback
7. Wait for approval before merging

## Questions?

- Open an issue on GitHub
- Check existing documentation
- Review code examples in the codebase

Thank you for contributing to DeepCritical!

