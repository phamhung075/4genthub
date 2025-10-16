#!/usr/bin/env python3
"""
Mark Obsolete Documentation Script
Renames low-value/outdated documentation with .obsolete extension
to keep ai_docs/ clean and focused on valuable AI knowledge.

Philosophy: AI docs should contain ONLY important, current knowledge.
Everything else is noise that degrades AI performance.
"""

import json
import os
from pathlib import Path
from datetime import datetime
import re

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
AI_DOCS = PROJECT_ROOT / "ai_docs"
INDEX_FILE = AI_DOCS / "index.json"

# Categories to analyze
CATEGORIES_TO_AUDIT = [
    "reports-status",
    "issues",
    "_workplace",
    "troubleshooting-guides",
    "migration-guides"
]

def load_index():
    """Load the documentation index."""
    with open(INDEX_FILE, 'r') as f:
        return json.load(f)

def is_valuable_doc(file_path, file_info):
    """
    Determine if a document provides valuable AI knowledge.

    KEEP (Valuable):
    - Current architecture documentation
    - Active troubleshooting guides
    - Setup and integration guides
    - Core concept explanations
    - Best practices and patterns

    MARK OBSOLETE (Low value):
    - Old status reports (> 30 days)
    - Resolved issues documentation
    - Migration guides for old versions
    - Duplicate content
    - Test results and temp analysis
    - Work-in-progress documents
    """
    path = Path(file_path)
    content_path = AI_DOCS / file_path

    # Already obsolete
    if path.suffix == '.obsolete' or '_obsolete_docs' in str(path):
        return True

    # Check by category first
    category = path.parts[0] if path.parts else ""

    # Status reports - keep only critical architectural reports
    if category == "reports-status":
        # Keep only these specific valuable reports
        keeper_reports = [
            'architecture-accuracy-audit',
            'duplicate-content-analysis',
            'documentation-consolidation-plan',
            'documentation-audit-summary'
        ]
        # Check if this is a keeper report
        is_keeper = any(keeper in path.name.lower() for keeper in keeper_reports)
        if is_keeper:
            return True
        # Everything else in reports-status is obsolete (old status reports)
        return False

    # Issues - mark resolved/old issues obsolete
    if category == "issues":
        if content_path.exists():
            try:
                with open(content_path, 'r') as f:
                    content = f.read(1000)
                    # Mark obsolete if resolved/closed/fixed
                    if any(term in content.lower() for term in ['status: resolved', 'status: closed', 'status: fixed', 'issue resolved']):
                        return False
            except:
                pass
        return True

    # Workplace - typically temporary work documents
    if category == "_workplace":
        # Check if it's final documentation or WIP
        if 'wip' in path.name.lower() or 'temp' in path.name.lower() or 'draft' in path.name.lower():
            return False
        # Check for results/logs files
        if 'results' in path.name.lower() or 'log' in path.name.lower():
            return False
        return True  # Keep if might be reference

    # Migration guides - keep only for current/recent versions
    if category == "migration-guides":
        # Extract version numbers if present
        version_pattern = r'v?(\d+)\.(\d+)\.(\d+)'
        matches = re.findall(version_pattern, path.name.lower())
        if matches:
            # Keep only guides for v0.0.4+ (current is ~0.0.5)
            for match in matches:
                major, minor, patch = map(int, match)
                if major == 0 and minor == 0 and patch < 4:
                    return False  # Old version
        return True

    # Troubleshooting - keep active guides, mark resolved issues obsolete
    if category == "troubleshooting-guides":
        if content_path.exists():
            try:
                with open(content_path, 'r') as f:
                    content = f.read(1000)
                    # If marked as resolved/obsolete in content
                    if any(term in content.lower() for term in ['no longer relevant', 'obsolete', 'resolved in version']):
                        return False
            except:
                pass
        return True

    # Testing-QA - keep guides, mark iteration summaries obsolete
    if category == "testing-qa":
        # Mark old iteration summaries as obsolete (historical records)
        if 'iteration' in path.name.lower() or 'test-fix-iteration' in path.name.lower():
            return False  # These are historical records, not current knowledge
        # Keep testing guides and current documentation
        return True

    # Default: keep important categories
    important_categories = [
        "authentication", "api-integration", "core-architecture",
        "development-guides", "setup-guides",
        "context-system", "product-requirements", "claude-code",
        "operations", "integration-guides"
    ]

    if category in important_categories:
        return True

    # Unknown category - keep by default (manual review needed)
    return True

def mark_obsolete(file_path, reason):
    """Mark a file as obsolete by adding .obsolete extension."""
    source = AI_DOCS / file_path
    if not source.exists():
        print(f"  ⚠️  File not found: {file_path}")
        return None

    # Add .obsolete extension
    dest = source.with_suffix(source.suffix + '.obsolete')

    # Rename the file
    source.rename(dest)
    new_path = dest.relative_to(AI_DOCS)

    print(f"  ✅ Marked obsolete: {file_path}")
    print(f"     → {new_path}")
    print(f"     Reason: {reason}")

    return str(new_path)

def scan_and_mark_obsolete():
    """Scan documentation and mark low-value files as obsolete."""
    print("🔍 Loading documentation index...")
    index = load_index()

    obsolete_marked = []
    kept_files = []

    # Analyze all categories
    print("\n📂 Analyzing documentation value...")
    categories = index.get("categories", {})

    for category_path, category_info in categories.items():
        # Skip already obsolete
        if '_obsolete_docs' in category_path:
            continue

        files = category_info.get("files", [])
        print(f"\n📁 Checking: {category_path}/ ({len(files)} files)")

        for file_info in files:
            file_path = file_info["path"]

            if is_valuable_doc(file_path, file_info):
                kept_files.append(file_path)
                print(f"  ✓ Keep: {file_path}")
            else:
                # Determine reason
                path = Path(file_path)
                category = path.parts[0] if path.parts else ""

                reason_map = {
                    "reports-status": "Old status report (>30 days or one-time analysis)",
                    "issues": "Resolved issue documentation",
                    "_workplace": "Temporary work document/results file",
                    "migration-guides": "Migration guide for old version",
                    "troubleshooting-guides": "Resolved troubleshooting issue"
                }

                reason = reason_map.get(category, "Low-value or outdated documentation")
                new_path = mark_obsolete(file_path, reason)

                if new_path:
                    obsolete_marked.append({
                        "original_path": file_path,
                        "new_path": new_path,
                        "reason": reason
                    })

    # Summary
    print("\n" + "="*70)
    print(f"📊 CLEANUP SUMMARY")
    print("="*70)
    print(f"Files analyzed: {len(kept_files) + len(obsolete_marked)}")
    print(f"Valuable docs kept: {len(kept_files)}")
    print(f"Low-value docs marked obsolete: {len(obsolete_marked)}")

    if obsolete_marked:
        print(f"\n📝 Files Marked Obsolete (by category):")

        # Group by category
        by_category = {}
        for item in obsolete_marked:
            category = Path(item['original_path']).parts[0]
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(item)

        for category, items in sorted(by_category.items()):
            print(f"\n  {category}/ ({len(items)} files):")
            for item in items:
                print(f"    • {Path(item['original_path']).name}")
                print(f"      Reason: {item['reason']}")
    else:
        print("\n✅ No low-value documentation found!")

    print("\n💡 Next steps:")
    print("   1. Review marked .obsolete files")
    print("   2. Run: python .claude/hooks/utils/docs_indexer.py")
    print("   3. Update CHANGELOG.md with cleanup summary")
    print("\n📁 Obsolete files remain in place with .obsolete extension")
    print("   They can be manually deleted or moved to _obsolete_docs/ later")

    return obsolete_marked, kept_files

if __name__ == "__main__":
    print("🧹 Documentation Value Cleanup Tool")
    print("="*70)
    print("Philosophy: ai_docs should contain ONLY valuable AI knowledge")
    print("="*70)

    obsolete, kept = scan_and_mark_obsolete()

    print("\n✅ Value-based cleanup complete!")
    print(f"   Quality ratio: {len(kept)}/{len(kept) + len(obsolete)} files are valuable")
