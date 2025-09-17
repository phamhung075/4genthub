#!/usr/bin/env python3
"""
Rebrand AgenthubMCP to agenthub across the entire codebase.
This script performs a comprehensive find and replace operation.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Define the project root
PROJECT_ROOT = Path("/home/daihungpham/__projects__/agentic-project")

# Define replacement patterns
REPLACEMENTS = [
    # Case-sensitive replacements
    ("AgenthubMCP", "agenthub"),
    ("Agenthub MCP", "agenthub"),
    ("DHAFNCK_MCP", "AGENTHUB"),
    ("agenthub_mcp", "agenthub"),
    ("agenthub-mcp", "agenthub"),
    ("agenthub", "agenthub"),
    ("Agenthub", "agenthub"),
    ("DHAFNCK", "AGENTHUB"),

    # Path replacements (already done via mv commands)
    # ("agenthub-frontend", "agenthub-frontend"),
    # ("agenthub_mcp_main", "agenthub_main"),
]

# Files and directories to skip
SKIP_PATTERNS = [
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.db",
    "*.sqlite",
    ".coverage",
    "htmlcov",
    "dist",
    "build",
    "*.egg-info",
    "scripts/rebrand_to_agenthub.py",  # Skip this script itself
]

def should_skip(path: Path) -> bool:
    """Check if a file or directory should be skipped."""
    path_str = str(path)
    for pattern in SKIP_PATTERNS:
        if pattern in path_str:
            return True
        if pattern.startswith("*") and path_str.endswith(pattern[1:]):
            return True
    return False

def is_text_file(path: Path) -> bool:
    """Check if a file is likely a text file."""
    text_extensions = [
        ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml",
        ".md", ".txt", ".sh", ".bash", ".zsh", ".fish",
        ".html", ".css", ".scss", ".sass", ".less",
        ".xml", ".toml", ".ini", ".cfg", ".conf",
        ".env", ".gitignore", ".dockerignore",
        "Dockerfile", "docker-compose",
    ]

    # Check by extension
    if any(str(path).endswith(ext) for ext in text_extensions):
        return True

    # Check for files without extension (like Dockerfile)
    if path.stem and not path.suffix:
        return True

    return False

def replace_in_file(file_path: Path, replacements: List[Tuple[str, str]]) -> int:
    """Replace all occurrences in a file. Returns number of replacements made."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, PermissionError):
        return 0

    original_content = content
    total_replacements = 0

    for old, new in replacements:
        # Count replacements
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            total_replacements += count

    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return total_replacements
        except PermissionError:
            print(f"Permission denied: {file_path}")
            return 0

    return 0

def main():
    """Main function to perform the rebranding."""
    print("🚀 Starting rebranding from AgenthubMCP to agenthub...")
    print(f"Project root: {PROJECT_ROOT}")

    total_files_processed = 0
    total_files_modified = 0
    total_replacements = 0

    # Walk through all files
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Filter out directories to skip
        dirs[:] = [d for d in dirs if not should_skip(Path(root) / d)]

        for file in files:
            file_path = Path(root) / file

            # Skip if should be skipped
            if should_skip(file_path):
                continue

            # Skip if not a text file
            if not is_text_file(file_path):
                continue

            total_files_processed += 1
            replacements_made = replace_in_file(file_path, REPLACEMENTS)

            if replacements_made > 0:
                total_files_modified += 1
                total_replacements += replacements_made
                relative_path = file_path.relative_to(PROJECT_ROOT)
                print(f"✅ Updated {relative_path} ({replacements_made} replacements)")

    print("\n" + "="*60)
    print("🎉 Rebranding Complete!")
    print(f"Files processed: {total_files_processed}")
    print(f"Files modified: {total_files_modified}")
    print(f"Total replacements: {total_replacements}")
    print("="*60)

    print("\n📋 Next steps:")
    print("1. Review the changes with 'git diff'")
    print("2. Update any environment variables in .env files")
    print("3. Update Docker container names if needed")
    print("4. Run tests to ensure everything works")
    print("5. Commit the changes")

if __name__ == "__main__":
    main()