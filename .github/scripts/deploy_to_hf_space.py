"""Deploy repository to Hugging Face Space, excluding unnecessary files."""

import os
import shutil
from pathlib import Path
from typing import Set

from huggingface_hub import HfApi, Repository


def get_excluded_dirs() -> Set[str]:
    """Get set of directory names to exclude from deployment."""
    return {
        "docs",
        "dev",
        "folder",
        "site",
        "tests",  # Optional - can be included if desired
        "examples",  # Optional - can be included if desired
        ".git",
        ".github",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "venv",
        "env",
        "ENV",
        "node_modules",
        ".cursor",
        "reference_repos",
        "burner_docs",
        "chroma_db",
        "logs",
        "build",
        "dist",
        ".eggs",
        "htmlcov",
    }


def get_excluded_files() -> Set[str]:
    """Get set of file names to exclude from deployment."""
    return {
        ".pre-commit-config.yaml",
        "mkdocs.yml",
        "uv.lock",
        "AGENTS.txt",
        "CONTRIBUTING.md",
        ".env",
        ".env.local",
        "*.local",
        ".DS_Store",
        "Thumbs.db",
        "*.log",
        ".coverage",
        "coverage.xml",
    }


def should_exclude(path: Path, excluded_dirs: Set[str], excluded_files: Set[str]) -> bool:
    """Check if a path should be excluded from deployment."""
    # Check if any parent directory is excluded
    for parent in path.parents:
        if parent.name in excluded_dirs:
            return True
    
    # Check if the path itself is a directory that should be excluded
    if path.is_dir() and path.name in excluded_dirs:
        return True
    
    # Check if the file name matches excluded patterns
    if path.is_file():
        # Check exact match
        if path.name in excluded_files:
            return True
        # Check pattern matches (simple wildcard support)
        for pattern in excluded_files:
            if "*" in pattern:
                # Simple pattern matching (e.g., "*.log")
                suffix = pattern.replace("*", "")
                if path.name.endswith(suffix):
                    return True
    
    return False


def deploy_to_hf_space() -> None:
    """Deploy repository to Hugging Face Space.
    
    Supports both user and organization Spaces:
    - User Space: username/space-name
    - Organization Space: organization-name/space-name
    
    Works with both classic tokens and fine-grained tokens.
    """
    # Get configuration from environment variables
    hf_token = os.getenv("HF_TOKEN")
    hf_username = os.getenv("HF_USERNAME")  # Can be username or organization name
    space_name = os.getenv("HF_SPACE_NAME")
    
    if not all([hf_token, hf_username, space_name]):
        raise ValueError(
            "Missing required environment variables: HF_TOKEN, HF_USERNAME, HF_SPACE_NAME"
        )
    
    # HF_USERNAME can be either a username or organization name
    # Format: {username|organization}/{space_name}
    repo_id = f"{hf_username}/{space_name}"
    local_dir = "hf_space"
    
    print(f"🚀 Deploying to Hugging Face Space: {repo_id}")
    
    # Initialize HF API
    api = HfApi(token=hf_token)
    
    # Clone or create repository
    try:
        repo = Repository(
            local_dir=local_dir,
            clone_from=repo_id,
            token=hf_token,
            repo_type="space",
        )
        print(f"✅ Cloned existing Space: {repo_id}")
    except Exception as e:
        print(f"⚠️  Could not clone Space (may not exist yet): {e}")
        # Create new repository
        api.create_repo(
            repo_id=space_name,
            repo_type="space",
            space_sdk="gradio",
            token=hf_token,
            exist_ok=True,
        )
        repo = Repository(
            local_dir=local_dir,
            clone_from=repo_id,
            token=hf_token,
            repo_type="space",
        )
        print(f"✅ Created new Space: {repo_id}")
    
    # Get exclusion sets
    excluded_dirs = get_excluded_dirs()
    excluded_files = get_excluded_files()
    
    # Remove all existing files in HF Space (except .git)
    print("🧹 Cleaning existing files...")
    for item in Path(local_dir).iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    
    # Copy files from repository root
    print("📦 Copying files...")
    repo_root = Path(".")
    files_copied = 0
    dirs_copied = 0
    
    for item in repo_root.rglob("*"):
        # Skip if in .git directory
        if ".git" in item.parts:
            continue
        
        # Skip if should be excluded
        if should_exclude(item, excluded_dirs, excluded_files):
            continue
        
        # Calculate relative path
        try:
            rel_path = item.relative_to(repo_root)
        except ValueError:
            # Item is outside repo root, skip
            continue
        
        # Skip if in excluded directory
        if any(part in excluded_dirs for part in rel_path.parts):
            continue
        
        # Destination path
        dest_path = Path(local_dir) / rel_path
        
        # Create parent directories
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file or directory
        if item.is_file():
            shutil.copy2(item, dest_path)
            files_copied += 1
        elif item.is_dir():
            # Directory will be created by parent mkdir, but we track it
            dirs_copied += 1
    
    print(f"✅ Copied {files_copied} files and {dirs_copied} directories")
    
    # Commit and push changes
    print("💾 Committing changes...")
    repo.git_add(auto_lfs_track=True)
    
    # Check if there are changes to commit
    try:
        # Try to check if repo is clean (may not be available in all versions)
        if hasattr(repo, "is_repo_clean") and repo.is_repo_clean():
            print("ℹ️  No changes to commit (repository is up to date)")
        else:
            repo.git_commit("Deploy to Hugging Face Space [skip ci]")
            print("📤 Pushing to Hugging Face Space...")
            repo.git_push()
            print("✅ Deployment complete!")
    except Exception as e:
        # If check fails, try to commit anyway (will fail gracefully if no changes)
        try:
            repo.git_commit("Deploy to Hugging Face Space [skip ci]")
            print("📤 Pushing to Hugging Face Space...")
            repo.git_push()
            print("✅ Deployment complete!")
        except Exception as commit_error:
            # If commit fails, likely no changes
            if "nothing to commit" in str(commit_error).lower():
                print("ℹ️  No changes to commit (repository is up to date)")
            else:
                print(f"⚠️  Warning during commit: {commit_error}")
                raise
    
    print(f"🎉 Successfully deployed to: https://huggingface.co/spaces/{repo_id}")


if __name__ == "__main__":
    deploy_to_hf_space()

