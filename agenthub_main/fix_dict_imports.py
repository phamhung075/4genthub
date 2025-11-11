#!/usr/bin/env python3
"""
Script to add 'Dict' to typing imports in files that use Dict but don't import it.
"""

import re
import sys
from pathlib import Path

# Files that need Dict import based on linting errors
FILES_NEEDING_DICT = [
    "src/tests/fixtures/mcp_auto_injection_fixtures.py",
    "src/tests/integration/test_id_validation_api_flows.py",
    "src/tests/performance/mocks/mock_mcp_server.py",
    "src/tests/utils/mcp_client_utils.py",
    "src/tests/utilities/docker_test_utils.py",
    "src/tests/unit/cache/test_redis_cache_decorator.py",
    "src/tests/unit/utilities/test_id_validator_behavioral.py",
]


def add_dict_to_typing_import(file_path: Path) -> bool:
    """
    Add Dict to existing typing import or create new import line.

    Returns True if file was modified, False otherwise.
    """
    content = file_path.read_text()
    lines = content.split("\n")

    modified = False
    new_lines = []
    typing_import_found = False

    for i, line in enumerate(lines):
        # Check if this is a typing import line
        if re.match(r"from typing import ", line):
            typing_import_found = True
            # Check if Dict is already in the import
            if "Dict" not in line:
                # Add Dict to the import
                # Handle both single-line and multi-line imports
                if line.rstrip().endswith(","):
                    # Multi-line import continuation
                    new_lines.append(line)
                elif "(" in line:
                    # Parenthesized import
                    new_lines.append(line)
                else:
                    # Simple single-line import
                    # Insert Dict at the beginning for alphabetical order
                    import_part = line.split("import ", 1)[1]
                    imports = [imp.strip() for imp in import_part.split(",")]
                    if "Dict" not in imports:
                        imports.insert(0, "Dict")
                        imports.sort()  # Keep alphabetical
                        new_line = f"from typing import {', '.join(imports)}"
                        new_lines.append(new_line)
                        modified = True
                        continue
            new_lines.append(line)
        else:
            new_lines.append(line)

    # If no typing import found, add it after other imports
    if not typing_import_found and "Dict" in content:
        # Find the last import line
        import_end_idx = 0
        for i, line in enumerate(new_lines):
            if line.startswith("import ") or line.startswith("from "):
                import_end_idx = i

        # Insert after last import
        new_lines.insert(import_end_idx + 1, "from typing import Dict")
        modified = True

    if modified:
        file_path.write_text("\n".join(new_lines))
        print(f"✅ Fixed: {file_path}")
        return True
    else:
        print(f"⏭️  Skipped: {file_path} (already has Dict or doesn't need it)")
        return False


def main():
    root = Path("/home/daihu/__projects__/4genthub/agenthub_main")

    modified_count = 0
    for file_rel in FILES_NEEDING_DICT:
        file_path = root / file_rel
        if file_path.exists():
            if add_dict_to_typing_import(file_path):
                modified_count += 1
        else:
            print(f"⚠️  Not found: {file_path}")

    print(f"\n📊 Summary: Modified {modified_count} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
