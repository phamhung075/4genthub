#!/usr/bin/env python3
"""Fix non-existent value object imports in test files - Version 2"""

import re
from pathlib import Path

# Mapping of non-existent to what they should be
# None means remove the import and usage
NON_EXISTENT_IMPORTS = {
    'TaskTitle': 'str',  # Should use plain str
    'TaskDescription': 'str',  # Should use plain str
    'TaskPriority': 'Priority',  # Should use Priority
    'UserId': 'str',  # Should use plain str
    'GitBranchName': 'str',  # Should use plain str
    'TaskDetails': 'str',  # Should use plain str (details field is str)
}

def remove_from_multiline_import(content: str) -> tuple[str, list[str]]:
    """Remove non-existent imports from multi-line import blocks"""
    changes = []

    # Find all import blocks from value_objects
    pattern = r'from\s+fastmcp\.task_management\.domain\.value_objects\s+import\s+\((.*?)\)'

    def replace_import_block(match):
        imports_block = match.group(1)
        import_lines = [line.strip().rstrip(',') for line in imports_block.split('\n')]

        new_imports = []
        for line in import_lines:
            if not line:
                continue

            # Check if this import should be removed
            should_remove = False
            for non_existent in NON_EXISTENT_IMPORTS:
                if line == non_existent or line.startswith(non_existent + ','):
                    should_remove = True
                    changes.append(f"Removed {non_existent} from value_objects import")
                    break

            if not should_remove:
                new_imports.append(line)

        if new_imports:
            imports_str = ',\n    '.join(new_imports)
            return f'from fastmcp.task_management.domain.value_objects import (\n    {imports_str}\n)'
        else:
            return ''  # Remove entire import if empty

    new_content = re.sub(pattern, replace_import_block, content, flags=re.DOTALL)

    # Also handle single-line imports
    for non_existent in NON_EXISTENT_IMPORTS:
        # Pattern: , TaskTitle,  or  ,TaskTitle  or  TaskTitle,
        pattern = rf',\s*{non_existent}\s*,|,\s*{non_existent}\s*(?=\))|(?<=\()\s*{non_existent}\s*,\s*'
        if re.search(pattern, new_content):
            new_content = re.sub(pattern, lambda m: ',' if m.group().count(',') > 1 else '', new_content)
            changes.append(f"Removed {non_existent} from inline import")

    return new_content, changes

def replace_usage_in_code(content: str) -> tuple[str, list[str]]:
    """Replace wrapper class usage with plain values"""
    changes = []

    replacements = {
        # TaskTitle("text") -> "text"
        r'TaskTitle\("([^"]+)"\)': r'"\1"',
        r"TaskTitle\('([^']+)'\)": r"'\1'",

        # TaskDescription("text") -> "text"
        r'TaskDescription\("([^"]+)"\)': r'"\1"',
        r"TaskDescription\('([^']+)'\)": r"'\1'",

        # TaskDetails("text") -> "text"
        r'TaskDetails\("([^"]+)"\)': r'"\1"',
        r"TaskDetails\('([^']+)'\)": r"'\1'",

        # GitBranchName("text") -> "text"
        r'GitBranchName\("([^"]+)"\)': r'"\1"',
        r"GitBranchName\('([^']+)'\)": r"'\1'",

        # UserId("text") -> "text"
        r'UserId\("([^"]+)"\)': r'"\1"',
        r"UserId\('([^']+)'\)": r"'\1'",

        # EstimatedEffort("text") -> "text" (also not a value object, just str)
        r'EstimatedEffort\("([^"]+)"\)': r'"\1"',
        r"EstimatedEffort\('([^']+)'\)": r"'\1'",

        # TaskPriority.HIGH -> Priority.HIGH
        r'TaskPriority\.': 'Priority.',
    }

    for pattern, replacement in replacements.items():
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            changes.append(f"Replaced usage pattern: {pattern[:30]}...")

    return content, changes

def fix_file(filepath: Path) -> tuple[bool, list[str]]:
    """Fix a single file"""
    if not filepath.exists():
        return False, [f"File not found"]

    content = filepath.read_text()
    original = content
    all_changes = []

    # Step 1: Remove non-existent imports
    content, changes1 = remove_from_multiline_import(content)
    all_changes.extend(changes1)

    # Step 2: Replace usage in code
    content, changes2 = replace_usage_in_code(content)
    all_changes.extend(changes2)

    # Step 3: Clean up empty lines
    content = re.sub(r'\n\n\n+', '\n\n', content)

    if content != original:
        filepath.write_text(content)
        return True, all_changes

    return False, []

def main():
    """Fix all error files"""
    # Get all test files with these imports
    base = Path(__file__).parent / "src/tests"

    # Find files with collection errors
    error_files = [
        "task_management/application/dtos/task/task_list_item_response_test.py",
        "task_management/application/dtos/task/task_response_test.py",
        "task_management/application/use_cases/add_subtask_test.py",
        "task_management/application/use_cases/get_subtask_test.py",
        "task_management/application/use_cases/get_subtasks_test.py",
        "task_management/application/use_cases/get_task_test.py",
        "task_management/application/use_cases/list_projects_test.py",
        "task_management/application/use_cases/next_task_test.py",
        "task_management/application/use_cases/project_health_check_test.py",
        "task_management/application/use_cases/update_subtask_test.py",
        "task_management/domain/entities/git_branch_test.py",
        "task_management/domain/entities/subtask_test.py",
        "task_management/domain/entities/task_test.py",
    ]

    print("🔧 Fixing non-existent value object imports (v2)...\n")

    total_fixed = 0
    total_changes = 0

    for file_rel in error_files:
        filepath = base / file_rel
        print(f"📝 {file_rel}")

        fixed, changes = fix_file(filepath)

        if fixed:
            total_fixed += 1
            total_changes += len(changes)
            for change in changes:
                print(f"   ✓ {change}")
        else:
            print(f"   - No changes needed")
        print()

    print(f"✅ Fixed {total_fixed}/{len(error_files)} files with {total_changes} changes")

if __name__ == "__main__":
    main()
