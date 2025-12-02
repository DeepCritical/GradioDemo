# Code Quality & Documentation

This document outlines code quality standards and documentation requirements for The DETERMINATOR.

## Linting

- Ruff with 100-char line length
- Ignore rules documented in `pyproject.toml`:
  - `PLR0913`: Too many arguments (agents need many params)
  - `PLR0912`: Too many branches (complex orchestrator logic)
  - `PLR0911`: Too many return statements (complex agent logic)
  - `PLR2004`: Magic values (statistical constants)
  - `PLW0603`: Global statement (singleton pattern)
  - `PLC0415`: Lazy imports for optional dependencies
  - `E402`: Module level import not at top (needed for pytest.importorskip)
  - `E501`: Line too long (ignore line length violations)
  - `RUF100`: Unused noqa (version differences between local/CI)

## Type Checking

- `mypy --strict` compliance
- `ignore_missing_imports = true` (for optional dependencies)
- Exclude: `reference_repos/`, `examples/`
- All functions must have complete type annotations

## Pre-commit

Pre-commit hooks run automatically on commit to ensure code quality. Configuration is in `.pre-commit-config.yaml`.

### Installation

```bash
# Install dependencies (includes pre-commit package)
uv sync --all-extras

# Set up git hooks (must be run separately)
uv run pre-commit install
```

**Note**: `uv sync --all-extras` installs the pre-commit package, but you must run `uv run pre-commit install` separately to set up the git hooks.

### Pre-commit Hooks

The following hooks run automatically on commit:

1. **ruff**: Lints code and fixes issues automatically
   - Runs on: `src/` (excludes `tests/`, `reference_repos/`)
   - Auto-fixes: Yes

2. **ruff-format**: Formats code with ruff
   - Runs on: `src/` (excludes `tests/`, `reference_repos/`)
   - Auto-fixes: Yes

3. **mypy**: Type checking
   - Runs on: `src/` (excludes `folder/`)
   - Additional dependencies: pydantic, pydantic-settings, tenacity, pydantic-ai

4. **pytest-unit**: Runs unit tests (excludes OpenAI and embedding_provider tests)
   - Runs: `tests/unit/` with `-m "not openai and not embedding_provider"`
   - Always runs: Yes (not just on changed files)

5. **pytest-local-embeddings**: Runs local embedding tests
   - Runs: `tests/` with `-m "local_embeddings"`
   - Always runs: Yes

### Manual Pre-commit Run

To run pre-commit hooks manually (without committing):

```bash
uv run pre-commit run --all-files
```

### Troubleshooting

- **Hooks failing**: Fix the issues shown in the output, then commit again
- **Skipping hooks**: Use `git commit --no-verify` (not recommended)
- **Hook not running**: Ensure hooks are installed with `uv run pre-commit install`
- **Type errors**: Check that all dependencies are installed with `uv sync --all-extras`

## Documentation

### Building Documentation

Documentation is built using MkDocs. Source files are in `docs/`, and the configuration is in `mkdocs.yml`.

```bash
# Build documentation
uv run mkdocs build

# Serve documentation locally (http://127.0.0.1:8000)
uv run mkdocs serve
```

The documentation site is published at: <https://deepcritical.github.io/GradioDemo/>

### Docstrings

- Google-style docstrings for all public functions
- Include Args, Returns, Raises sections
- Use type hints in docstrings only if needed for clarity

Example:

<!--codeinclude-->
[Search Method Docstring Example](../src/tools/pubmed.py) start_line:51 end_line:70
<!--/codeinclude-->

### Code Comments

- Explain WHY, not WHAT
- Document non-obvious patterns (e.g., why `requests` not `httpx` for ClinicalTrials)
- Mark critical sections: `# CRITICAL: ...`
- Document rate limiting rationale
- Explain async patterns when non-obvious

## See Also

- [Code Style](code-style.md) - Code style guidelines
- [Testing](testing.md) - Testing guidelines
