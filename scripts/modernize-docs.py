#!/usr/bin/env python3
"""
Automated Documentation Modernization Script
Updates all active ai_docs files to current architecture standards.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
AI_DOCS = PROJECT_ROOT / "ai_docs"

# Architecture modernization patterns
REPLACEMENTS = [
    # Python version updates
    (r'Python 3\.12\.\d+', 'Python 3.14.0'),
    (r'Python 3\.12', 'Python 3.14.0'),
    (r'python 3\.12', 'Python 3.14.0'),
    (r'py3\.12', 'Python 3.14.0'),

    # PostgreSQL version updates
    (r'PostgreSQL 15', 'PostgreSQL 18'),
    (r'postgres:15', 'postgres:18-alpine'),

    # DDD Phase updates
    (r'DDD Phase [1-7](?!\d)', 'DDD Phase 8'),
    (r'Phase [1-7] of DDD', 'DDD Phase 8'),

    # React/Vite updates
    (r'React 18\.\d+', 'React 19.x'),
    (r'React 18', 'React 19.x'),
    (r'Vite [1-6]\.\d+', 'Vite 7.x'),
    (r'Vite [1-6]', 'Vite 7.x'),

    # TypeScript updates
    (r'TypeScript 5\.\d+', 'TypeScript 4.x'),

    # YAML config references (legacy)
    (r'YAML configuration files?', 'Dynamic Tool Enforcement v2.0 (response-based permissions)'),
    (r'\.yaml config', 'dynamic configuration from call_agent response'),

    # Event System
    (r'(?<!Event)EventBus(?! pattern)', 'EventBus (with EventQueue and EventWorker)'),

    # Generic improvements
    (r'in the file `([^`]+)`(?! at lines?)', r'in `\1` (see file for specific lines)'),
]

# Patterns to add if missing
ADDITIONS = {
    'python_version': 'Python 3.14.0+',
    'ddd_phase': 'DDD Phase 8 Complete',
    'event_system': 'Event System (EventQueue, EventBus, EventWorker)',
    'dynamic_tools': 'Dynamic Tool Enforcement v2.0',
}

def should_process_file(file_path: Path) -> bool:
    """Check if file should be processed."""
    # Skip obsolete files
    if '.obsolete' in str(file_path):
        return False

    # Skip certain directories
    skip_dirs = {'_obsolete_docs', 'assets'}
    if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
        return False

    # Only process .md files
    return file_path.suffix == '.md'

def modernize_content(content: str, file_path: Path) -> Tuple[str, List[str]]:
    """Apply modernization patterns to content."""
    changes = []
    original_content = content

    # Apply replacement patterns
    for pattern, replacement in REPLACEMENTS:
        matches = re.findall(pattern, content)
        if matches:
            content = re.sub(pattern, replacement, content)
            changes.append(f"Updated: {pattern[:50]}... → {replacement[:50]}")

    # Check for missing modern references
    if 'Python 3.14' not in content and 'python' in content.lower():
        # File discusses Python but doesn't mention 3.14
        changes.append("Note: Python version may need manual review")

    if 'DDD Phase 8' not in content and 'ddd' in content.lower():
        changes.append("Note: DDD Phase may need manual review")

    return content, changes

def process_file(file_path: Path) -> Dict[str, any]:
    """Process a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        updated_content, changes = modernize_content(original_content, file_path)

        if updated_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            return {
                'file': str(file_path.relative_to(AI_DOCS)),
                'status': 'updated',
                'changes': changes
            }
        else:
            return {
                'file': str(file_path.relative_to(AI_DOCS)),
                'status': 'no_changes',
                'changes': []
            }

    except Exception as e:
        return {
            'file': str(file_path.relative_to(AI_DOCS)),
            'status': 'error',
            'error': str(e)
        }

def main():
    """Main execution."""
    print("🔄 AI Documentation Modernization Tool")
    print("=" * 70)
    print(f"Scanning: {AI_DOCS}")
    print()

    # Find all markdown files
    all_files = []
    for file_path in AI_DOCS.rglob("*.md"):
        if should_process_file(file_path):
            all_files.append(file_path)

    print(f"Found {len(all_files)} files to process")
    print()

    # Process files by folder
    results_by_folder = {}

    for file_path in sorted(all_files):
        folder = file_path.parent.relative_to(AI_DOCS)
        if folder not in results_by_folder:
            results_by_folder[folder] = []

        result = process_file(file_path)
        results_by_folder[folder].append(result)

    # Generate report
    print("📊 MODERNIZATION RESULTS")
    print("=" * 70)

    total_files = 0
    total_updated = 0
    total_errors = 0

    for folder, results in sorted(results_by_folder.items()):
        updated = sum(1 for r in results if r['status'] == 'updated')
        errors = sum(1 for r in results if r['status'] == 'error')

        total_files += len(results)
        total_updated += updated
        total_errors += errors

        status = "✅" if updated > 0 else "✓"
        print(f"\n{status} {folder}/ ({len(results)} files)")
        if updated > 0:
            print(f"   Updated: {updated} files")
            # Show sample changes from first updated file
            for r in results:
                if r['status'] == 'updated' and r['changes']:
                    print(f"   Sample changes: {r['changes'][0]}")
                    break
        if errors > 0:
            print(f"   ⚠️  Errors: {errors} files")

    print()
    print("=" * 70)
    print(f"📈 SUMMARY")
    print(f"Total files processed: {total_files}")
    print(f"Files updated: {total_updated}")
    print(f"Files unchanged: {total_files - total_updated - total_errors}")
    print(f"Errors: {total_errors}")
    print()

    if total_updated > 0:
        print("✅ Modernization complete!")
        print("Next: Review changes and update CHANGELOG.md")
    else:
        print("✅ All files already up to date!")

if __name__ == "__main__":
    main()
