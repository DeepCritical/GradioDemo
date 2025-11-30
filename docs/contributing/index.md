# Contributing to DeepCritical

Thank you for your interest in contributing to DeepCritical! This guide will help you get started.

## Git Workflow

- `main`: Production-ready (GitHub)
- `dev`: Development integration (GitHub)
- Use feature branches: `yourname-dev`
- **NEVER** push directly to `main` or `dev` on HuggingFace
- GitHub is source of truth; HuggingFace is for deployment

## Development Commands

```bash
make install      # Install dependencies + pre-commit
make check        # Lint + typecheck + test (MUST PASS)
make test         # Run unit tests
make lint         # Run ruff
make format       # Format with ruff
make typecheck    # Run mypy
make test-cov     # Test with coverage
```

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




















