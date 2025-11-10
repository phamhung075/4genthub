#!/usr/bin/env python3
"""
Modernize datetime timezone usage to Python 3.11+ UTC constant.

This script:
1. Finds all Python files using timezone.utc
2. Updates imports to use UTC from datetime module
3. Replaces all timezone.utc with UTC
4. Removes timezone import if no longer needed
"""

import re
from pathlib import Path


def process_file(file_path: Path) -> bool:
    """
    Process a single Python file to modernize datetime usage.

    Returns:
        bool: True if file was modified, False otherwise
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        # Check if file uses timezone.utc
        if 'timezone.utc' not in content:
            return False

        lines = content.split('\n')
        modified_lines = []
        imports_section_end = 0
        has_utc_import = False
        has_timezone_import = False
        datetime_import_line_idx = None

        # First pass: analyze imports
        for idx, line in enumerate(lines):
            # Track where imports end (first non-import, non-comment, non-blank line)
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('import') and not stripped.startswith('from'):
                if imports_section_end == 0:
                    imports_section_end = idx

            # Check for existing imports
            if 'from datetime import' in line:
                datetime_import_line_idx = idx
                if 'UTC' in line or ', UTC' in line or 'UTC,' in line:
                    has_utc_import = True
                if 'timezone' in line:
                    has_timezone_import = True

        # Second pass: modify imports and content
        for idx, line in enumerate(lines):
            modified_line = line

            # Update datetime import line to add UTC
            if idx == datetime_import_line_idx and not has_utc_import:
                # Add UTC to the import
                if 'from datetime import' in line:
                    # Handle various import formats
                    if ' import datetime' in line and ', ' not in line.split('import')[1]:
                        # from datetime import datetime
                        modified_line = line.replace('from datetime import datetime', 'from datetime import UTC, datetime')
                    elif 'import (' in line:
                        # Multi-line import - just add UTC after opening paren
                        modified_line = line.replace('import (', 'import (\n    UTC,')
                    else:
                        # Single line with multiple imports - add UTC at the beginning
                        parts = line.split('import ')
                        if len(parts) == 2:
                            imports = parts[1].strip()
                            modified_line = f"{parts[0]}import UTC, {imports}"

            # Replace timezone.utc with UTC
            if 'timezone.utc' in modified_line:
                modified_line = modified_line.replace('timezone.utc', 'UTC')

            modified_lines.append(modified_line)

        # Third pass: clean up timezone import if only used for .utc
        final_content = '\n'.join(modified_lines)

        # Check if timezone is still used for anything other than .utc
        if has_timezone_import:
            # Remove timezone from content temporarily to check usage
            temp_content = final_content.replace(', timezone', '').replace('timezone,', '').replace('timezone', '')
            # If no other usage of timezone module exists, we can remove it
            # But keep it if there are timezone class usages
            if 'timezone(' not in final_content and 'timezone.' not in final_content:
                # Remove timezone from imports
                final_content = re.sub(r',\s*timezone\b', '', final_content)
                final_content = re.sub(r'\btimezone\s*,', '', final_content)
                final_content = re.sub(r'from datetime import timezone\s*\n', '', final_content)

        # Check if content actually changed
        if final_content != original_content:
            file_path.write_text(final_content, encoding='utf-8')
            return True

        return False

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False


def main():
    """Main function to process all Python files."""
    # Start from src directory
    src_dir = Path(__file__).parent.parent / 'src'

    if not src_dir.exists():
        print(f"❌ Source directory not found: {src_dir}")
        return

    print("🔍 Finding Python files with timezone.utc usage...")
    print(f"📁 Scanning: {src_dir}")
    print()

    # Find all Python files with timezone.utc
    python_files = list(src_dir.rglob('*.py'))
    files_to_process = []

    for py_file in python_files:
        try:
            if 'timezone.utc' in py_file.read_text(encoding='utf-8'):
                files_to_process.append(py_file)
        except:
            continue

    print(f"📊 Found {len(files_to_process)} files with timezone.utc")
    print()

    if not files_to_process:
        print("✅ No files to process!")
        return

    # Process each file
    modified_count = 0
    for py_file in files_to_process:
        relative_path = py_file.relative_to(src_dir.parent)
        if process_file(py_file):
            print(f"✅ Modified: {relative_path}")
            modified_count += 1
        else:
            print(f"⏭️  Skipped: {relative_path}")

    print()
    print(f"{'='*60}")
    print("✨ Modernization Complete!")
    print(f"📝 Modified {modified_count} files")
    print("🎯 Changed timezone.utc → UTC (Python 3.11+ modern syntax)")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
