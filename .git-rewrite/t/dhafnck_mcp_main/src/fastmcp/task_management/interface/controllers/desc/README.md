# Tool Description Organization

This directory contains tool descriptions separated from controller logic for better maintainability, organization, and reusability.

## Structure

```
desc/
├── README.md                           # This documentation
├── description_loader.py               # Utility for loading descriptions
├── __init__.py                         # Package initialization
├── task/                               # Task-related descriptions
│   ├── __init__.py
│   └── tool/                          # Individual tool descriptions
│       ├── __init__.py
│       └── manage_task_description.py  # manage_task tool description
├── subtask/                            # Subtask-related descriptions
│   ├── __init__.py
│   └── manage_subtask_description.py   # manage_subtask tool description
└── agent/                              # Agent-related descriptions
    ├── __init__.py
    └── call_agent_description.py       # call_agent tool description
```

## Purpose

### Benefits of Separation

1. **Maintainability**: Tool descriptions can be updated without modifying controller code
2. **Reusability**: Descriptions can be shared across multiple controllers or tools
3. **Organization**: Clear separation between documentation and logic
4. **Version Control**: Changes to descriptions can be tracked independently
5. **Collaboration**: Documentation can be edited by different team members
6. **Testing**: Descriptions can be validated and tested separately

### Clean Code Principles

- **Single Responsibility**: Controllers focus on MCP protocol, descriptions focus on documentation
- **Open/Closed**: Easy to extend with new descriptions without modifying existing code
- **DRY**: Avoid duplicating comprehensive documentation across files
- **Separation of Concerns**: Business logic, protocol handling, and documentation are separated

## Usage

### Loading Descriptions in Controllers

```python
from .desc import description_loader

class MyController:
    def register_tools(self, mcp: "FastMCP"):
        # Load all descriptions using the new pattern
        descriptions = self._get_my_tool_descriptions()
        
        # Access specific tool descriptions
        manage_task_desc = descriptions["manage_task"]
        
        @mcp.tool()
        def my_tool(
            param: Annotated[str, Field(description=manage_task_desc["parameters"]["param"])]
        ) -> Dict[str, Any]:
            f"""{manage_task_desc["description"]}"""
            # Tool implementation here

    def _get_my_tool_descriptions(self) -> Dict[str, Any]:
        """
        Flatten tool descriptions for robust access.
        """
        all_desc = description_loader.get_all_descriptions()
        flat = {}
        # Look for your tool in any subdict (e.g., all_desc['task']['manage_task'])
        for sub in all_desc.values():
            if isinstance(sub, dict) and "manage_task" in sub:
                flat["manage_task"] = sub["manage_task"]
        return flat
```

### Adding New Descriptions

1. **Create Description File**: Add new `.py` file in appropriate subdirectory
2. **Define Constants**: Use `TOOL_NAME_DESCRIPTION` and `TOOL_NAME_PARAMETERS` constants
3. **Update Loader**: Add loading logic to `description_loader.py`
4. **Use in Controller**: Import and use via the description loader

### Description File Format

Each description file should contain:

```python
"""
Tool Name Description

Brief description of what this tool does.
"""

TOOL_NAME_DESCRIPTION = """🔧 TOOL TITLE - Brief description

⭐ WHAT IT DOES: Comprehensive explanation
📋 WHEN TO USE: Usage scenarios  
🎯 CRITICAL FOR: Critical use cases

🔧 FUNCTIONALITY:
• Feature 1: Description
• Feature 2: Description

💡 ACTION TYPES:
• 'action1': Description
• 'action2': Description

⚠️ USAGE GUIDELINES:
• Guideline 1
• Guideline 2

🎯 USE CASES:
• Use case 1
• Use case 2
"""

TOOL_NAME_PARAMETERS = {
    "param1": "Detailed parameter description with validation rules",
    "param2": "Another parameter description",
    # ... more parameters
}
```

## Integration with Controllers

### Before (Embedded Descriptions)

```python
@mcp.tool()
def manage_task(
    action: Annotated[str, Field(description="Long embedded description...")]
) -> Dict[str, Any]:
    """Long embedded docstring with comprehensive documentation..."""
    return self.manage_task(action)
```

### After (External Descriptions)

```python
@mcp.tool()
def manage_task(
    action: Annotated[str, Field(description=manage_task_desc["parameters"]["action"])]
) -> Dict[str, Any]:
    f"""{manage_task_desc["description"]}"""
    return self.manage_task(action)
```

## Benefits in Practice

### For Developers
- **Focused Code**: Controllers contain only business logic and protocol handling
- **Easy Updates**: Change documentation without touching controller code
- **Better Testing**: Test descriptions and logic separately
- **Code Reviews**: Smaller, focused changes

### For Documentation
- **Comprehensive**: Full documentation without cluttering code
- **Consistent**: Standardized format across all tools
- **Searchable**: Easy to find and reference specific documentation
- **Maintainable**: Update documentation independently

### For Teams
- **Collaboration**: Different team members can work on docs vs code
- **Specialization**: Technical writers can focus on descriptions
- **Quality**: Dedicated attention to documentation quality
- **Consistency**: Enforced documentation standards

## Best Practices

1. **Naming Convention**: Use `TOOL_NAME_DESCRIPTION` and `TOOL_NAME_PARAMETERS`
2. **Emoji Headers**: Use consistent emoji headers for visual organization
3. **Structured Sections**: Follow the established section format
4. **Parameter Details**: Include validation rules, formats, and examples
5. **Error Handling**: Graceful fallbacks in description loader
6. **Documentation**: Keep this README updated with new patterns

## Migration Guide

To migrate existing embedded descriptions:

1. **Extract Description**: Copy docstring to new description file
2. **Extract Parameters**: Copy Field descriptions to parameters dictionary
3. **Update Controller**: Replace embedded text with loader calls
4. **Test**: Verify tools still work with external descriptions
5. **Clean Up**: Remove old embedded descriptions

This separation enables better maintainability while preserving the comprehensive documentation that makes tools easy to understand and use.

## Agent Tool Documentation

### Location
- `desc/agent/call_agent_description.py`: Contains the documentation for the call_agent tool.
- `desc/agent/__init__.py`: Package marker for agent tool descriptions.

### Structure
- Follows the same pattern as task and subtask tool documentation.
- Includes high-level overview, action types, data structure, usage guidelines, and parameter descriptions.

### Loader Integration
- The recursive description loader automatically picks up all agent tool documentation in the `agent/` directory.
- Access via `description_loader.get_all_descriptions()['agent']['call_agent']`. 