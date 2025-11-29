# Implementation Patterns

This document outlines common implementation patterns used in DeepCritical.

## Search Tools

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

## Judge Handlers

- Implement `JudgeHandlerProtocol` (`async def assess(question, evidence) -> JudgeAssessment`)
- Use pydantic-ai `Agent` with `output_type=JudgeAssessment`
- System prompts in `src/prompts/judge.py`
- Support fallback handlers: `MockJudgeHandler`, `HFInferenceJudgeHandler`
- Always return valid `JudgeAssessment` (never raise exceptions)

## Agent Factory Pattern

- Use factory functions for creating agents (`src/agent_factory/`)
- Lazy initialization for optional dependencies (e.g., embeddings, Modal)
- Check requirements before initialization:

```python
def check_magentic_requirements() -> None:
    if not settings.has_openai_key:
        raise ConfigurationError("Magentic requires OpenAI")
```

## State Management

- **Magentic Mode**: Use `ContextVar` for thread-safe state (`src/agents/state.py`)
- **Simple Mode**: Pass state via function parameters
- Never use global mutable state (except singletons via `@lru_cache`)

## Singleton Pattern

Use `@lru_cache(maxsize=1)` for singletons:

```python
@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
```

- Lazy initialization to avoid requiring dependencies at import time

## See Also

- [Code Style](code-style.md) - Code style guidelines
- [Error Handling](error-handling.md) - Error handling guidelines







