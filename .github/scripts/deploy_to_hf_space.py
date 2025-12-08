"""Deploy repository to Hugging Face Space, excluding unnecessary files."""

import os
import shutil
import subprocess
<<<<<<< HEAD
import tempfile
from pathlib import Path
=======
from pathlib import Path
from typing import Set
>>>>>>> origin/dev

from huggingface_hub import HfApi


<<<<<<< HEAD
def get_excluded_dirs() -> set[str]:
=======
def get_excluded_dirs() -> Set[str]:
>>>>>>> origin/dev
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
<<<<<<< HEAD
        "hf_space",  # Exclude the cloned HF Space directory itself
    }


def get_excluded_files() -> set[str]:
=======
    }


def get_excluded_files() -> Set[str]:
>>>>>>> origin/dev
    """Get set of file names to exclude from deployment."""
    return {
        ".pre-commit-config.yaml",
        "mkdocs.yml",
        "uv.lock",
        "AGENTS.txt",
<<<<<<< HEAD
=======
        "CONTRIBUTING.md",
>>>>>>> origin/dev
        ".env",
        ".env.local",
        "*.local",
        ".DS_Store",
        "Thumbs.db",
        "*.log",
        ".coverage",
        "coverage.xml",
    }


<<<<<<< HEAD
def should_exclude(path: Path, excluded_dirs: set[str], excluded_files: set[str]) -> bool:
=======
def should_exclude(path: Path, excluded_dirs: Set[str], excluded_files: Set[str]) -> bool:
>>>>>>> origin/dev
    """Check if a path should be excluded from deployment."""
    # Check if any parent directory is excluded
    for parent in path.parents:
        if parent.name in excluded_dirs:
            return True
<<<<<<< HEAD

    # Check if the path itself is a directory that should be excluded
    if path.is_dir() and path.name in excluded_dirs:
        return True

=======
    
    # Check if the path itself is a directory that should be excluded
    if path.is_dir() and path.name in excluded_dirs:
        return True
    
>>>>>>> origin/dev
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
<<<<<<< HEAD

=======
    
>>>>>>> origin/dev
    return False


def deploy_to_hf_space() -> None:
    """Deploy repository to Hugging Face Space.
<<<<<<< HEAD

    Supports both user and organization Spaces:
    - User Space: username/space-name
    - Organization Space: organization-name/space-name

=======
    
    Supports both user and organization Spaces:
    - User Space: username/space-name
    - Organization Space: organization-name/space-name
    
>>>>>>> origin/dev
    Works with both classic tokens and fine-grained tokens.
    """
    # Get configuration from environment variables
    hf_token = os.getenv("HF_TOKEN")
    hf_username = os.getenv("HF_USERNAME")  # Can be username or organization name
    space_name = os.getenv("HF_SPACE_NAME")
<<<<<<< HEAD

    # Check which variables are missing and provide helpful error message
    missing = []
    if not hf_token:
        missing.append("HF_TOKEN (should be in repository secrets)")
    if not hf_username:
        missing.append("HF_USERNAME (should be in repository variables)")
    if not space_name:
        missing.append("HF_SPACE_NAME (should be in repository variables)")

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Please configure:\n"
            f"  - HF_TOKEN in Settings > Secrets and variables > Actions > Secrets\n"
            f"  - HF_USERNAME in Settings > Secrets and variables > Actions > Variables\n"
            f"  - HF_SPACE_NAME in Settings > Secrets and variables > Actions > Variables"
        )

=======
    
    if not all([hf_token, hf_username, space_name]):
        raise ValueError(
            "Missing required environment variables: HF_TOKEN, HF_USERNAME, HF_SPACE_NAME"
        )
    
>>>>>>> origin/dev
    # HF_USERNAME can be either a username or organization name
    # Format: {username|organization}/{space_name}
    repo_id = f"{hf_username}/{space_name}"
    local_dir = "hf_space"
<<<<<<< HEAD

    print(f"🚀 Deploying to Hugging Face Space: {repo_id}")

    # Initialize HF API
    api = HfApi(token=hf_token)

=======
    
    print(f"🚀 Deploying to Hugging Face Space: {repo_id}")
    
    # Initialize HF API
    api = HfApi(token=hf_token)
    
>>>>>>> origin/dev
    # Create Space if it doesn't exist
    try:
        api.repo_info(repo_id=repo_id, repo_type="space", token=hf_token)
        print(f"✅ Space exists: {repo_id}")
    except Exception:
        print(f"⚠️  Space does not exist, creating: {repo_id}")
        # Create new repository
        # Note: For organizations, repo_id should be "org/space-name"
        # For users, repo_id should be "username/space-name"
        api.create_repo(
            repo_id=repo_id,  # Full repo_id including owner
            repo_type="space",
            space_sdk="gradio",
            token=hf_token,
            exist_ok=True,
        )
        print(f"✅ Created new Space: {repo_id}")
<<<<<<< HEAD

    # Configure Git credential helper for authentication
    # This is needed for Git LFS to work properly with fine-grained tokens
    print("🔐 Configuring Git credentials...")

    # Use Git credential store to store the token
    # This allows Git LFS to authenticate properly
    temp_dir = Path(tempfile.gettempdir())
    credential_store = temp_dir / ".git-credentials-hf"

    # Write credentials in the format: https://username:token@huggingface.co
    credential_store.write_text(
        f"https://{hf_username}:{hf_token}@huggingface.co\n", encoding="utf-8"
    )
    try:
        credential_store.chmod(0o600)  # Secure permissions (Unix only)
    except OSError:
        # Windows doesn't support chmod, skip
        pass

    # Configure Git to use the credential store
    subprocess.run(
        ["git", "config", "--global", "credential.helper", f"store --file={credential_store}"],
        check=True,
        capture_output=True,
    )

    # Also set environment variable for Git LFS
    os.environ["GIT_CREDENTIAL_HELPER"] = f"store --file={credential_store}"

    # Clone repository using git
    # Use the token in the URL for initial clone, but LFS will use credential store
    space_url = f"https://{hf_username}:{hf_token}@huggingface.co/spaces/{repo_id}"

    if Path(local_dir).exists():
        print(f"🧹 Removing existing {local_dir} directory...")
        shutil.rmtree(local_dir)

    print("📥 Cloning Space repository...")
=======
    
    # Clone repository using git
    space_url = f"https://{hf_token}@huggingface.co/spaces/{repo_id}"
    
    if Path(local_dir).exists():
        print(f"🧹 Removing existing {local_dir} directory...")
        shutil.rmtree(local_dir)
    
    print(f"📥 Cloning Space repository...")
>>>>>>> origin/dev
    try:
        result = subprocess.run(
            ["git", "clone", space_url, local_dir],
            check=True,
            capture_output=True,
            text=True,
        )
<<<<<<< HEAD
        print("✅ Cloned Space repository")

        # After clone, configure the remote to use credential helper
        # This ensures future operations (like push) use the credential store
        os.chdir(local_dir)
        subprocess.run(
            ["git", "remote", "set-url", "origin", f"https://huggingface.co/spaces/{repo_id}"],
            check=True,
            capture_output=True,
        )
        os.chdir("..")

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else e.stdout if e.stdout else "Unknown error"
        print(f"❌ Failed to clone Space repository: {error_msg}")

        # Try alternative: clone with LFS skip, then fetch LFS files separately
        print("🔄 Trying alternative clone method (skip LFS during clone)...")
        try:
            env = os.environ.copy()
            env["GIT_LFS_SKIP_SMUDGE"] = "1"  # Skip LFS during clone

            subprocess.run(
                ["git", "clone", space_url, local_dir],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            print("✅ Cloned Space repository (LFS skipped)")

            # Configure remote
            os.chdir(local_dir)
            subprocess.run(
                ["git", "remote", "set-url", "origin", f"https://huggingface.co/spaces/{repo_id}"],
                check=True,
                capture_output=True,
            )

            # Try to fetch LFS files with proper authentication
            print("📥 Fetching LFS files...")
            subprocess.run(
                ["git", "lfs", "pull"],
                check=False,  # Don't fail if LFS pull fails - we'll continue without LFS files
                capture_output=True,
                text=True,
            )
            os.chdir("..")
            print("✅ Repository cloned (LFS files may be incomplete, but deployment can continue)")
        except subprocess.CalledProcessError as e2:
            error_msg2 = e2.stderr if e2.stderr else e2.stdout if e2.stdout else "Unknown error"
            print(f"❌ Alternative clone method also failed: {error_msg2}")
            raise RuntimeError(f"Git clone failed: {error_msg}") from e

    # Get exclusion sets
    excluded_dirs = get_excluded_dirs()
    excluded_files = get_excluded_files()

=======
        print(f"✅ Cloned Space repository")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else e.stdout if e.stdout else "Unknown error"
        print(f"❌ Failed to clone Space repository: {error_msg}")
        raise RuntimeError(f"Git clone failed: {error_msg}") from e
    
    # Get exclusion sets
    excluded_dirs = get_excluded_dirs()
    excluded_files = get_excluded_files()
    
>>>>>>> origin/dev
    # Remove all existing files in HF Space (except .git)
    print("🧹 Cleaning existing files...")
    for item in Path(local_dir).iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
<<<<<<< HEAD

=======
    
>>>>>>> origin/dev
    # Copy files from repository root
    print("📦 Copying files...")
    repo_root = Path(".")
    files_copied = 0
    dirs_copied = 0
<<<<<<< HEAD

=======
    
>>>>>>> origin/dev
    for item in repo_root.rglob("*"):
        # Skip if in .git directory
        if ".git" in item.parts:
            continue
<<<<<<< HEAD

        # Skip if in hf_space directory (the cloned Space directory)
        if "hf_space" in item.parts:
            continue

        # Skip if should be excluded
        if should_exclude(item, excluded_dirs, excluded_files):
            continue

=======
        
        # Skip if should be excluded
        if should_exclude(item, excluded_dirs, excluded_files):
            continue
        
>>>>>>> origin/dev
        # Calculate relative path
        try:
            rel_path = item.relative_to(repo_root)
        except ValueError:
            # Item is outside repo root, skip
            continue
<<<<<<< HEAD

        # Skip if in excluded directory
        if any(part in excluded_dirs for part in rel_path.parts):
            continue

        # Destination path
        dest_path = Path(local_dir) / rel_path

        # Create parent directories
        dest_path.parent.mkdir(parents=True, exist_ok=True)

=======
        
        # Skip if in excluded directory
        if any(part in excluded_dirs for part in rel_path.parts):
            continue
        
        # Destination path
        dest_path = Path(local_dir) / rel_path
        
        # Create parent directories
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
>>>>>>> origin/dev
        # Copy file or directory
        if item.is_file():
            shutil.copy2(item, dest_path)
            files_copied += 1
        elif item.is_dir():
            # Directory will be created by parent mkdir, but we track it
            dirs_copied += 1
<<<<<<< HEAD

    print(f"✅ Copied {files_copied} files and {dirs_copied} directories")

    # Commit and push changes using git
    print("💾 Committing changes...")

    # Change to the Space directory
    original_cwd = os.getcwd()
    os.chdir(local_dir)

=======
    
    print(f"✅ Copied {files_copied} files and {dirs_copied} directories")
    
    # Commit and push changes using git
    print("💾 Committing changes...")
    
    # Change to the Space directory
    original_cwd = os.getcwd()
    os.chdir(local_dir)
    
>>>>>>> origin/dev
    try:
        # Configure git user (required for commit)
        subprocess.run(
            ["git", "config", "user.name", "github-actions[bot]"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
            check=True,
            capture_output=True,
        )
<<<<<<< HEAD

=======
        
>>>>>>> origin/dev
        # Add all files
        subprocess.run(
            ["git", "add", "."],
            check=True,
            capture_output=True,
        )
<<<<<<< HEAD

        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
        )

=======
        
        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        
>>>>>>> origin/dev
        if result.stdout.strip():
            # There are changes, commit and push
            subprocess.run(
                ["git", "commit", "-m", "Deploy to Hugging Face Space [skip ci]"],
                check=True,
                capture_output=True,
            )
            print("📤 Pushing to Hugging Face Space...")
<<<<<<< HEAD
            # Ensure remote URL uses credential helper (not token in URL)
            subprocess.run(
                ["git", "remote", "set-url", "origin", f"https://huggingface.co/spaces/{repo_id}"],
                check=True,
                capture_output=True,
            )
=======
>>>>>>> origin/dev
            subprocess.run(
                ["git", "push"],
                check=True,
                capture_output=True,
            )
            print("✅ Deployment complete!")
        else:
            print("ℹ️  No changes to commit (repository is up to date)")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else (e.stdout if e.stdout else str(e))
        if isinstance(error_msg, bytes):
            error_msg = error_msg.decode("utf-8", errors="replace")
        if "nothing to commit" in error_msg.lower():
            print("ℹ️  No changes to commit (repository is up to date)")
        else:
            print(f"⚠️  Error during git operations: {error_msg}")
            raise RuntimeError(f"Git operation failed: {error_msg}") from e
    finally:
        # Return to original directory
        os.chdir(original_cwd)
<<<<<<< HEAD

        # Clean up credential store for security
        try:
            if credential_store.exists():
                credential_store.unlink()
        except Exception:
            # Ignore cleanup errors
            pass

=======
    
>>>>>>> origin/dev
    print(f"🎉 Successfully deployed to: https://huggingface.co/spaces/{repo_id}")


if __name__ == "__main__":
    deploy_to_hf_space()
<<<<<<< HEAD
=======

>>>>>>> origin/dev
