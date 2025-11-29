#!/usr/bin/env python3
"""Cross-platform pytest runner that syncs dependencies before running tests."""

import subprocess
import sys


def run_command(
    cmd: list[str], check: bool = True, shell: bool = False, cwd: str | None = None
) -> int:
    """Run a command and return exit code."""
    try:
        result = subprocess.run(
            cmd,
            check=check,
            shell=shell,
            cwd=cwd,
            env=None,  # Use current environment, uv will handle venv
        )
        return result.returncode
    except subprocess.CalledProcessError as e:
        return e.returncode
    except FileNotFoundError:
        print(f"Error: Command not found: {cmd[0]}")
        return 1


def main() -> int:
    """Main entry point."""
    import os
    from pathlib import Path

    # Get the project root (where pyproject.toml is)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Change to project root to ensure uv works correctly
    os.chdir(project_root)

    # Check if uv is available
    if run_command(["uv", "--version"], check=False) != 0:
        print("Error: uv not found. Please install uv: https://github.com/astral-sh/uv")
        return 1

    # Parse arguments
    test_type = sys.argv[1] if len(sys.argv) > 1 else "unit"
    extra_args = sys.argv[2:] if len(sys.argv) > 2 else []

    # Sync dependencies - always include dev
    # Note: embeddings dependencies are now in main dependencies, not optional
    # So we just sync with --dev for all test types
    sync_cmd = ["uv", "sync", "--dev"]

    print(f"Syncing dependencies for {test_type} tests...")
    if run_command(sync_cmd, cwd=project_root) != 0:
        return 1

    # Build pytest command - use uv run to ensure correct environment
    if test_type == "unit":
        pytest_args = [
            "tests/unit/",
            "-v",
            "-m",
            "not openai and not embedding_provider",
            "--tb=short",
            "-p",
            "no:logfire",
        ]
    elif test_type == "embeddings":
        pytest_args = [
            "tests/",
            "-v",
            "-m",
            "local_embeddings",
            "--tb=short",
            "-p",
            "no:logfire",
        ]
    else:
        pytest_args = []

    pytest_args.extend(extra_args)

    # Use uv run python -m pytest to ensure we use the venv's pytest
    # This is more reliable than uv run pytest which might find system pytest
    pytest_cmd = ["uv", "run", "python", "-m", "pytest", *pytest_args]

    print(f"Running {test_type} tests...")
    return run_command(pytest_cmd, cwd=project_root)


if __name__ == "__main__":
    sys.exit(main())
