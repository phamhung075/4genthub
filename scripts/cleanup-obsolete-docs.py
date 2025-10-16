#!/usr/bin/env python3
"""
Cleanup Obsolete Documentation Script
Compares ai_docs/index.json entries with actual system files
and moves obsolete documentation to _obsolete_docs folder.
"""

import json
import os
from pathlib import Path
from datetime import datetime
import shutil

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
AI_DOCS = PROJECT_ROOT / "ai_docs"
INDEX_FILE = AI_DOCS / "index.json"
OBSOLETE_DOCS = AI_DOCS / "_obsolete_docs"
ABSOLUTE_DOCS = AI_DOCS / "_absolute_docs"

def load_index():
    """Load the documentation index."""
    with open(INDEX_FILE, 'r') as f:
        return json.load(f)

def check_file_exists(documented_file):
    """Check if a documented file actually exists in the project."""
    file_path = PROJECT_ROOT / documented_file
    return file_path.exists()

def move_to_obsolete(doc_path, reason):
    """Move obsolete documentation to _obsolete_docs folder."""
    source = AI_DOCS / doc_path
    if not source.exists():
        print(f"  ⚠️  Doc file not found: {doc_path}")
        return None

    # Create timestamp-based subfolder in obsolete
    timestamp = datetime.now().strftime("%Y%m%d")
    dest_folder = OBSOLETE_DOCS / timestamp
    dest_folder.mkdir(parents=True, exist_ok=True)

    # Preserve relative path structure
    relative_path = source.relative_to(AI_DOCS)
    dest = dest_folder / relative_path
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Move the file
    shutil.move(str(source), str(dest))
    print(f"  ✅ Moved: {doc_path} -> {dest.relative_to(AI_DOCS)}")
    print(f"     Reason: {reason}")

    return str(dest.relative_to(AI_DOCS))

def scan_obsolete_docs():
    """Scan for obsolete documentation."""
    print("🔍 Loading documentation index...")
    index = load_index()

    obsolete_found = []

    # Check absolute_docs tracked files
    print("\n📋 Checking _absolute_docs tracked files...")
    tracked = index.get("absolute_docs", {}).get("tracked_files", {})

    for documented_file, info in tracked.items():
        if not check_file_exists(documented_file):
            print(f"\n❌ File not found: {documented_file}")
            doc_path = info.get("doc_path")
            if doc_path:
                new_location = move_to_obsolete(doc_path, f"Source file '{documented_file}' no longer exists")
                if new_location:
                    obsolete_found.append({
                        "documented_file": documented_file,
                        "doc_path": doc_path,
                        "new_location": new_location,
                        "reason": "source_file_missing"
                    })

    # Check all documentation categories
    print("\n📂 Checking documentation categories...")
    categories = index.get("categories", {})

    for category_path, category_info in categories.items():
        if category_path.startswith("_obsolete_docs"):
            # Skip already obsolete docs
            continue

        files = category_info.get("files", [])
        for file_info in files:
            doc_file_path = Path(file_info["path"])

            # For _absolute_docs, check if source exists
            if doc_file_path.parts[0] == "_absolute_docs" and len(doc_file_path.parts) > 1:
                # Extract the documented file path
                # Pattern: _absolute_docs/path/to/file.ext.md documents path/to/file.ext
                relative_parts = doc_file_path.parts[1:]  # Remove _absolute_docs

                if relative_parts[-1].endswith(".md"):
                    # Remove .md extension to get source file
                    source_parts = list(relative_parts)
                    source_parts[-1] = source_parts[-1][:-3]  # Remove .md

                    # Special case: f_index.md documents a folder
                    if source_parts[-1] == "f_index":
                        source_parts = source_parts[:-1]  # Just the folder

                    documented_file = "/".join(source_parts)

                    if documented_file and not check_file_exists(documented_file):
                        full_doc_path = file_info["path"]
                        print(f"\n❌ Source missing for doc: {full_doc_path}")
                        print(f"   Expected source: {documented_file}")

                        new_location = move_to_obsolete(full_doc_path, f"Source '{documented_file}' not found")
                        if new_location:
                            obsolete_found.append({
                                "documented_file": documented_file,
                                "doc_path": full_doc_path,
                                "new_location": new_location,
                                "reason": "source_missing_category_check"
                            })

    # Summary
    print("\n" + "="*60)
    print(f"📊 SUMMARY")
    print("="*60)
    print(f"Total obsolete docs found: {len(obsolete_found)}")

    if obsolete_found:
        print("\n📝 Obsolete Documentation Moved:")
        for item in obsolete_found:
            print(f"  • {item['doc_path']}")
            print(f"    → {item['new_location']}")
            print(f"    Reason: {item['reason']}")
    else:
        print("\n✅ No obsolete documentation found!")

    print("\n💡 Next step: Run the docs indexer to update index.json:")
    print("   python .claude/hooks/utils/docs_indexer.py")

    return obsolete_found

if __name__ == "__main__":
    print("🧹 Obsolete Documentation Cleanup Tool")
    print("="*60)

    # Ensure obsolete docs folder exists
    OBSOLETE_DOCS.mkdir(exist_ok=True)

    obsolete = scan_obsolete_docs()

    print("\n✅ Cleanup complete!")
