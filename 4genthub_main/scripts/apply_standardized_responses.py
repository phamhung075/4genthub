#!/usr/bin/env python3
"""
Script to apply standardized response format to all MCP controllers
"""

import os
import re
from pathlib import Path


def update_controller_imports(file_path: Path) -> bool:
    """Add standardized response formatter import to controller"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already imported
    if 'StandardResponseFormatter' in content:
        print(f"✓ {file_path.name} already has StandardResponseFormatter imported")
        return False
    
    # Find the imports section and add our import
    import_pattern = r'(from \.\.utils\.error_handler import.*\n)'
    replacement = r'\1from ..utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes\n'
    
    new_content = re.sub(import_pattern, replacement, content)
    
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"✓ Updated imports in {file_path.name}")
        return True
    
    return False


def add_standardization_methods(file_path: Path) -> bool:
    """Add response standardization helper methods to controller"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if methods already exist
    if '_standardize_response' in content:
        print(f"✓ {file_path.name} already has standardization methods")
        return False
    
    # Find a good place to add the methods (before the last method or at the end of class)
    # Look for the last method definition in the class
    methods_to_add = '''
    def _standardize_response(
        self, 
        result: Dict[str, Any], 
        operation: str,
        workflow_guidance: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert legacy response format to standardized format.
        
        Args:
            result: The original response from facade
            operation: The operation performed
            workflow_guidance: Workflow guidance to include
            metadata: Additional metadata
            
        Returns:
            Standardized response following the new format
        """
        # Check if this is already a standardized response
        if "operation_id" in result and "confirmation" in result:
            return result
            
        # Handle error responses
        if not result.get("success", False):
            error_code = result.get("error_code", ErrorCodes.OPERATION_FAILED)
            
            # Check for validation errors
            if "field" in result or "parameter" in result:
                return StandardResponseFormatter.create_validation_error_response(
                    operation=operation,
                    field=result.get("field") or result.get("parameter", "unknown"),
                    expected=result.get("expected", "valid value"),
                    hint=result.get("hint")
                )
            
            # Standard error response
            return StandardResponseFormatter.create_error_response(
                operation=operation,
                error=result.get("error", "Operation failed"),
                error_code=error_code,
                metadata=metadata
            )
        
        # Handle success responses
        # Extract the main data object
        data = self._extract_data_from_result(result)
        
        # Check for partial failures
        partial_failures = []
        if "context_update_error" in result:
            partial_failures.append({
                "operation": "context_update",
                "error": result["context_update_error"],
                "impact": "Context may be out of sync"
            })
        
        # Create standardized response
        if partial_failures:
            return StandardResponseFormatter.create_partial_success_response(
                operation=operation,
                data=data,
                partial_failures=partial_failures,
                metadata=metadata,
                workflow_guidance=workflow_guidance or result.get("workflow_guidance")
            )
        else:
            return StandardResponseFormatter.create_success_response(
                operation=operation,
                data=data,
                metadata=metadata,
                workflow_guidance=workflow_guidance or result.get("workflow_guidance")
            )
    
    def _extract_data_from_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data payload from result based on controller type"""
        # Override this method in each controller for specific data extraction
        data = {}
        
        # Common patterns
        for key in ["task", "tasks", "context", "subtask", "subtasks", 
                    "agent", "agents", "git_branch", "branches", "project"]:
            if key in result:
                data[key] = result[key]
        
        # If no standard keys found, include all non-metadata fields
        if not data:
            data = {k: v for k, v in result.items() 
                   if k not in ["success", "error", "workflow_guidance"]}
        
        return data
    
    def _create_standardized_error(
        self,
        operation: str,
        field: str,
        expected: str,
        hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a standardized validation error response."""
        return StandardResponseFormatter.create_validation_error_response(
            operation=operation,
            field=field,
            expected=expected,
            hint=hint
        )
'''
    
    # Find the last method in the class
    class_pattern = r'(class \w+.*?:.*?)(\n\n|\Z)'
    
    def add_methods_to_class(match):
        class_content = match.group(1)
        # Add methods before the end of the class
        return class_content + methods_to_add + match.group(2)
    
    # This is a simplified approach - in reality we'd need better parsing
    # For now, let's just add it before the last line if we can't find a good spot
    if '\n\nclass ' in content:
        # Multiple classes, be careful
        print(f"⚠️  {file_path.name} has multiple classes, needs manual review")
        return False
    
    # Add before the last function or at the end
    lines = content.split('\n')
    insert_index = len(lines) - 1
    
    # Find the last method definition
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith('def ') and not lines[i].strip().startswith('def create_'):
            insert_index = i
            break
    
    # Insert the methods
    lines.insert(insert_index, methods_to_add)
    
    new_content = '\n'.join(lines)
    
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"✓ Added standardization methods to {file_path.name}")
    return True


def update_handler_methods(file_path: Path) -> bool:
    """Update handler methods to use standardized responses"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # This is controller-specific and would need custom logic for each
    # For now, we'll just report what needs to be done
    
    handlers = re.findall(r'def (_handle_\w+)\(', content)
    if handlers:
        print(f"ℹ️  {file_path.name} has {len(handlers)} handler methods that need updating:")
        for handler in handlers:
            print(f"   - {handler}")
    
    return False


def main():
    """Main function to process all controllers"""
    controllers_dir = Path("/home/daihungpham/agentic-project/4genthub_main/src/fastmcp/task_management/interface/controllers")
    
    # List of controller files to update
    controller_files = [
        "subtask_mcp_controller.py",
        "context_mcp_controller.py",
        "git_branch_mcp_controller.py",
        "agent_mcp_controller.py",
        "rule_orchestration_controller.py",
        "project_mcp_controller.py",
        "connection_mcp_controller.py",
        "compliance_mcp_controller.py"
    ]
    
    print("🔄 Applying standardized response format to all controllers...")
    print("=" * 60)
    
    for controller_file in controller_files:
        file_path = controllers_dir / controller_file
        
        if not file_path.exists():
            print(f"❌ {controller_file} not found")
            continue
        
        print(f"\n📄 Processing {controller_file}...")
        
        # Step 1: Update imports
        update_controller_imports(file_path)
        
        # Step 2: Add standardization methods
        add_standardization_methods(file_path)
        
        # Step 3: Report what needs manual updating
        update_handler_methods(file_path)
    
    print("\n" + "=" * 60)
    print("✅ Script completed!")
    print("\n⚠️  Manual steps required:")
    print("1. Update each handler method to use _standardize_response()")
    print("2. Replace error returns with _create_standardized_error()")
    print("3. Override _extract_data_from_result() for controller-specific data")
    print("4. Test each controller after updates")


if __name__ == "__main__":
    main()