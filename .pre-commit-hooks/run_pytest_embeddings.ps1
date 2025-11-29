# PowerShell wrapper to sync embeddings dependencies and run embeddings tests

$ErrorActionPreference = "Stop"

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "Syncing embeddings dependencies..."
    uv sync --extra embeddings
    Write-Host "Running embeddings tests..."
    uv run pytest tests/ -v -m local_embeddings --tb=short -p no:logfire
} else {
    Write-Error "uv not found"
    exit 1
}

