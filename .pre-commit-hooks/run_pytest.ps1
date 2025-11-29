# PowerShell pytest runner for pre-commit (Windows)
# Uses uv if available, otherwise falls back to pytest

if (Get-Command uv -ErrorAction SilentlyContinue) {
    # Sync dependencies before running tests
    uv sync
    uv run pytest $args
} else {
    Write-Warning "uv not found, using system pytest (may have missing dependencies)"
    pytest $args
}








