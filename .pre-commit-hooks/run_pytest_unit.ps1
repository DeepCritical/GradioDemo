# PowerShell wrapper to sync dependencies and run unit tests

$ErrorActionPreference = "Stop"

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "Syncing dependencies..."
    uv sync
    Write-Host "Running unit tests..."
    uv run pytest tests/unit/ -v -m "not openai and not embedding_provider" --tb=short -p no:logfire
} else {
    Write-Error "uv not found"
    exit 1
}

