#!/bin/bash
# Wrapper script to sync dependencies and run unit tests

set -e

if command -v uv >/dev/null 2>&1; then
    echo "Syncing dependencies..."
    uv sync
    echo "Running unit tests..."
    uv run pytest tests/unit/ -v -m "not openai and not embedding_provider" --tb=short -p no:logfire
else
    echo "Error: uv not found"
    exit 1
fi

