#!/usr/bin/env python3
"""
Complete the rebranding from agenthub to agenthub for remaining files.
This script handles SQL files and other specific file types.
"""

import os
from pathlib import Path

# Define the project root
PROJECT_ROOT = Path("/home/daihungpham/__projects__/agentic-project")

# Files that still need updating
FILES_TO_UPDATE = [
    "docker-system/docker/Dockerfile.backend.production",
    "docker-system/docker/Dockerfile.frontend.dev",
    "docker-system/docker/Dockerfile.frontend.production",
    "docker-system/docker/Dockerfile.frontend",
    ".github/workflows/test_coverage.yml",
    ".github/workflows/production-deployment.yml",
    "scripts/deployment/force-caprover-rebuild.sh",
    "scripts/force-caprover-rebuild.sh",
    "agenthub_main/scripts/init.sql",
    "docker-system/init-postgres-production.sql",
    "agenthub_main/scripts/supabase_complete_wipe.sql",
    "agenthub_main/scripts/supabase_data_cleanup.sql",
    "agenthub_main/config/keycloak_service_account.sample",
    "agenthub_main/.github/workflows/deploy-mvp.yml",
    "agenthub_main/.github/workflows/production-deployment.yml",
]

# Define replacement patterns
REPLACEMENTS = [
    # Case-sensitive replacements
    ("AgenthubMCP", "agenthub"),
    ("agenthub_mcp", "agenthub"),
    ("agenthub-mcp", "agenthub"),
    ("agenthub_user", "agenthub_user"),
    ("agenthub-frontend", "agenthub-frontend"),
    ("agenthub_mcp_main", "agenthub_main"),
    ("agenthub", "agenthub"),
    ("Agenthub", "agenthub"),
    ("DHAFNCK", "AGENTHUB"),
]

def replace_in_file(file_path: Path):
    """Replace all occurrences in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, PermissionError, FileNotFoundError) as e:
        print(f"❌ Error reading {file_path}: {e}")
        return False

    original_content = content
    for old, new in REPLACEMENTS:
        content = content.replace(old, new)

    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Updated {file_path}")
            return True
        except PermissionError as e:
            print(f"❌ Permission denied writing {file_path}: {e}")
            return False
    else:
        print(f"ℹ️  No changes needed for {file_path}")
        return False

def main():
    """Main function to complete the rebranding."""
    print("🚀 Completing rebranding from agenthub to agenthub...")
    print(f"Project root: {PROJECT_ROOT}")
    print()

    updated_count = 0
    error_count = 0

    for file_relative in FILES_TO_UPDATE:
        file_path = PROJECT_ROOT / file_relative
        if file_path.exists():
            if replace_in_file(file_path):
                updated_count += 1
        else:
            print(f"⚠️  File not found: {file_path}")
            error_count += 1

    print("\n" + "="*60)
    print("🎉 Rebranding Complete!")
    print(f"Files updated: {updated_count}")
    if error_count > 0:
        print(f"Files not found: {error_count}")
    print("="*60)

if __name__ == "__main__":
    main()