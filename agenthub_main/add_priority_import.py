#!/usr/bin/env python3
"""Add missing Priority import to files that use it"""

import re
from pathlib import Path

FILES_NEEDING_PRIORITY = [
    "src/tests/task_management/application/dtos/task/task_list_item_response_test.py",
    "src/tests/task_management/application/dtos/task/task_response_test.py",
    "src/tests/task_management/application/use_cases/add_subtask_test.py",
    "src/tests/task_management/application/use_cases/get_subtask_test.py",
    "src/tests/task_management/application/use_cases/get_subtasks_test.py",
    "src/tests/task_management/application/use_cases/get_task_test.py",
    "src/tests/task_management/application/use_cases/next_task_test.py",
    "src/tests/task_management/application/use_cases/project_health_check_test.py",
    "src/tests/task_management/application/use_cases/update_subtask_test.py",
    "src/tests/task_management/domain/entities/subtask_test.py",
    "src/tests/task_management/domain/entities/task_test.py",
]

def add_priority_to_import(content: str) -> tuple[str, bool]:
    """Add Priority to value_objects import block"""

    # Pattern for multiline import from value_objects
    pattern = r'(from\s+fastmcp\.task_management\.domain\.value_objects\s+import\s+\()(.*?)(\))'

    def add_priority(match):
        prefix = match.group(1)
        imports = match.group(2)
        suffix = match.group(3)

        # Check if Priority is already there
        if re.search(r'\bPriority\b', imports):
            return match.group(0)  # Already has Priority

        # Add Priority to the import list
        import_lines = [line.strip() for line in imports.split('\n') if line.strip()]

        # Add Priority as the last import
        import_lines.append('Priority')

        # Format nicely
        formatted_imports = ',\n    '.join(import_lines)

        return f'{prefix}\n    {formatted_imports}\n{suffix}'

    new_content, count = re.subn(pattern, add_priority, content, flags=re.DOTALL)

    return new_content, count > 0

def main():
    """Add Priority import to all files that need it"""
    base = Path(__file__).parent

    print("🔧 Adding missing Priority imports...\n")

    total_fixed = 0

    for file_rel in FILES_NEEDING_PRIORITY:
        filepath = base / file_rel
        print(f"📝 {file_rel}")

        if not filepath.exists():
            print(f"   ⚠ File not found")
            continue

        content = filepath.read_text()

        new_content, changed = add_priority_to_import(content)

        if changed:
            filepath.write_text(new_content)
            total_fixed += 1
            print(f"   ✓ Added Priority to imports")
        else:
            print(f"   - Already has Priority or no value_objects import")

    print(f"\n✅ Added Priority import to {total_fixed}/{len(FILES_NEEDING_PRIORITY)} files")

if __name__ == "__main__":
    main()
