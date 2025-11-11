#!/usr/bin/env python3
"""Add 'from __future__ import annotations' to files that need it"""

import re
from pathlib import Path


def needs_future_annotations(content: str) -> bool:
    """Check if file uses | union syntax in type annotations"""
    # Check for | in type annotations (e.g., str | None, int | str)
    return bool(re.search(r":\s*\w+\s*\|\s*(\w+|None)", content))


def has_future_annotations(content: str) -> bool:
    """Check if file already has future annotations import"""
    return "from __future__ import annotations" in content


def add_future_annotations(content: str) -> str:
    """Add future annotations import to the top of the file"""
    lines = content.split("\n")

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
        if stripped and not stripped.startswith("#"):
            if not stripped.startswith('"""') and not stripped.startswith("'''"):
                insert_at = i
                break

    # Insert the future import
    lines.insert(insert_at, "from __future__ import annotations")
    lines.insert(insert_at + 1, "")  # Add blank line

    return "\n".join(lines)


def main():
    """Main entry point"""
    src_dir = Path("src")
    fixed_count = 0
    checked_count = 0

    for py_file in src_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
            checked_count += 1

            if needs_future_annotations(content) and not has_future_annotations(
                content
            ):
                new_content = add_future_annotations(content)
                py_file.write_text(new_content, encoding="utf-8")
                fixed_count += 1
                print(f"Fixed: {py_file.relative_to(src_dir.parent)}")

        except Exception as e:
            print(f"Error processing {py_file}: {e}")

    print(f"\nChecked: {checked_count} files")
    print(f"Fixed: {fixed_count} files")


if __name__ == "__main__":
    main()
