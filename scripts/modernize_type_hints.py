#!/usr/bin/env python3
"""
Modernize Python Type Hints Script

Converts deprecated typing imports to modern Python 3.10+ syntax:
- List[X] -> list[X]
- Dict[K, V] -> dict[K, V]
- Set[X] -> set[X]
- Tuple[X, Y] -> tuple[X, Y]
- Optional[X] -> X | None

Also handles:
- Import cleanup (removes unused imports)
- Sorts imports with isort
- datetime.UTC modernization
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class TypeHintModernizer:
    """Modernizes type hints in Python files"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.files_modified = 0
        self.files_checked = 0

        # Patterns for type hint replacements
        self.type_replacements = {
            r'\bList\[': 'list[',
            r'\bDict\[': 'dict[',
            r'\bSet\[': 'set[',
            r'\bTuple\[': 'tuple[',
        }

        # Optional pattern needs special handling: Optional[X] -> X | None
        self.optional_pattern = re.compile(r'Optional\[([^\]]+)\]')

        # Imports to remove from typing module
        self.deprecated_imports = {
            'List', 'Dict', 'Set', 'Tuple', 'Optional'
        }

    def modernize_file(self, file_path: Path) -> bool:
        """
        Modernize type hints in a single file.

        Returns:
            True if file was modified, False otherwise
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content

            # Step 1: Replace type annotations
            content = self._replace_type_annotations(content)

            # Step 2: Handle Optional[X] -> X | None
            content = self._replace_optional(content)

            # Step 3: Clean up imports
            content = self._cleanup_imports(content)

            # Step 4: Fix datetime.UTC if needed
            content = self._fix_datetime_utc(content)

            # Step 5: Add future annotations if needed
            if self._needs_future_annotations(content) and not self._has_future_annotations(content):
                content = self._add_future_annotations(content)

            # Check if content changed
            if content != original_content:
                if not self.dry_run:
                    file_path.write_text(content, encoding='utf-8')
                self.files_modified += 1
                return True

            return False

        except Exception as e:
            print(f"Error processing {file_path}: {e}", file=sys.stderr)
            return False

    def _replace_type_annotations(self, content: str) -> str:
        """Replace List, Dict, Set, Tuple with lowercase versions"""
        for old_pattern, new_text in self.type_replacements.items():
            content = re.sub(old_pattern, new_text, content)
        return content

    def _replace_optional(self, content: str) -> str:
        """Replace Optional[X] with X | None"""

        def replace_optional_match(match):
            inner_type = match.group(1)
            # Handle nested optionals and complex types
            return f"{inner_type} | None"

        # Replace Optional recursively
        while self.optional_pattern.search(content):
            content = self.optional_pattern.sub(replace_optional_match, content)

        return content

    def _cleanup_imports(self, content: str) -> str:
        """Remove unused typing imports and clean up import statements"""
        lines = content.split('\n')
        new_lines = []

        for line in lines:
            # Check if this is a typing import line
            if re.match(r'^from typing import', line):
                # Extract imported items
                import_match = re.search(r'from typing import (.+)', line)
                if import_match:
                    imports_str = import_match.group(1)

                    # Handle multi-line imports with parentheses
                    if '(' in imports_str and ')' not in imports_str:
                        # Multi-line import, skip for now (complex case)
                        new_lines.append(line)
                        continue

                    # Split imports and filter out deprecated ones
                    imports = [imp.strip() for imp in imports_str.split(',')]

                    # Keep only non-deprecated imports
                    kept_imports = []
                    for imp in imports:
                        # Remove comments and clean
                        imp_clean = imp.split('#')[0].strip()
                        if imp_clean and imp_clean not in self.deprecated_imports:
                            kept_imports.append(imp_clean)

                    # Reconstruct import line
                    if kept_imports:
                        if len(kept_imports) == 1:
                            new_lines.append(f"from typing import {kept_imports[0]}")
                        else:
                            new_lines.append(f"from typing import {', '.join(kept_imports)}")
                    # else: skip the line entirely (all imports were deprecated)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        return '\n'.join(new_lines)

    def _fix_datetime_utc(self, content: str) -> str:
        """Fix datetime.UTC imports and usage"""

        # Check if file uses datetime
        if 'datetime' not in content:
            return content

        # Fix import: from datetime import timezone -> from datetime import UTC
        # Only if timezone.utc is used
        if 'timezone.utc' in content or 'timezone.UTC' in content:
            # Replace import
            content = re.sub(
                r'from datetime import (.*)timezone(.*)',
                lambda m: f"from datetime import {m.group(1)}UTC{m.group(2)}",
                content
            )

            # Replace usage
            content = content.replace('timezone.utc', 'UTC')
            content = content.replace('timezone.UTC', 'UTC')

        return content

    def _needs_future_annotations(self, content: str) -> bool:
        """Check if file uses | union syntax in type annotations"""
        return bool(re.search(r':\s*\w+\s*\|\s*(\w+|None)', content))

    def _has_future_annotations(self, content: str) -> bool:
        """Check if file already has future annotations import"""
        return 'from __future__ import annotations' in content

    def _add_future_annotations(self, content: str) -> str:
        """Add future annotations import to the top of the file"""
        lines = content.split('\n')

        # Find the insertion point (after docstring, before other imports)
        insert_at = 0
        in_docstring = False
        docstring_char = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Handle module docstring
            if i == 0 or (i == 1 and not lines[0].strip()):
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    docstring_char = stripped[:3]
                    if stripped.count(docstring_char) >= 2:  # Single line docstring
                        insert_at = i + 1
                        continue
                    else:
                        in_docstring = True
                        continue

            if in_docstring:
                if docstring_char in line:
                    in_docstring = False
                    insert_at = i + 1
                continue

            # If we see an import or code, insert before it
            if stripped and not stripped.startswith('#'):
                if not stripped.startswith('"""') and not stripped.startswith("'''"):
                    insert_at = i
                    break

        # Insert the future import
        lines.insert(insert_at, 'from __future__ import annotations')
        lines.insert(insert_at + 1, '')  # Add blank line

        return '\n'.join(lines)

    def process_directory(self, directory: Path, exclude_patterns: List[str] = None) -> None:
        """
        Process all Python files in a directory recursively.

        Args:
            directory: Root directory to process
            exclude_patterns: List of patterns to exclude (e.g., ['test_', '__pycache__'])
        """
        exclude_patterns = exclude_patterns or [
            '__pycache__',
            '.venv',
            'venv',
            '.git',
            'node_modules',
            '.pytest_cache',
            'dist',
            'build',
            '*.egg-info'
        ]

        print(f"Processing directory: {directory}")
        print(f"Dry run: {self.dry_run}")
        print("-" * 60)

        for py_file in directory.rglob('*.py'):
            # Check exclusions
            if any(pattern in str(py_file) for pattern in exclude_patterns):
                continue

            self.files_checked += 1

            if self.modernize_file(py_file):
                status = "[DRY RUN] Would modify" if self.dry_run else "Modified"
                print(f"{status}: {py_file.relative_to(directory)}")

        print("-" * 60)
        print(f"Files checked: {self.files_checked}")
        print(f"Files {'would be ' if self.dry_run else ''}modified: {self.files_modified}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Modernize Python type hints to Python 3.10+ syntax",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (preview changes)
  python modernize_type_hints.py --dry-run

  # Apply changes to entire project
  python modernize_type_hints.py

  # Apply changes to specific directory
  python modernize_type_hints.py --directory src/fastmcp/auth

  # Apply changes with custom excludes
  python modernize_type_hints.py --exclude "test_*" --exclude "migrations"
        """
    )

    parser.add_argument(
        '--directory',
        type=Path,
        default=Path.cwd() / 'src',
        help='Directory to process (default: ./src)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )

    parser.add_argument(
        '--exclude',
        action='append',
        help='Patterns to exclude (can be specified multiple times)'
    )

    args = parser.parse_args()

    # Validate directory
    if not args.directory.exists():
        print(f"Error: Directory not found: {args.directory}", file=sys.stderr)
        sys.exit(1)

    if not args.directory.is_dir():
        print(f"Error: Not a directory: {args.directory}", file=sys.stderr)
        sys.exit(1)

    # Run modernizer
    modernizer = TypeHintModernizer(dry_run=args.dry_run)
    modernizer.process_directory(args.directory, exclude_patterns=args.exclude)

    # Run ruff to fix remaining issues
    if not args.dry_run and modernizer.files_modified > 0:
        print("\nRunning ruff to fix import sorting...")
        import subprocess
        try:
            subprocess.run(
                ['ruff', 'check', '--fix', '--select', 'I001', str(args.directory)],
                check=False
            )
            print("✅ Import sorting complete")
        except FileNotFoundError:
            print("⚠️  ruff not found, skipping import sorting")


if __name__ == '__main__':
    main()
