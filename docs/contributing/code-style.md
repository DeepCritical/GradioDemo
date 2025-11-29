# Code Style & Conventions

This document outlines the code style and conventions for DeepCritical.

## Type Safety

- **ALWAYS** use type hints for all function parameters and return types
- Use `mypy --strict` compliance (no `Any` unless absolutely necessary)
- Use `TYPE_CHECKING` imports for circular dependencies:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.services.embeddings import EmbeddingService
```

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







