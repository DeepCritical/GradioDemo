# Code Style & Conventions

This document outlines the code style and conventions for The DETERMINATOR.

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
```

### Running Commands

All development commands should use `uv run` prefix:

```bash
# Instead of: pytest tests/
uv run pytest tests/

# Instead of: ruff check src
uv run ruff check src

# Instead of: mypy src
uv run mypy src
```

This ensures commands run in the correct virtual environment managed by `uv`.

## Type Safety

- **ALWAYS** use type hints for all function parameters and return types
- Use `mypy --strict` compliance (no `Any` unless absolutely necessary)
- Use `TYPE_CHECKING` imports for circular dependencies:

<!--codeinclude-->
[TYPE_CHECKING Import Pattern](../src/utils/citation_validator.py) start_line:8 end_line:11
<!--/codeinclude-->

## Pydantic Models

- All data exchange uses Pydantic models (`src/utils/models.py`)
- Models are frozen (`model_config = {"frozen": True}`) for immutability
- Use `Field()` with descriptions for all model fields
- Validate with `ge=`, `le=`, `min_length=`, `max_length=` constraints

## Async Patterns

- **ALL** I/O operations must be async (`async def`, `await`)
- Use `asyncio.gather()` for parallel operations
- CPU-bound work (embeddings, parsing) must use `run_in_executor()`:

```python
loop = asyncio.get_running_loop()
result = await loop.run_in_executor(None, cpu_bound_function, args)
```

- Never block the event loop with synchronous I/O

## Common Pitfalls

1. **Blocking the event loop**: Never use sync I/O in async functions
2. **Missing type hints**: All functions must have complete type annotations
3. **Global mutable state**: Use ContextVar or pass via parameters
4. **Import errors**: Lazy-load optional dependencies (magentic, modal, embeddings)

## See Also

- [Error Handling](error-handling.md) - Error handling guidelines
- [Implementation Patterns](implementation-patterns.md) - Common patterns
