# Code Quality & Documentation

This document outlines code quality standards and documentation requirements.

## Linting

- Ruff with 100-char line length
- Ignore rules documented in `pyproject.toml`:
  - `PLR0913`: Too many arguments (agents need many params)
  - `PLR0912`: Too many branches (complex orchestrator logic)
  - `PLR0911`: Too many return statements (complex agent logic)
  - `PLR2004`: Magic values (statistical constants)
  - `PLW0603`: Global statement (singleton pattern)
  - `PLC0415`: Lazy imports for optional dependencies

## Type Checking

- `mypy --strict` compliance
- `ignore_missing_imports = true` (for optional dependencies)
- Exclude: `reference_repos/`, `examples/`
- All functions must have complete type annotations

## Pre-commit

- Run `make check` before committing
- Must pass: lint + typecheck + test-cov
- Pre-commit hooks installed via `make install`

## Documentation

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

## See Also

- [Code Style](code-style.md) - Code style guidelines
- [Testing](testing.md) - Testing guidelines













