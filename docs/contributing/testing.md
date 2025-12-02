# Testing Requirements

This document outlines testing requirements and guidelines for The DETERMINATOR.

## Test Structure

- Unit tests in `tests/unit/` (mocked, fast)
- Integration tests in `tests/integration/` (real APIs, marked `@pytest.mark.integration`)
- Use markers: `unit`, `integration`, `slow`, `openai`, `huggingface`, `embedding_provider`, `local_embeddings`

## Test Markers

The project uses pytest markers to categorize tests. These markers are defined in `pyproject.toml`:

- `@pytest.mark.unit`: Unit tests (mocked, fast) - Run with `-m "unit"`
- `@pytest.mark.integration`: Integration tests (real APIs) - Run with `-m "integration"`
- `@pytest.mark.slow`: Slow tests - Run with `-m "slow"`
- `@pytest.mark.openai`: Tests requiring OpenAI API key - Run with `-m "openai"` or exclude with `-m "not openai"`
- `@pytest.mark.huggingface`: Tests requiring HuggingFace API key or using HuggingFace models - Run with `-m "huggingface"`
- `@pytest.mark.embedding_provider`: Tests requiring API-based embedding providers (OpenAI, etc.) - Run with `-m "embedding_provider"`
- `@pytest.mark.local_embeddings`: Tests using local embeddings (sentence-transformers, ChromaDB) - Run with `-m "local_embeddings"`

### Running Tests by Marker

```bash
# Run only unit tests (excludes OpenAI tests by default)
uv run pytest tests/unit/ -v -m "not openai" -p no:logfire

# Run HuggingFace tests
uv run pytest tests/ -v -m "huggingface" -p no:logfire

# Run all tests
uv run pytest tests/ -v -p no:logfire

# Run only local embedding tests
uv run pytest tests/ -v -m "local_embeddings" -p no:logfire

# Exclude slow tests
uv run pytest tests/ -v -m "not slow" -p no:logfire
```

**Note**: The `-p no:logfire` flag disables the logfire plugin to avoid conflicts during testing.

## Mocking

- Use `respx` for httpx mocking
- Use `pytest-mock` for general mocking
- Mock LLM calls in unit tests (use `MockJudgeHandler`)
- Fixtures in `tests/conftest.py`: `mock_httpx_client`, `mock_llm_response`

## TDD Workflow

1. Write failing test in `tests/unit/`
2. Implement in `src/`
3. Ensure test passes
4. Run checks: `uv run ruff check src tests && uv run mypy src && uv run pytest --cov=src --cov-report=term-missing tests/unit/ -v -m "not openai" -p no:logfire`

### Test Command Examples

```bash
# Run unit tests (default, excludes OpenAI tests)
uv run pytest tests/unit/ -v -m "not openai" -p no:logfire

# Run HuggingFace tests
uv run pytest tests/ -v -m "huggingface" -p no:logfire

# Run all tests
uv run pytest tests/ -v -p no:logfire
```

## Test Examples

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

## Test Coverage

### Terminal Coverage Report

```bash
uv run pytest --cov=src --cov-report=term-missing tests/unit/ -v -m "not openai" -p no:logfire
```

This shows coverage with missing lines highlighted in the terminal output.

### HTML Coverage Report

```bash
uv run pytest --cov=src --cov-report=html -p no:logfire
```

This generates an HTML coverage report in `htmlcov/index.html`. Open this file in your browser to see detailed coverage information.

### Coverage Goals

- Aim for >80% coverage on critical paths
- Exclude: `__init__.py`, `TYPE_CHECKING` blocks
- Coverage configuration is in `pyproject.toml` under `[tool.coverage.*]`

## See Also

- [Code Style](code-style.md) - Code style guidelines
- [Implementation Patterns](implementation-patterns.md) - Common patterns
