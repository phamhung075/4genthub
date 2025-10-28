#!/usr/bin/env python3
"""Fix non-existent value object imports in test files"""

import re
from pathlib import Path

# Files with collection errors that need fixing
ERROR_FILES = [
    "src/tests/task_management/application/dtos/task/task_list_item_response_test.py",
    "src/tests/task_management/application/dtos/task/task_response_test.py",
    "src/tests/task_management/application/use_cases/add_subtask_test.py",
    "src/tests/task_management/application/use_cases/get_subtask_test.py",
    "src/tests/task_management/application/use_cases/get_subtasks_test.py",
    "src/tests/task_management/application/use_cases/get_task_test.py",
    "src/tests/task_management/application/use_cases/list_projects_test.py",
    "src/tests/task_management/application/use_cases/next_task_test.py",
    "src/tests/task_management/application/use_cases/project_health_check_test.py",
    "src/tests/task_management/application/use_cases/update_subtask_test.py",
    "src/tests/task_management/domain/entities/git_branch_test.py",
    "src/tests/task_management/domain/entities/subtask_test.py",
    "src/tests/task_management/domain/entities/task_test.py",
]

# Mapping of wrong imports to correct ones (or None to remove)
IMPORT_REPLACEMENTS = {
    'TaskTitle': None,  # Remove - use str
    'TaskDescription': None,  # Remove - use str
    'TaskPriority': 'Priority',  # Replace with Priority
    'UserId': None,  # Remove - use str
    'GitBranchName': None,  # Remove - use str
}

def fix_imports_in_file(filepath: Path) -> tuple[bool, list[str]]:
    """Fix imports in a single file"""
    changes = []

    if not filepath.exists():
        return False, [f"File not found: {filepath}"]

    content = filepath.read_text()
    original_content = content

    # Fix imports in import statements
    for wrong, correct in IMPORT_REPLACEMENTS.items():
        # Pattern: from X import A, TaskTitle, B
        pattern = rf'from\s+(\S+)\s+import\s+([^;\n]+)'

        def replace_import(match):
            module = match.group(1)
            imports = match.group(2)

            if wrong in imports:
                # Split imports, remove the wrong one or replace it
                import_list = [i.strip() for i in imports.split(',')]

                if correct:
                    # Replace
                    import_list = [correct if i == wrong else i for i in import_list]
                    changes.append(f"Replaced {wrong} with {correct} in import from {module}")
                else:
                    # Remove
                    import_list = [i for i in import_list if i != wrong]
                    changes.append(f"Removed {wrong} from import from {module}")

                if import_list:
                    return f"from {module} import {', '.join(import_list)}"
                else:
                    return ""  # Remove entire import line if empty
            return match.group(0)

        content = re.sub(pattern, replace_import, content)

    # Clean up empty import lines
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

    if content != original_content:
        filepath.write_text(content)
        return True, changes

    return False, []

def main():
    """Fix all error files"""
    base_path = Path(__file__).parent

    total_fixed = 0
    total_changes = 0

    print("🔧 Fixing non-existent value object imports...\n")

    for file_rel_path in ERROR_FILES:
        filepath = base_path / file_rel_path
        print(f"Processing: {file_rel_path}")

        fixed, changes = fix_imports_in_file(filepath)

        if fixed:
            total_fixed += 1
            total_changes += len(changes)
            for change in changes:
                print(f"  ✓ {change}")
        else:
            if changes:
                print(f"  ⚠ {changes[0]}")
            else:
                print(f"  - No changes needed")
        print()

    print(f"\n✅ Summary: Fixed {total_fixed} files with {total_changes} total changes")

if __name__ == "__main__":
    main()
