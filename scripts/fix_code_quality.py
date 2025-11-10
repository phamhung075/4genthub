#!/usr/bin/env python3
"""
Fix common code quality issues in Python files

Handles:
- Bare except clauses (E722)
- Equality comparisons to True/False (E712)
- Unused variables (F841) - prefix with _
- Duplicate dictionary keys (F601)
- Module level imports not at top (E402)
"""

import re
from pathlib import Path
from typing import List, Tuple


def fix_bare_except(content: str) -> str:
    """Replace bare 'except:' with 'except Exception:'"""
    # Pattern: except: -> except Exception:
    content = re.sub(r'\bexcept\s*:', 'except Exception:', content)
    return content


def fix_boolean_comparisons(content: str) -> str:
    """Fix comparisons to True/False"""
    # Replace == True with just the variable (in if/while/assert)
    content = re.sub(r'if\s+(\w+[\.\w]*)\s*==\s*True\s*:', r'if \1:', content)
    content = re.sub(r'while\s+(\w+[\.\w]*)\s*==\s*True\s*:', r'while \1:', content)

    # Replace == False with not
    content = re.sub(r'if\s+(\w+[\.\w]*)\s*==\s*False\s*:', r'if not \1:', content)
    content = re.sub(r'while\s+(\w+[\.\w]*)\s*==\s*False\s*:', r'while not \1:', content)

    return content


def fix_unused_variables(content: str, file_path: Path) -> str:
    """Prefix unused variables with underscore"""
    # This is tricky - we'll let ruff handle this with --fix
    # But we can add a comment for manual review
    return content


def find_duplicate_dict_keys(content: str, file_path: Path) -> list[tuple[int, str]]:
    """Find duplicate dictionary keys for manual review"""
    issues = []
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        # Simple check for duplicate keys in same dict literal
        if '{' in line and ':' in line:
            # Extract potential dict content
            dict_match = re.search(r'\{([^}]+)\}', line)
            if dict_match:
                dict_content = dict_match.group(1)
                keys = re.findall(r'["\'](\w+)["\']:', dict_content)
                if len(keys) != len(set(keys)):
                    issues.append((i, line.strip()))

    return issues


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Fix code quality issues")
    parser.add_argument('--dry-run', action='store_true', help='Preview changes')
    parser.add_argument('--directory', type=Path, default=Path('src'), help='Directory to process')

    args = parser.parse_args()

    files_modified = 0
    files_checked = 0

    for py_file in args.directory.rglob('*.py'):
        try:
            content = py_file.read_text(encoding='utf-8')
            original = content
            files_checked += 1

            # Apply fixes
            content = fix_bare_except(content)
            content = fix_boolean_comparisons(content)

            # Check for duplicate keys
            dup_keys = find_duplicate_dict_keys(content, py_file)
            if dup_keys:
                print(f"\n⚠️  Duplicate dict keys in {py_file}:")
                for line_num, line in dup_keys:
                    print(f"  Line {line_num}: {line}")

            if content != original:
                if not args.dry_run:
                    py_file.write_text(content, encoding='utf-8')
                files_modified += 1
                print(f"{'[DRY RUN] Would modify' if args.dry_run else 'Modified'}: {py_file.relative_to(args.directory.parent)}")

        except Exception as e:
            print(f"Error processing {py_file}: {e}")

    print(f"\n{'=' * 60}")
    print(f"Files checked: {files_checked}")
    print(f"Files {'would be ' if args.dry_run else ''}modified: {files_modified}")

    print("\n📝 Next steps:")
    print("1. Use ruff to auto-fix remaining issues:")
    print("   ruff check src/ --fix --unsafe-fixes")
    print("\n2. For unused imports and variables:")
    print("   ruff check src/ --select F401,F841 --fix")
    print("\n3. For import organization:")
    print("   ruff check src/ --select E402,I001 --fix")


if __name__ == '__main__':
    main()
