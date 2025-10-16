# MCP Parameter Type Resolution Guide - Complete Implementation Pattern

## Overview

This guide documents the complete pattern for implementing MCP (Model Context Protocol) tool controllers with proper parameter type handling, two-stage validation, and clean architecture. This pattern solves parameter type display issues and provides a maintainable, scalable approach for MCP tools.

## Problem Statement

MCP framework has limitations with certain Python type annotations:
- Does not properly recognize `Optional[Type]` annotations
- Shows `Union[Type1, Type2]` as "unknown" type in tool interfaces
- Cannot properly display complex type hints in parameter documentation
- **Critical**: `oneOf` and `anyOf` JSON schema constructs are not recognized and show as "unknown"
- **Hidden Issue**: Global schema monkey patches can override clean parameter definitions

## Solution Approach

### 1. Simplified Type Annotations

Instead of using complex types in function signatures, use simple base types that MCP can recognize:

**Before (Shows as "unknown"):**
```python
assignees: Annotated[Optional[Union[str, List[str]]], Field(description="...")] = None
limit: Annotated[Union[int, str], Field(description="...")] = None
```

**After (Shows proper type):**
```python
assignees: Annotated[str, Field(description="[OPTIONAL] ...")] = None
limit: Annotated[int, Field(description="[OPTIONAL] ...")] = None
```

### 2. Parameter Description Convention

Since MCP doesn't recognize `Optional`, indicate optional parameters in the description:

```python
# Required parameter
action: Annotated[str, Field(description="Task management action. Required. ...")]

# Optional parameter  
task_id: Annotated[str, Field(description="[OPTIONAL] Task identifier ...")] = None
```

### 3. Type Conversion in Function Body

Handle flexible input types through conversion logic inside the function:

```python
async def manage_task(
    assignees: Annotated[str, Field(description="[OPTIONAL] ...")] = None,
    limit: Annotated[int, Field(description="[OPTIONAL] ...")] = None,
    ...
) -> Dict[str, Any]:
    # Handle flexible input types
    if assignees is not None and isinstance(assignees, str):
        if ',' in assignees:
            assignees = [a.strip() for a in assignees.split(',')]
    
    # Convert string representations to integers
    if limit is not None and not isinstance(limit, int):
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 50  # Default value
```

## Complete Implementation Pattern

### Step 1: Create Parameter Definitions Module

Create a separate module for centralized parameter management:

```python
# manage_task_description.py

TOOL_NAME = "manage_task"

# Comprehensive tool documentation
MANAGE_TASK_DESCRIPTION = """
📋 TASK MANAGEMENT SYSTEM - Complete task lifecycle operations

⚠️ PARAMETER VALIDATION PATTERN - TWO-STAGE VALIDATION:

📌 WHY ONLY 'action' IS REQUIRED IN JSON SCHEMA:
The tool uses a two-stage validation pattern:
1. **Schema Level**: Only 'action' is marked as required in JSON schema
2. **Business Logic Level**: Based on the action value, specific parameters become required

This design provides:
- ✅ Flexibility: Different actions need different parameters
- ✅ Better Error Messages: Context-specific validation errors
- ✅ MCP Compatibility: Works better with single required parameter
- ✅ User Experience: Clear feedback about what's missing for each action

📋 ACTUAL REQUIRED PARAMETERS BY ACTION (Validated in Business Logic):
| Action | Required Parameters | Optional But Recommended |
|--------|-------------------|--------------------------|
| create | action, git_branch_id, title | description, priority |
| update | action, task_id | any field to update |
| get | action, task_id | include_context |
| delete | action, task_id | - |
| complete | action, task_id | completion_summary, testing_notes |
| list | action | git_branch_id, status, priority |
| search | action, query | limit |
| next | action, git_branch_id | include_context |
| add_dependency | action, task_id, dependency_id | - |
| remove_dependency | action, task_id, dependency_id | - |
"""

# Parameter descriptions dictionary
MANAGE_TASK_PARAMETERS_DESCRIPTION = {
    "action": "Task management action. Valid: 'create', 'update', 'get', 'delete', 'complete', 'list', 'search', 'next', 'add_dependency', 'remove_dependency'.",
    "task_id": "Task identifier (UUID). Required for: update, get, delete, complete, add/remove_dependency.",
    "git_branch_id": "Git branch UUID identifier. Required for 'create' and 'next' actions.",
    "title": "Task title - be specific and action-oriented. Required for: create.",
    "description": "Detailed task description with acceptance criteria. Optional but recommended.",
    "status": "Task status: 'todo', 'in_progress', 'blocked', 'review', 'testing', 'done', 'cancelled'.",
    "priority": "Task priority: 'low', 'medium', 'high', 'urgent', 'critical'. Default: 'medium'.",
    "assignees": "User identifiers - accepts string (single user) or comma-separated string (multiple users).",
    "labels": "Categories/tags - accepts string (single label) or comma-separated string (multiple labels).",
    "limit": "Maximum number of results. Default: 50. Range: 1-100",
    "include_context": "Include vision insights and recommendations (true/false). Default: false.",
    # ... all other parameters
}

# JSON Schema with organized parameters
# TWO-STAGE VALIDATION DESIGN:
# - Schema Level: Only 'action' is marked as required here
# - Business Logic: Action-specific parameters are validated in the controller
MANAGE_TASK_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["action"]
        },
        
        # Task identification parameters
        "task_id": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["task_id"]
        },
        "git_branch_id": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["git_branch_id"]
        },
        
        # Task creation/update parameters
        "title": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["title"]
        },
        "description": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["description"]
        },
        
        # Multi-value parameters (accept comma-separated strings)
        "assignees": {
            "type": "string",  # Not array! MCP doesn't handle complex types
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["assignees"]
        },
        "labels": {
            "type": "string",  # Not array! MCP doesn't handle complex types
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["labels"]
        },
        
        # Boolean control parameters
        "include_context": {
            "type": "boolean",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["include_context"]
        },
        
        # Search and filter parameters
        "limit": {
            "type": "integer",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["limit"]
        },
        # ... all other properties organized by category
    },
    "required": ["action"],  # Only action is required at schema level!
    "additionalProperties": False
}

def get_manage_task_description():
    """Get the complete task management tool description."""
    return MANAGE_TASK_DESCRIPTION

def get_manage_task_parameters():
    """Get the task management tool parameters schema."""
    return MANAGE_TASK_PARAMS
```

### Step 2: Implement Controller with Two-Stage Validation

```python
# task_mcp_controller.py

from typing import Dict, Any, Optional, List, Annotated
from pydantic import Field
from .manage_task_description import (
    get_manage_task_description,
    get_manage_task_parameters
)

class TaskMCPController:
    def register_tools(self, mcp: "FastMCP"):
        """Register MCP tools with the server."""
        
        # Load description and parameters from centralized definitions
        tool_description = get_manage_task_description()
        tool_parameters = get_manage_task_parameters()
        
        # Extract parameter definitions for use in annotations
        params = tool_parameters["properties"]
        
        async def manage_task(
            # Required parameter
            action: Annotated[str, Field(description=params["action"]["description"])],
            
            # All other parameters are optional at schema level
            # Add "[OPTIONAL]" prefix to descriptions for clarity
            task_id: Annotated[str, Field(description="[OPTIONAL] " + params["task_id"]["description"])] = None,
            git_branch_id: Annotated[str, Field(description="[OPTIONAL] " + params["git_branch_id"]["description"])] = None,
            title: Annotated[str, Field(description="[OPTIONAL] " + params["title"]["description"])] = None,
            description: Annotated[str, Field(description="[OPTIONAL] " + params["description"]["description"])] = None,
            
            # Use simple types for MCP compatibility:
            # - str instead of Union[str, List[str]] for arrays
            # - int instead of Union[int, str] for numbers
            # - bool instead of Union[bool, str] for booleans
            assignees: Annotated[str, Field(description="[OPTIONAL] " + params["assignees"]["description"])] = None,
            labels: Annotated[str, Field(description="[OPTIONAL] " + params["labels"]["description"])] = None,
            dependencies: Annotated[str, Field(description="[OPTIONAL] " + params["dependencies"]["description"])] = None,
            
            # Integer parameters
            limit: Annotated[int, Field(description="[OPTIONAL] " + params["limit"]["description"])] = None,
            offset: Annotated[int, Field(description="[OPTIONAL] " + params["offset"]["description"])] = None,
            
            # Boolean parameters
            include_context: Annotated[bool, Field(description="[OPTIONAL] " + params["include_context"]["description"])] = None,
            force_full_generation: Annotated[bool, Field(description="[OPTIONAL] " + params["force_full_generation"]["description"])] = None,
            
            # ... all other parameters
        ) -> Dict[str, Any]:
            """Main task management function with all parameters.
            
            TWO-STAGE VALIDATION PATTERN:
            1. Schema validation: Only 'action' is required at MCP level
            2. Business validation: Action-specific parameters are validated based on the action value
            
            This design allows flexible parameter requirements while maintaining a single entry point.
            """
            
            # Handle boolean defaults
            if include_context is None:
                include_context = False
            if force_full_generation is None:
                force_full_generation = False
            
            # Handle flexible input types for parameters that can be comma-separated
            if assignees is not None and isinstance(assignees, str):
                if ',' in assignees:
                    assignees = [a.strip() for a in assignees.split(',')]
            
            if labels is not None and isinstance(labels, str):
                if ',' in labels:
                    labels = [l.strip() for l in labels.split(',')]
            
            if dependencies is not None and isinstance(dependencies, str):
                if ',' in dependencies:
                    dependencies = [d.strip() for d in dependencies.split(',')]
            
            # Convert string representations of integers to actual integers
            if limit is not None and not isinstance(limit, int):
                try:
                    limit = int(limit)
                except (ValueError, TypeError):
                    limit = 50  # Default value
            
            if offset is not None and not isinstance(offset, int):
                try:
                    offset = int(offset)
                except (ValueError, TypeError):
                    offset = 0  # Default value
            
            # Delegate to actual implementation with all parameters
            return await self.manage_task(
                action=action, task_id=task_id, git_branch_id=git_branch_id,
                title=title, description=description, status=status,
                priority=priority, details=details, estimated_effort=estimated_effort,
                assignees=assignees, labels=labels, due_date=due_date,
                dependencies=dependencies, dependency_id=dependency_id, context_id=context_id,
                completion_summary=completion_summary, testing_notes=testing_notes,
                query=query, limit=limit, offset=offset, sort_by=sort_by,
                sort_order=sort_order, include_context=include_context,
                force_full_generation=force_full_generation,
                assignee=assignee, tag=tag, user_id=user_id
            )
        
        # Register tool with description only (parameters is not supported by mcp.tool decorator)
        mcp.tool(description=tool_description)(manage_task)
    
    async def manage_task(self, action: str, user_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Main entry point for task management operations.
        
        Two-stage validation pattern:
        - Stage 1: MCP validates only 'action' is present (schema level)
        - Stage 2: This method validates action-specific requirements (business level)
        """
        
        try:
            # Validate request based on action using ValidationFactory
            validation_result = self._validate_request(action, **kwargs)
            if not validation_result[0]:
                return validation_result[1]  # Return validation error
            
            # Execute operation based on action
            # ... operation logic here
            
        except Exception as e:
            return self._create_error_response(str(e))
```

## Type Mapping Guidelines

### MCP-Compatible Types

| Python Type | MCP Display | Usage |
|------------|-------------|--------|
| `str` | string | Text parameters |
| `int` | integer | Numeric parameters |
| `bool` | boolean | True/false flags |
| `float` | number | Decimal numbers |

### Types to Avoid in Signatures

| Avoid | Use Instead | Handle In Body |
|-------|-------------|----------------|
| `Optional[str]` | `str` with `= None` | Check for None |
| `Union[str, List[str]]` | `str` with `= None` | Parse comma-separated |
| `Union[int, str]` | `int` with `= None` | Convert string to int |
| `Union[bool, str]` | `bool` with `= None` | Parse string booleans |
| `List[str]` | `str` with `= None` | Split on comma |
| `Dict[str, Any]` | `dict` or handle as JSON string | Parse JSON in body |

### JSON Schema to Avoid

| Avoid | Use Instead | Why |
|-------|-------------|-----|
| `"oneOf": [...]` | Single `"type"` | MCP doesn't recognize oneOf |
| `"anyOf": [...]` | Single `"type"` | MCP doesn't recognize anyOf |
| Complex nested schemas | Simple flat types | MCP only handles basic types |

## Parameter Documentation Format

### Required Parameters
```python
action: Annotated[str, Field(description="Action to perform. Required. Valid values: ...")]
```

### Optional Parameters
```python
task_id: Annotated[str, Field(description="[OPTIONAL] Task identifier. Used for ...")] = None
```

### Parameters with Multiple Input Formats
```python
assignees: Annotated[str, Field(description="[OPTIONAL] User IDs - can be string, list, or comma-separated. Examples: 'user1' or 'user1,user2'")] = None
```

## Conversion Patterns

### 1. Comma-Separated String to List
```python
if param is not None and isinstance(param, str):
    if ',' in param:
        param = [item.strip() for item in param.split(',')]
```

### 2. String to Integer
```python
if param is not None and not isinstance(param, int):
    try:
        param = int(param)
    except (ValueError, TypeError):
        param = default_value
```

### 3. JSON String to Dictionary
```python
if param is not None and isinstance(param, str):
    try:
        param = json.loads(param)
    except json.JSONDecodeError:
        # Handle as plain string or error
        pass
```

### 4. Boolean String Parsing
```python
if param is not None and isinstance(param, str):
    param = param.lower() in ('true', '1', 'yes', 'on')
```

### Step 3: Implement Validation Factory

```python
# validators/parameter_validator.py

class ParameterValidator:
    """Validates parameters based on action requirements."""
    
    def validate_create_task_params(self, title: Optional[str], git_branch_id: Optional[str], 
                                  **kwargs) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate parameters for task creation."""
        
        # Validate required fields for create action
        if not title or not title.strip():
            return False, self._create_validation_error(
                "title", "A non-empty title string", "Include 'title' in your request"
            )
        
        if not git_branch_id:
            return False, self._create_validation_error(
                "git_branch_id", "A valid git_branch_id string", 
                "Include 'git_branch_id' in your request"
            )
        
        # Validate optional fields...
        return True, None

# factories/validation_factory.py

class ValidationFactory:
    """Factory for handling validation based on action."""
    
    def validate_request(self, action: str, **kwargs) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Route validation based on action."""
        
        if action == "create":
            return self._parameter_validator.validate_create_task_params(
                title=kwargs.get('title'),
                git_branch_id=kwargs.get('git_branch_id'),
                **kwargs
            )
        elif action in ["update", "get", "delete", "complete"]:
            task_id = kwargs.get('task_id')
            if not task_id:
                return False, self._create_error_response(
                    "task_id is required for this action"
                )
            return True, None
        elif action == "search":
            query = kwargs.get('query')
            if not query:
                return False, self._create_error_response(
                    "query is required for search action"
                )
            return True, None
        # ... handle other actions
```

## Complete Example: Generic MCP Controller

```python
from typing import Dict, Any, Annotated
from pydantic import Field
import json

class GenericMCPController:
    """Generic MCP controller following best practices."""
    
    def __init__(self):
        # Load parameter definitions
        self.tool_description = self.get_tool_description()
        self.tool_parameters = self.get_tool_parameters()
    
    def get_tool_description(self) -> str:
        """Load tool description from external file or constant."""
        return "Tool description with examples and usage..."
    
    def get_tool_parameters(self) -> Dict[str, Any]:
        """Load parameter schema."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform. Required."
                },
                "data": {
                    "type": "string",
                    "description": "Data parameter - accepts JSON string"
                },
                "items": {
                    "type": "string",
                    "description": "Items - comma-separated list"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of items"
                },
                "enabled": {
                    "type": "boolean",
                    "description": "Enable feature"
                }
            },
            "required": ["action"],
            "additionalProperties": False
        }
    
    def register_tools(self, mcp: "FastMCP"):
        """Register tools with MCP server."""
        
        params = self.tool_parameters["properties"]
        
        async def generic_tool(
            action: Annotated[str, Field(description=params["action"]["description"])],
            data: Annotated[str, Field(description="[OPTIONAL] " + params["data"]["description"])] = None,
            items: Annotated[str, Field(description="[OPTIONAL] " + params["items"]["description"])] = None,
            count: Annotated[int, Field(description="[OPTIONAL] " + params["count"]["description"])] = None,
            enabled: Annotated[bool, Field(description="[OPTIONAL] " + params["enabled"]["description"])] = None
        ) -> Dict[str, Any]:
            """Generic tool implementation."""
            
            # Handle JSON string conversion
            if data is not None and isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    return {"error": "Invalid JSON in data parameter"}
            
            # Handle comma-separated list
            if items is not None and isinstance(items, str):
                items = [item.strip() for item in items.split(',')]
            
            # Handle integer conversion
            if count is not None and not isinstance(count, int):
                try:
                    count = int(count)
                except (ValueError, TypeError):
                    count = 0
            
            # Handle boolean default
            if enabled is None:
                enabled = False
            
            # Delegate to actual implementation
            return await self.execute_action(
                action=action,
                data=data,
                items=items,
                count=count,
                enabled=enabled
            )
        
        # Register with MCP
        mcp.tool(description=self.tool_description)(generic_tool)
    
    async def execute_action(self, **kwargs) -> Dict[str, Any]:
        """Actual implementation logic."""
        # Implementation here
        pass
```

## Testing Parameter Types

To verify parameters display correctly:

1. Register the tool with MCP server
2. Check the tool documentation/interface
3. Verify each parameter shows the correct type (string, integer, boolean)
4. Test with various input formats to ensure conversions work

## Common Issues and Solutions

### Issue: Parameters showing as "unknown"
**Solution:** 
1. Remove Union and Optional types from signatures
2. Avoid `oneOf` and `anyOf` in JSON schemas
3. Check for global schema monkey patches that might be adding these constructs

### Issue: Schema Monkey Patch Interference
**Problem:** Global schema patches may automatically add `anyOf` to certain parameter names
**Solution:** 
1. Exclude your parameters from the patch lists in `schema_monkey_patch.py`
2. Or disable the monkey patch for specific controllers
3. Check `FLEXIBLE_ARRAY_PARAMETERS`, `FLEXIBLE_BOOLEAN_PARAMETERS`, and `FLEXIBLE_INTEGER_PARAMETERS` lists

### Issue: Complex types not recognized
**Solution:** Use simple base types and handle conversion in function body

### Issue: Required vs Optional confusion  
**Solution:** Use "[OPTIONAL]" prefix in description and `= None` default

### Issue: MCP crashes with certain type annotations
**Solution:** Avoid complex generics, use simple types

## Key Architectural Principles

### 1. Two-Stage Validation Pattern
- **Schema Level**: Only the action/operation parameter is required
- **Business Logic**: Action-specific parameters are validated in the controller
- **Benefits**: Flexibility, better error messages, MCP compatibility

### 2. Centralized Parameter Management
- All parameters defined in one place (description module)
- Reusable across documentation and code
- Single source of truth for parameter schemas

### 3. Clean Parameter Organization
```python
MANAGE_TASK_PARAMS = {
    "properties": {
        # Primary parameter (always required)
        "action": {...},
        
        # Task identification parameters
        "task_id": {...},
        "git_branch_id": {...},
        
        # Task creation/update parameters
        "title": {...},
        "description": {...},
        
        # Multi-value parameters (comma-separated)
        "assignees": {...},
        "labels": {...},
        
        # Boolean control parameters
        "include_context": {...},
        
        # Search and filter parameters
        "limit": {...},
        "offset": {...},
        
        # Additional parameters...
    },
    "required": ["action"],  # Only action required!
}
```

### 4. Schema Monkey Patch Awareness
Check and exclude your parameters from global schema patches:
```python
# schema_monkey_patch.py
FLEXIBLE_ARRAY_PARAMETERS = {
    # Remove your parameters if they're here
    'insights_found', 'tags',  # Keep these
    # 'assignees', 'labels'  # Remove these for task controller
}
```

## Migration Checklist

When updating existing controllers to this pattern:

- [ ] **Create Description Module**
  - [ ] Define TOOL_DESCRIPTION with two-stage validation explanation
  - [ ] Create PARAMETERS_DESCRIPTION dictionary
  - [ ] Build PARAMS schema with only primary parameter as required
  - [ ] Add helper functions (get_description, get_parameters)

- [ ] **Update Controller Implementation**
  - [ ] Load parameters from description module
  - [ ] Use simple types in function signature (str, int, bool)
  - [ ] Add "[OPTIONAL]" prefix to optional parameter descriptions
  - [ ] Implement type conversion in function body
  - [ ] Add two-stage validation documentation in docstrings

- [ ] **Implement Validation**
  - [ ] Create ValidationFactory for action-based validation
  - [ ] Define required parameters per action
  - [ ] Return clear error messages for missing parameters

- [ ] **Handle Type Conversions**
  - [ ] Convert comma-separated strings to lists
  - [ ] Parse string integers to int
  - [ ] Handle boolean string representations
  - [ ] Parse JSON strings to dictionaries

- [ ] **Test and Verify**
  - [ ] Check parameter display in MCP interface (no "unknown" types)
  - [ ] Test all input formats work correctly
  - [ ] Verify validation errors are clear and helpful
  - [ ] Ensure all parameters are actually used

## Benefits of This Approach

1. **Clear Type Display:** Parameters show proper types in MCP tools
2. **Flexible Input:** Accepts multiple input formats through conversion
3. **Maintainable:** Centralized parameter definitions
4. **Consistent:** Standard pattern across all controllers
5. **MCP Compatible:** Works within framework limitations

## Summary: The Complete Pattern

### Architecture Overview
```
┌─────────────────────────────────────────────────┐
│           MCP Tool Registration                  │
│                                                  │
│  1. Load centralized parameter definitions       │
│  2. Register tool with simple types              │
│  3. Only 'action' required at schema level       │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│         Stage 1: Schema Validation              │
│                                                  │
│  • MCP validates 'action' exists                │
│  • All other parameters are optional            │
│  • Simple types for MCP compatibility           │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│         Stage 2: Business Validation            │
│                                                  │
│  • ValidationFactory checks action requirements │
│  • Returns specific errors for missing params   │
│  • Handles type conversions in function body    │
└─────────────────────────────────────────────────┘
```

### Key Implementation Files
1. **manage_[feature]_description.py** - Centralized parameter definitions
2. **[feature]_mcp_controller.py** - Controller with two-stage validation
3. **factories/validation_factory.py** - Action-based validation logic
4. **validators/parameter_validator.py** - Detailed parameter validation

### Critical Rules
1. ✅ Only mark primary parameter as required in schema
2. ✅ Use simple types (str, int, bool) in function signatures
3. ✅ Add "[OPTIONAL]" prefix to optional parameter descriptions
4. ✅ Handle type conversions in function body
5. ✅ Document two-stage validation pattern in code
6. ✅ Check for schema monkey patch interference
7. ✅ Organize parameters into logical groups with comments
8. ✅ Ensure all defined parameters are actually used

## Conclusion

This complete pattern provides a robust, maintainable solution for MCP parameter handling that:
- Resolves type display issues ("unknown" parameters)
- Maintains flexibility with two-stage validation
- Provides clear, actionable error messages
- Supports multiple input formats through type conversion
- Creates a single source of truth for parameters
- Works within MCP framework limitations

By following this guide, all MCP controllers will have properly typed parameters that display correctly in tool interfaces while maintaining the flexibility needed for complex operations.