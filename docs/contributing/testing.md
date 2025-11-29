# Testing Requirements

This document outlines testing requirements and guidelines for DeepCritical.

## Test Structure

- Unit tests in `tests/unit/` (mocked, fast)
- Integration tests in `tests/integration/` (real APIs, marked `@pytest.mark.integration`)
- Use markers: `unit`, `integration`, `slow`

## Mocking

- Use `respx` for httpx mocking
- Use `pytest-mock` for general mocking
- Mock LLM calls in unit tests (use `MockJudgeHandler`)
- Fixtures in `tests/conftest.py`: `mock_httpx_client`, `mock_llm_response`

## TDD Workflow

1. Write failing test in `tests/unit/`
2. Implement in `src/`
3. Ensure test passes
4. Run `make check` (lint + typecheck + test)

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

- Run `make test-cov` for coverage report
- Aim for >80% coverage on critical paths
- Exclude: `__init__.py`, `TYPE_CHECKING` blocks

## See Also

- [Code Style](code-style.md) - Code style guidelines
- [Implementation Patterns](implementation-patterns.md) - Common patterns












