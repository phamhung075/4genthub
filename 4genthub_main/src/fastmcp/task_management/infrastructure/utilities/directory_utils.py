"""Directory Utilities

Infrastructure utilities for directory management following DDD principles.
"""

from pathlib import Path
import os
from typing import Optional

# Removed problematic tool_path import


def _find_project_root() -> Path:
    """Find project root by looking for 4genthub_main directory"""
    current_path = Path(__file__).resolve()
    
    # Walk up the directory tree looking for 4genthub_main
    while current_path.parent != current_path:
        if (current_path / "4genthub_main").exists():
            return current_path
        current_path = current_path.parent
    
    # If not found, use current working directory as fallback
    cwd = Path.cwd()
    if (cwd / "4genthub_main").exists():
        return cwd
        
    # Last resort - use the directory containing 4genthub_main
    current_path = Path(__file__).resolve()
    while current_path.parent != current_path:
        if current_path.name == "4genthub_main":
            return current_path.parent
        current_path = current_path.parent
    
    # Absolute fallback
    # Use environment variable or default data path
    data_path = os.environ.get('4GENTHUB_DATA_PATH', '/data')
    # If running in development, try to find project root
    if not os.path.exists(data_path):
        # Try current working directory
        cwd = Path.cwd()
        if (cwd / "4genthub_main").exists():
            return cwd
        # Try parent directories
        current = Path(__file__).resolve()
        while current.parent != current:
            if (current / "4genthub_main").exists():
                return current
            current = current.parent
        # Fall back to temp directory for safety
        return Path("/tmp/4genthub_project")
    return Path(data_path)


def ensure_brain_dir(brain_dir: Optional[str] = None) -> Path:
    """
    Ensure brain directory exists.
    
    This is an infrastructure utility function that handles file system paths
    and directory creation concerns.
    
    Args:
        brain_dir: Optional path to brain directory
        
    Returns:
        Path to the brain directory
    """
    if brain_dir is None:
        project_root = _find_project_root()
        brain_dir = project_root / ".cursor" / "brain"
    else:
        brain_dir = Path(brain_dir)
    
    brain_dir.mkdir(parents=True, exist_ok=True)
    return brain_dir