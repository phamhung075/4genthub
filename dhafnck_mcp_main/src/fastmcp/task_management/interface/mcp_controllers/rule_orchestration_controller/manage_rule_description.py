"""
Rule Management Tool Description

This module contains the comprehensive documentation for the manage_rule MCP tool.
Separated from the controller logic for better maintainability and organization.
"""

MANAGE_RULE_DESCRIPTION = """
🎛️ RULE MANAGEMENT SYSTEM - Complete rule lifecycle operations with Vision System Integration

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

📝 PRACTICAL EXAMPLES FOR AI:
1. Understanding rule system:
   - action: "info"
   - Returns: Complete rule system state, available rules, hierarchy structure

2. Analyzing before modification:
   - action: "analyze_hierarchy", target: "security_rules"
   - Returns: Dependency tree, impact analysis, modification warnings

3. Composing complex rules:
   - action: "compose_nested_rules", target: "auth_rules", content: "inherit:base_security"
   - Returns: Composed rule set with inheritance applied

4. Client synchronization:
   - action: "sync_client", target: "client_123", content: "push"
   - Returns: Sync status, conflicts resolved, performance metrics

5. Performance monitoring:
   - action: "cache_status"
   - Returns: Cache hit rates, memory usage, optimization suggestions

🔍 DECISION TREES:
IF rule_operation_type == "read":
    IF need_hierarchy:
        USE "analyze_hierarchy"
    ELIF need_dependencies:
        USE "get_dependencies"
    ELSE:
        USE "info" or "list"
ELIF rule_operation_type == "modify":
    SEQUENCE:
        1. USE "analyze_hierarchy" (understand impact)
        2. USE "validate_rule_hierarchy" (pre-check)
        3. PERFORM modification
        4. USE "compose_nested_rules" (if inheritance needed)
        5. USE "sync_client" (propagate changes)
ELIF rule_operation_type == "sync":
    IF new_client:
        USE "register_client" → "authenticate_client" → "sync_client"
    ELSE:
        USE "client_diff" → "resolve_conflicts" → "sync_client"

📊 WORKFLOW PATTERNS:
1. Rule System Discovery:
   - info → list → analyze_hierarchy → get_dependencies

2. Rule Modification Flow:
   - backup → analyze_hierarchy → modify → validate_rule_hierarchy → sync_client

3. Client Onboarding:
   - register_client → authenticate_client → sync_client → client_status

4. Conflict Resolution:
   - client_diff → analyze conflicts → resolve_conflicts → sync_client → client_status

5. Performance Optimization:
   - cache_status → client_analytics → identify bottlenecks → optimize → monitor

🔄 VISION SYSTEM FEATURES (Automatic):
• Rule pattern detection and suggestion
• Hierarchy optimization recommendations
• Conflict prediction and prevention
• Performance bottleneck identification
• Security vulnerability detection in rules
• Best practice enforcement
• Automatic rule composition optimization

💡 ENHANCED PARAMETERS:
• action: Required. The rule operation to perform (see table above)
• target: Optional. Specific rule set, client ID, or resource identifier
• content: Optional. Additional data for the operation (JSON string for complex data)

📈 RESPONSE ENHANCEMENTS:
• workflow_guidance: AI-generated guidance for next steps
• hierarchy_insights: Understanding of rule relationships
• conflict_analysis: Automatic conflict detection results
• performance_metrics: Operation timing and efficiency data
• security_analysis: Rule security implications
• optimization_suggestions: Ways to improve rule efficiency

🛡️ RULE HIERARCHY PATTERNS:
• Global Rules: Organization-wide policies and standards
• Project Rules: Project-specific configurations and overrides
• Component Rules: Component-level customizations
• Inheritance Chain: Component → Project → Global (most specific wins)

🔐 CLIENT SYNCHRONIZATION PATTERNS:
• Push Sync: Server rules pushed to clients (authoritative)
• Pull Sync: Client requests latest rules from server
• Bidirectional Sync: Merge server and client rules with conflict resolution
• Selective Sync: Sync only specific rule categories or projects

💡 BEST PRACTICES FOR AI:
• Always check rule hierarchy before modifications
• Use backup before major rule changes
• Validate hierarchy after composition operations
• Monitor cache status for performance optimization
• Regularly check client_analytics for usage patterns
• Resolve conflicts promptly to maintain consistency
• Use enhanced_info for comprehensive system understanding

⚠️ IMPORTANT NOTES:
• Rule modifications affect all dependent rules in the hierarchy
• Client synchronization requires proper authentication
• Cache invalidation happens automatically on rule changes
• Conflict resolution uses configurable merge strategies
• Performance degrades with deeply nested rule hierarchies (>10 levels)
• Always validate rule syntax before applying changes

🛑 ERROR HANDLING:
• If required fields are missing, a clear error message is returned specifying which fields are needed
• Unknown actions return an error listing valid actions
• Internal errors are logged and returned with a generic error message
• Validation failures include specific rule violations
• Sync conflicts return detailed conflict information
"""

# Modern parameter structure for MCP compatibility
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
    """Get manage rule description for use in controller."""
    return MANAGE_RULE_DESCRIPTION

# Legacy parameter descriptions for backward compatibility
MANAGE_RULE_PARAMETERS = {
    "action": "Rule management action to perform. Required. Valid: 'list', 'backup', 'restore', 'clean', 'info', 'load_core', 'parse_rule', 'analyze_hierarchy', 'get_dependencies', 'enhanced_info', 'compose_nested_rules', 'resolve_rule_inheritance', 'validate_rule_hierarchy', 'build_hierarchy', 'load_nested', 'cache_status', 'register_client', 'authenticate_client', 'sync_client', 'client_diff', 'resolve_conflicts', 'client_status', 'client_analytics'. (string)",
    "target": "Target for the action. Optional. Can be rule name, rule path, client ID, or resource identifier. Default: empty string. Examples: 'security_rules', 'client_123', 'project/auth_rules'. (string)",
    "content": "Content for the action. Optional. Can be rule content, configuration data, or operation parameters. For complex data, use JSON string format. Default: empty string. Examples: 'inherit:base_rules', '{\"merge_strategy\": \"recursive\"}'. (string)"
}