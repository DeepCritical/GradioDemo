# Error Handling & Logging

This document outlines error handling and logging conventions for The DETERMINATOR.

## Exception Hierarchy

Use custom exception hierarchy (`src/utils/exceptions.py`):

<!--codeinclude-->
[Exception Hierarchy](../src/utils/exceptions.py) start_line:4 end_line:31
<!--/codeinclude-->

## Error Handling Rules

- Always chain exceptions: `raise SearchError(...) from e`
- Log errors with context using `structlog`:

```python
logger.error("Operation failed", error=str(e), context=value)
```

- Never silently swallow exceptions
- Provide actionable error messages

## Logging

- Use `structlog` for all logging (NOT `print` or `logging`)
- Import: `import structlog; logger = structlog.get_logger()`
- Log with structured data: `logger.info("event", key=value)`
- Use appropriate levels: DEBUG, INFO, WARNING, ERROR

## Logging Examples

```python
logger.info("Starting search", query=query, tools=[t.name for t in tools])
logger.warning("Search tool failed", tool=tool.name, error=str(result))
logger.error("Assessment failed", error=str(e))
```

## Error Chaining

Always preserve exception context:

```python
try:
    result = await api_call()
except httpx.HTTPError as e:
    raise SearchError(f"API call failed: {e}") from e
```

## See Also

- [Code Style](code-style.md) - Code style guidelines
- [Testing](testing.md) - Testing guidelines
