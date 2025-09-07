#!/usr/bin/env python3
"""
MCP Controller Integration Patch

This patch demonstrates how to integrate the parameter validation fix
into the existing MCP controllers to resolve the validation issues.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

# Import our fix
from fastmcp.task_management.interface.utils.parameter_validation_fix import coerce_parameter_types, ParameterTypeCoercionError


def create_enhanced_mcp_tool_wrapper():
    """
    Create an enhanced MCP tool wrapper that applies parameter coercion
    before calling the actual tool functions.
    """
    
    def enhanced_mcp_tool(original_tool_func):
        """
        Decorator to enhance MCP tool functions with parameter coercion.
        
        Args:
            original_tool_func: The original MCP tool function
            
        Returns:
            Enhanced function with parameter coercion
        """
        
        def wrapper(*args, **kwargs):
            """
            Wrapper function that applies parameter coercion before calling the original function.
            """
            try:
                # Apply parameter coercion to keyword arguments
                if kwargs:
                    coerced_kwargs = coerce_parameter_types(kwargs)
                    
                    # Call the original function with coerced parameters
                    return original_tool_func(*args, **coerced_kwargs)
                else:
                    # No kwargs to coerce, call original function directly
                    return original_tool_func(*args, **kwargs)
                    
            except ParameterTypeCoercionError as e:
                # Return a properly formatted error response
                return {
                    "success": False,
                    "error": str(e),
                    "error_code": "PARAMETER_COERCION_ERROR",
                    "parameter": e.parameter,
                    "provided_value": str(e.value),
                    "expected_type": e.expected_type,
                    "hint": "Check parameter format. Numeric parameters can be provided as strings or integers."
                }
            except Exception as e:
                # Handle any other errors
                return {
                    "success": False,
                    "error": f"Tool execution error: {str(e)}",
                    "error_code": "TOOL_EXECUTION_ERROR",
                    "hint": "Please check your parameters and try again."
                }
        
        # Preserve the original function's metadata
        wrapper.__name__ = original_tool_func.__name__
        wrapper.__doc__ = original_tool_func.__doc__
        wrapper.__annotations__ = getattr(original_tool_func, '__annotations__', {})
        
        return wrapper
    
    return enhanced_mcp_tool


# Enhanced controller classes for demonstration

class EnhancedTaskMCPController:
    """
    Enhanced TaskMCPController with parameter coercion.
    """
    def __init__(self, task_facade_factory):
        self.task_facade_factory = task_facade_factory
        self.enhanced_tool = create_enhanced_mcp_tool_wrapper()
        
        @property  
        def manage_task_tool(self):
            """
            Enhanced manage_task_tool with parameter coercion.
            """
            return self.enhanced_tool(self._manage_task_tool_impl)
        
        def _manage_task_tool_impl(self, action: str, **kwargs):
            """
            Implementation of manage_task_tool with coerced parameters.
            
            At this point, all parameters have been coerced to the correct types:
            - String integers like "5" have been converted to int 5
            - String booleans like "true" have been converted to bool True
            - Lists and other types remain unchanged
            """
            
            # Now we can safely use the parameters without type validation errors
            
            # Extract coerced parameters
            git_branch_id = kwargs.get('git_branch_id')
            title = kwargs.get('title')
            description = kwargs.get('description')
            status = kwargs.get('status')
            priority = kwargs.get('priority')
            assignees = kwargs.get('assignees')
            labels = kwargs.get('labels')
            estimated_effort = kwargs.get('estimated_effort')
            due_date = kwargs.get('due_date')
            dependencies = kwargs.get('dependencies')
            limit = kwargs.get('limit')  # This will be an int, not a string
            include_context = kwargs.get('include_context', False)  # This will be a bool
            
            # Perform action-specific logic
            if action == "create":
                return self._handle_create_task(
                    git_branch_id=git_branch_id,
                    title=title,
                    description=description,
                    priority=priority,
                    assignees=assignees,
                    labels=labels,
                    estimated_effort=estimated_effort,
                    due_date=due_date,
                    dependencies=dependencies
                )
            elif action == "update":
                return self._handle_update_task(kwargs)
            elif action == "list":
                return self._handle_list_tasks(
                    status=status,
                    priority=priority,
                    limit=limit,  # Now guaranteed to be int
                    include_context=include_context  # Now guaranteed to be bool
                )
            elif action == "search":
                query = kwargs.get('query')
                return self._handle_search_tasks(
                    query=query,
                    limit=limit,  # Now guaranteed to be int
                    git_branch_id=git_branch_id
                )
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "error_code": "UNKNOWN_ACTION"
                }
        
        def _handle_create_task(self, **kwargs):
            """Handle task creation with coerced parameters."""
            # Implementation would go here
            return {"success": True, "action": "create", "message": "Task created successfully"}
        
        def _handle_update_task(self, kwargs):
            """Handle task update with coerced parameters."""
            # Implementation would go here
            return {"success": True, "action": "update", "message": "Task updated successfully"}
        
        def _handle_list_tasks(self, **kwargs):
            """Handle task listing with coerced parameters."""
            # Implementation would go here
            return {"success": True, "action": "list", "tasks": [], "parameters_used": kwargs}
        
        def _handle_search_tasks(self, **kwargs):
            """Handle task search with coerced parameters."""
            # Implementation would go here
            return {"success": True, "action": "search", "results": [], "parameters_used": kwargs}


def patch_subtask_mcp_controller():
    """
    Example of how to patch the SubtaskMCPController to use parameter coercion.
    """
    
    class EnhancedSubtaskMCPController:
        """
        Enhanced SubtaskMCPController with parameter coercion.
        """
        
        def __init__(self, subtask_facade_factory):
            self.subtask_facade_factory = subtask_facade_factory
            self.enhanced_tool = create_enhanced_mcp_tool_wrapper()
        
        @property
        def manage_subtask_tool(self):
            """
            Enhanced manage_subtask_tool with parameter coercion.
            """
            return self.enhanced_tool(self._manage_subtask_tool_impl)
        
        def _manage_subtask_tool_impl(self, action: str, **kwargs):
            """
            Implementation of manage_subtask_tool with coerced parameters.
            """
            
            # Extract coerced parameters
            task_id = kwargs.get('task_id')
            subtask_id = kwargs.get('subtask_id')
            title = kwargs.get('title')
            description = kwargs.get('description')
            status = kwargs.get('status')
            priority = kwargs.get('priority')
            assignees = kwargs.get('assignees')
            progress_percentage = kwargs.get('progress_percentage')  # Now guaranteed to be int
            progress_notes = kwargs.get('progress_notes')
            blockers = kwargs.get('blockers')
            insights_found = kwargs.get('insights_found')
            
            # Perform action-specific logic
            if action == "create":
                return self._handle_create_subtask(
                    task_id=task_id,
                    title=title,
                    description=description,
                    priority=priority,
                    assignees=assignees
                )
            elif action == "update":
                return self._handle_update_subtask(
                    task_id=task_id,
                    subtask_id=subtask_id,
                    progress_percentage=progress_percentage,  # Now guaranteed to be int
                    progress_notes=progress_notes,
                    blockers=blockers,
                    insights_found=insights_found
                )
            elif action == "list":
                return self._handle_list_subtasks(task_id=task_id)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "error_code": "UNKNOWN_ACTION"
                }
        
        def _handle_create_subtask(self, **kwargs):
            """Handle subtask creation with coerced parameters."""
            return {"success": True, "action": "create", "message": "Subtask created successfully"}
        
        def _handle_update_subtask(self, **kwargs):
            """Handle subtask update with coerced parameters."""
            # The progress_percentage is now guaranteed to be an integer
            progress = kwargs.get('progress_percentage')
            if progress is not None:
                # Validate range (0-100)
                if not (0 <= progress <= 100):
                    return {
                        "success": False,
                        "error": f"Progress percentage must be between 0 and 100, got {progress}",
                        "error_code": "PROGRESS_OUT_OF_RANGE"
                    }
            
            return {"success": True, "action": "update", "message": "Subtask updated successfully", "progress": progress}
        
        def _handle_list_subtasks(self, **kwargs):
            """Handle subtask listing with coerced parameters."""
            return {"success": True, "action": "list", "subtasks": []}


def demo_integration():
    """
    Demonstrate how the integration works with the original failing cases.
    """
    print("🔧 MCP Controller Integration Demo")
    print("=" * 40)
    
    # Create enhanced controllers
    task_controller = EnhancedTaskMCPController(None)  # None for demo
    subtask_controller = EnhancedSubtaskMCPController(None)  # None for demo
    
    # Test the original failing cases
    test_cases = [
        {
            "name": "Task search with string limit",
            "controller": task_controller,
            "method": "manage_task_tool",
            "args": {"action": "search", "query": "test", "limit": "5"}  # String limit
        },
        {
            "name": "Task list with string boolean",
            "controller": task_controller, 
            "method": "manage_task_tool",
            "args": {"action": "list", "include_context": "true"}  # String boolean
        },
        {
            "name": "Subtask update with string progress",
            "controller": subtask_controller,
            "method": "manage_subtask_tool", 
            "args": {"action": "update", "task_id": "test", "subtask_id": "test", "progress_percentage": "50"}  # String progress
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print(f"Arguments: {test_case['args']}")
        
        try:
            # Get the method and call it
            method = getattr(test_case['controller'], test_case['method'])
            result = method(**test_case['args'])
            
            if result.get('success', False):
                print(f"✅ SUCCESS: {result.get('message', 'Operation completed')}")
                if 'parameters_used' in result:
                    print(f"   Coerced parameters: {result['parameters_used']}")
            else:
                print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
    
    print(f"\n🎯 Integration Demo Complete!")


if __name__ == "__main__":
    demo_integration()