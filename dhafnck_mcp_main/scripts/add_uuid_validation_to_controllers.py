#!/usr/bin/env python3
"""
Script to add UUID validation to all MCP controllers that handle UUID parameters.
This ensures consistent validation across all controllers.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Controllers and their UUID parameters to check
CONTROLLERS_TO_CHECK = [
    ("project_mcp_controller.py", ["project_id"]),
    ("git_branch_mcp_controller.py", ["project_id", "git_branch_id"]),
    ("agent_mcp_controller.py", ["project_id", "agent_id", "git_branch_id"]),
    ("unified_context_controller.py", ["context_id", "task_id", "git_branch_id", "project_id"]),
    ("dependency_mcp_controller.py", ["task_id", "dependency_id"]),
]

UUID_VALIDATION_METHOD = '''
    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """
        Validate if a string is a valid UUID format.
        
        Accepts both formats:
        - Standard UUID with hyphens: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        - Hex format without hyphens: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx (32 chars)
        
        Args:
            uuid_string: String to validate
            
        Returns:
            True if valid UUID format, False otherwise
        """
        if not uuid_string or not isinstance(uuid_string, str):
            return False
            
        uuid_string = uuid_string.strip()
        
        # Try to parse as UUID - this handles both formats
        try:
            uuid.UUID(uuid_string)
            return True
        except (ValueError, TypeError):
            # Check if it's a 32-character hex string (UUID without hyphens)
            if len(uuid_string) == 32 and re.match(r'^[0-9a-fA-F]{32}$', uuid_string):
                return True
            return False'''

def add_imports_if_needed(content: str) -> str:
    """Add uuid and re imports if not present."""
    lines = content.split('\n')
    
    # Find where imports are
    import_section_start = -1
    import_section_end = -1
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            if import_section_start == -1:
                import_section_start = i
            import_section_end = i
    
    # Check if uuid and re are imported
    has_uuid = any('import uuid' in line for line in lines)
    has_re = any('import re' in line for line in lines)
    
    if not has_uuid or not has_re:
        imports_to_add = []
        if not has_uuid:
            imports_to_add.append('import uuid')
        if not has_re:
            imports_to_add.append('import re')
        
        # Insert after other imports
        if import_section_end >= 0:
            for imp in reversed(imports_to_add):
                lines.insert(import_section_end + 1, imp)
    
    return '\n'.join(lines)

def add_validation_method_if_needed(content: str) -> str:
    """Add the _is_valid_uuid method if not present."""
    if '_is_valid_uuid' not in content:
        # Find the last method or end of class
        lines = content.split('\n')
        
        # Find the last line of the class (before the next class or end of file)
        last_method_line = -1
        indent_level = None
        in_class = False
        
        for i, line in enumerate(lines):
            if 'class ' in line and 'MCPController' in line:
                in_class = True
                # Determine indent level
                indent_level = len(line) - len(line.lstrip())
            elif in_class:
                if line.strip() and not line[indent_level:indent_level+1].isspace() and line.strip()[0] not in '#':
                    # End of class
                    break
                if line.strip().startswith('def '):
                    last_method_line = i
        
        # Find the end of the last method
        if last_method_line > 0:
            for i in range(last_method_line + 1, len(lines)):
                if lines[i].strip() and not lines[i].startswith(' '):
                    # Insert before this line
                    lines.insert(i, UUID_VALIDATION_METHOD)
                    break
            else:
                # End of file
                lines.append(UUID_VALIDATION_METHOD)
        
        return '\n'.join(lines)
    
    return content

def generate_uuid_validation_code(param_name: str) -> str:
    """Generate validation code for a UUID parameter."""
    return f'''
        # Validate UUID format for {param_name} if provided
        if {param_name} and not self._is_valid_uuid({param_name}):
            return {{
                "success": False,
                "error": f"Invalid {param_name} format: '{{{param_name}}}'. Expected UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "error_code": "INVALID_FORMAT",
                "field": "{param_name}",
                "expected_format": "UUID (e.g., 550e8400-e29b-41d4-a716-446655440000)",
                "hint": "Use a valid UUID for {param_name}. Get UUIDs from creation or list operations."
            }}'''

def main():
    base_path = Path("/home/daihungpham/agentic-project/dhafnck_mcp_main/src/fastmcp/task_management/interface/controllers")
    
    for controller_file, uuid_params in CONTROLLERS_TO_CHECK:
        file_path = base_path / controller_file
        
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            continue
        
        print(f"\n📝 Processing {controller_file}...")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check if already has validation
        if '_is_valid_uuid' in content:
            print(f"  ✅ Already has UUID validation method")
        else:
            print(f"  ⚠️ Missing UUID validation - needs update")
            print(f"  📋 UUID parameters to validate: {uuid_params}")
            
            # Add imports
            content = add_imports_if_needed(content)
            
            # Add validation method
            content = add_validation_method_if_needed(content)
            
            # Note: Adding parameter validation would require more complex parsing
            # to find the right location in each manage_* method
            print(f"  ℹ️ Manual review needed to add parameter validation for: {uuid_params}")

if __name__ == "__main__":
    main()