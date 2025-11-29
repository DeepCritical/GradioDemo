#!/usr/bin/env python3
"""Cross-platform pytest runner that syncs dependencies before running tests."""

import shutil
import subprocess
import sys
from pathlib import Path


def clean_caches(project_root: Path) -> None:
    """Remove pytest and Python cache directories and files.

    Only scans specific directories (src/, tests/) to avoid resource
    exhaustion from scanning large directories like .venv on Windows.
    """
    # Directories to scan for caches (only project code, not dependencies)
    scan_dirs = ["src", "tests", ".pre-commit-hooks"]

    # Directories to exclude (to avoid resource issues)
    exclude_dirs = {
        ".venv",
        "venv",
        "ENV",
        "env",
        ".git",
        "node_modules",
        "dist",
        "build",
        ".eggs",
        "reference_repos",
        "folder",
    }

    cache_patterns = [
        ".pytest_cache",
        "__pycache__",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".mypy_cache",
        ".ruff_cache",
    ]

    def should_exclude(path: Path) -> bool:
        """Check if a path should be excluded from cache cleanup."""
        # Check if any parent directory is in exclude list
        for parent in path.parents:
            if parent.name in exclude_dirs:
                return True
        # Check if the path itself is excluded
        if path.name in exclude_dirs:
            return True
        return False

    cleaned = []

    # Only scan specific directories to avoid resource exhaustion
    for scan_dir in scan_dirs:
        scan_path = project_root / scan_dir
        if not scan_path.exists():
            continue

        for pattern in cache_patterns:
            if "*" in pattern:
                # Handle glob patterns for files
                try:
                    for cache_file in scan_path.rglob(pattern):
                        if should_exclude(cache_file):
                            continue
                        try:
                            if cache_file.is_file():
                                cache_file.unlink()
                                cleaned.append(str(cache_file.relative_to(project_root)))
                        except OSError:
                            pass  # Ignore errors (file might be locked or already deleted)
                except OSError:
                    pass  # Ignore errors during directory traversal
            else:
                # Handle directory patterns
                try:
                    for cache_dir in scan_path.rglob(pattern):
                        if should_exclude(cache_dir):
                            continue
                        try:
                            if cache_dir.is_dir():
                                shutil.rmtree(cache_dir, ignore_errors=True)
                                cleaned.append(str(cache_dir.relative_to(project_root)))
                        except OSError:
                            pass  # Ignore errors (directory might be locked)
                except OSError:
                    pass  # Ignore errors during directory traversal

    # Also clean root-level caches (like .pytest_cache in project root)
    for pattern in [".pytest_cache", ".mypy_cache", ".ruff_cache"]:
        cache_path = project_root / pattern
        if cache_path.exists() and cache_path.is_dir():
            try:
                shutil.rmtree(cache_path, ignore_errors=True)
                cleaned.append(pattern)
            except OSError:
                pass

    if cleaned:
        print(f"Cleaned {len(cleaned)} cache items")
    else:
        print("No cache files found to clean")


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

    # Get the project root (where pyproject.toml is)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Change to project root to ensure uv works correctly
    os.chdir(project_root)

    # Clean caches before running tests
    print("Cleaning pytest and Python caches...")
    clean_caches(project_root)

    # Check if uv is available
    if run_command(["uv", "--version"], check=False) != 0:
        print("Error: uv not found. Please install uv: https://github.com/astral-sh/uv")
        return 1

    # Parse arguments
    test_type = sys.argv[1] if len(sys.argv) > 1 else "unit"
    extra_args = sys.argv[2:] if len(sys.argv) > 2 else []

    # Sync dependencies - always include dev
    # Note: embeddings dependencies are now in main dependencies, not optional
    # Use --extra dev for [project.optional-dependencies].dev (not --dev which is for [dependency-groups])
    sync_cmd = ["uv", "sync", "--extra", "dev"]

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
            "--cache-clear",  # Clear pytest cache before running
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
            "--cache-clear",  # Clear pytest cache before running
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
