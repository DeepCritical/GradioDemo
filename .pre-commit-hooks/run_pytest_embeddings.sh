#!/bin/bash
# Wrapper script to sync embeddings dependencies and run embeddings tests

set -e

if command -v uv >/dev/null 2>&1; then
    echo "Syncing embeddings dependencies..."
    uv sync --extra embeddings
    echo "Running embeddings tests..."
    uv run pytest tests/ -v -m local_embeddings --tb=short -p no:logfire
else
    echo "Error: uv not found"
    exit 1
fi

