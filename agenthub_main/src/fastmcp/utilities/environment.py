"""Environment detection utilities for FastMCP."""

from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Literal

EnvironmentType = Literal["docker", "local"]


def detect_environment() -> EnvironmentType:
    """
    Detect if the application is running in Docker or locally.

    Returns:
        "docker" if running in Docker container, "local" otherwise
    """
    # Check for Docker-specific indicators
    docker_indicators = [
        # Check if running in Docker container (most reliable)
        os.path.exists("/.dockerenv"),
        # Check for Docker cgroups (fallback)
        _has_docker_cgroups(),
        # Check for specific environment variable we set in Dockerfile
        os.environ.get("CONTAINER_ENV") == "docker",
        # Check hostname pattern (containers often have random hostnames)
        _is_container_hostname(),
    ]

    return "docker" if any(docker_indicators) else "local"


def _has_docker_cgroups() -> bool:
    """Check if running inside Docker by examining cgroups."""
    try:
        with open("/proc/1/cgroup") as f:
            content = f.read()
            return "docker" in content or "containerd" in content
    except (FileNotFoundError, PermissionError, OSError):
        return False


def _is_container_hostname() -> bool:
    """Check if hostname suggests container environment."""
    try:
        hostname = platform.node()
        # Container hostnames are often short random strings
        # This is a heuristic and may have false positives
        return len(hostname) == 12 and hostname.islower()
    except Exception:
        return False


def get_log_directory(environment: EnvironmentType | None = None) -> Path:
    """
    Get the appropriate log directory based on the environment.

    Args:
        environment: Override environment detection (for testing)

    Returns:
        Path to the log directory
    """
    if environment is None:
        environment = detect_environment()

    if environment == "docker":
        # In Docker, logs should go to mounted volume
        return Path("/data/logs")
    else:
        # In local development, logs go to project's logs directory
        current = Path.cwd()

        # Priority 1: Check for .git directory (definitive project root indicator)
        # This ensures consistency regardless of where the server starts
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists():
                return parent / "logs"

        # Priority 2: Fallback to other project indicators if .git not found
        # (rare case for projects not using git)
        fallback_indicators = ["pyproject.toml", "CLAUDE.md", "docker-system"]

        for parent in [current] + list(current.parents):
            if any((parent / indicator).exists() for indicator in fallback_indicators):
                return parent / "logs"

        # Fallback to current directory logs folder
        return current / "logs"


def ensure_log_directory_exists(log_dir: Path | None = None) -> Path:
    """
    Ensure the log directory exists and is writable.

    Args:
        log_dir: Optional override for log directory

    Returns:
        Path to the ensured log directory

    Raises:
        OSError: If directory cannot be created or is not writable
    """
    if log_dir is None:
        log_dir = get_log_directory()

    # Create directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)

    # Test if directory is writable
    test_file = log_dir / ".write_test"
    try:
        test_file.touch()
        test_file.unlink()
    except (PermissionError, OSError) as e:
        raise OSError(f"Log directory {log_dir} is not writable: {e}") from e

    return log_dir


def get_log_file_path(filename: str = "agenthub.log", log_dir: Path | None = None) -> Path:
    """
    Get the full path for a log file.

    Args:
        filename: Name of the log file
        log_dir: Optional override for log directory

    Returns:
        Full path to the log file
    """
    if log_dir is None:
        log_dir = ensure_log_directory_exists()

    return log_dir / filename


def get_environment_info() -> dict:
    """
    Get comprehensive environment information for debugging.

    Returns:
        Dictionary with environment details
    """
    env_type = detect_environment()
    log_dir = get_log_directory()

    return {
        "environment_type": env_type,
        "log_directory": str(log_dir),
        "log_directory_exists": log_dir.exists(),
        "log_directory_writable": log_dir.is_dir() and os.access(log_dir, os.W_OK) if log_dir.exists() else False,
        "platform": platform.platform(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
        "cwd": str(Path.cwd()),
        "docker_env_exists": os.path.exists("/.dockerenv"),
        "container_env_var": os.environ.get("CONTAINER_ENV"),
        "relevant_env_vars": {
            key: value for key, value in os.environ.items()
            if any(keyword in key.lower() for keyword in ["docker", "container", "log"])
        }
    }