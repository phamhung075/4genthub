"""
Rule Management Tool Description
This file contains the description for the manage_rule MCP tool.
"""

MANAGE_RULE_DESCRIPTION = """
🎯 RULE MANAGEMENT SYSTEM - Complete rule lifecycle operations with Vision System Integration

⭐ WHAT IT DOES: Handles all rule operations including CRUD, search, dependencies, and workflow management. Automatically enriches rules with vision insights, hierarchy analysis, and intelligent pattern detection.
📋 WHEN TO USE: For any rule-related operation from creation to synchronization, including hierarchy analysis and client management.
🎯 CRITICAL FOR: Rule governance, hierarchical rule systems, client synchronization, and maintaining development standards.

🤖 AI USAGE GUIDELINES:
• ALWAYS use 'info' action first to understand current rule system state
• USE 'analyze_hierarchy' before modifying rules to understand dependencies
• APPLY 'compose_nested_rules' for rule inheritance and composition
• LEVERAGE 'client_sync' for distributed rule consistency
• MONITOR with 'cache_status' and 'client_analytics' for performance

| Action                    | Required Parameters | Optional Parameters | Description                                      |
|---------------------------|--------------------|---------------------|--------------------------------------------------|
| list                      | (none)             | target, content     | List all available rules in the system           |
| backup                    | (none)             | target, content     | Create backup of current rule configuration      |
| restore                   | (none)             | target, content     | Restore rules from backup                        |
| clean                     | (none)             | target, content     | Clean up obsolete or invalid rules               |
| info                      | (none)             | target, content     | Get comprehensive rule system information        |
| load_core                 | (none)             | target, content     | Load core system rules                           |
| parse_rule                | (none)             | target, content     | Parse and validate rule syntax                   |
| analyze_hierarchy         | (none)             | target, content     | Analyze rule hierarchy and dependencies          |
| get_dependencies          | (none)             | target, content     | Get rule dependency graph                        |
| enhanced_info             | (none)             | target, content     | Get enhanced rule info with insights             |
| compose_nested_rules      | (none)             | target, content     | Compose rules with inheritance                   |
| resolve_rule_inheritance  | (none)             | target, content     | Resolve rule inheritance chain                   |
| validate_rule_hierarchy   | (none)             | target, content     | Validate rule hierarchy integrity                |
| build_hierarchy           | (none)             | target, content     | Build complete rule hierarchy                    |
| load_nested               | (none)             | target, content     | Load nested rule structures                      |
| cache_status              | (none)             | target, content     | Get rule cache status and metrics                |
| register_client           | (none)             | target, content     | Register client for rule synchronization         |
| authenticate_client       | (none)             | target, content     | Authenticate client for secure access            |
| sync_client               | (none)             | target, content     | Synchronize rules with client                    |
| client_diff               | (none)             | target, content     | Get differences between server and client        |
| resolve_conflicts         | (none)             | target, content     | Resolve rule conflicts automatically             |
| client_status             | (none)             | target, content     | Get client synchronization status                |
| client_analytics          | (none)             | target, content     | Get client usage analytics                       |
"""

MANAGE_RULE_PARAMETERS_DESCRIPTION = {
    "action": "Rule management action to perform. Valid: 'list', 'backup', 'restore', 'clean', 'info', 'load_core', 'parse_rule', 'analyze_hierarchy', 'get_dependencies', 'enhanced_info', 'compose_nested_rules', 'resolve_rule_inheritance', 'validate_rule_hierarchy', 'build_hierarchy', 'load_nested', 'cache_status', 'register_client', 'authenticate_client', 'sync_client', 'client_diff', 'resolve_conflicts', 'client_status', 'client_analytics'",
    "target": "[OPTIONAL] Target for the action. Can be rule name, rule path, client ID, or resource identifier. Examples: 'security_rules', 'client_123', 'project/auth_rules'",
    "content": "[OPTIONAL] Content for the action. Can be rule content, configuration data, or operation parameters. For complex data, use JSON string format. Examples: 'inherit:base_rules', '{\"merge_strategy\": \"recursive\"}'"
}

MANAGE_RULE_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": MANAGE_RULE_PARAMETERS_DESCRIPTION["action"]
        },
        
        # Optional parameters
        "target": {
            "type": "string",
            "description": MANAGE_RULE_PARAMETERS_DESCRIPTION["target"]
        },
        "content": {
            "type": "string",
            "description": MANAGE_RULE_PARAMETERS_DESCRIPTION["content"]
        }
    },
    "required": ["action"],  # Only action required at schema level - business logic validates per action
    "additionalProperties": False
}

def get_manage_rule_parameters():
    """Get manage rule parameters for use in controller."""
    return MANAGE_RULE_PARAMS["properties"]

def get_manage_rule_description():
    """Return the manage_rule tool description"""
    return {
        "description": MANAGE_RULE_DESCRIPTION,
        "parameters": {
            "action": "Rule management action to perform. Required. Valid: 'list', 'backup', 'restore', 'clean', 'info', 'load_core', 'parse_rule', 'analyze_hierarchy', 'get_dependencies', 'enhanced_info', 'compose_nested_rules', 'resolve_rule_inheritance', 'validate_rule_hierarchy', 'build_hierarchy', 'load_nested', 'cache_status', 'register_client', 'authenticate_client', 'sync_client', 'client_diff', 'resolve_conflicts', 'client_status', 'client_analytics'. (string)",
            "target": "Target for the action. Optional. Can be rule name, rule path, client ID, or resource identifier. Default: empty string. Examples: 'security_rules', 'client_123', 'project/auth_rules'. (string)",
            "content": "Content for the action. Optional. Can be rule content, configuration data, or operation parameters. For complex data, use JSON string format. Default: empty string. Examples: 'inherit:base_rules', '{\"merge_strategy\": \"recursive\"}'. (string)"
        }
    }