"""
Cursor Rules Tool Description

This module contains the comprehensive documentation for the cursor rules MCP tool.
Separated from the controller logic for better maintainability and organization.
"""

CURSOR_RULES_DESCRIPTION = """
🎛️ CURSOR RULES MANAGEMENT SYSTEM - System-wide Rule Operations and Orchestration

⭐ WHAT IT DOES: Manages the complete lifecycle of cursor rules including loading, parsing, hierarchy analysis, composition, client synchronization, and intelligent caching. Provides comprehensive rule orchestration for AI agents.
📋 WHEN TO USE: Rule operations, system configuration, rule hierarchy management, client synchronization, and administrative tasks.
🎯 CRITICAL FOR: System-wide rule management, hierarchical rule composition, multi-client synchronization, and rule governance.
🚀 ENHANCED FEATURES: Nested rule composition, inheritance resolution, client-specific rule delivery, conflict resolution, and performance analytics.

🤖 AI USAGE GUIDELINES:
• ALWAYS use 'info' or 'enhanced_info' first to understand the current rule state
• USE 'analyze_hierarchy' before making changes to understand dependencies
• BACKUP rules before making significant changes using 'backup' action
• COMPOSE nested rules using 'compose_nested_rules' for inheritance
• SYNC clients after rule updates using 'sync_client' action
• VALIDATE rule hierarchy after changes using 'validate_rule_hierarchy'

| Action                    | Required Parameters | Optional Parameters | Description                                      |
|---------------------------|--------------------|---------------------|--------------------------------------------------|
| list                      | action             | target, content     | List all available rules in the system           |
| backup                    | action             | target, content     | Create backup of current rules                   |
| restore                   | action             | target, content     | Restore rules from backup                        |
| clean                     | action             | target, content     | Clean up orphaned or invalid rules               |
| info                      | action             | target, content     | Get basic rule system information                |
| load_core                 | action             | target, content     | Load core system rules                           |
| parse_rule                | action             | target, content     | Parse and validate a specific rule               |
| analyze_hierarchy         | action             | target, content     | Analyze rule dependency hierarchy                |
| get_dependencies          | action             | target, content     | Get dependencies for a specific rule             |
| enhanced_info             | action             | target, content     | Get comprehensive rule system info               |
| compose_nested_rules      | action             | target, content     | Compose rules with inheritance                   |
| resolve_rule_inheritance  | action             | target, content     | Resolve inheritance chain for a rule             |
| validate_rule_hierarchy   | action             | target, content     | Validate entire rule hierarchy                   |
| build_hierarchy           | action             | target, content     | Build complete rule hierarchy tree               |
| load_nested               | action             | target, content     | Load rules with nested dependencies              |
| cache_status              | action             | target, content     | Get rule cache status and metrics                |
| register_client           | action             | target, content     | Register new client for rule sync                |
| authenticate_client       | action             | target, content     | Authenticate client for operations               |
| sync_client               | action             | target, content     | Synchronize rules with a client                  |
| client_diff               | action             | target, content     | Get differences between client/server            |
| resolve_conflicts         | action             | target, content     | Resolve rule conflicts for client                |
| client_status             | action             | target, content     | Get client synchronization status                |
| client_analytics          | action             | target, content     | Get client usage analytics                       |

🔍 DECISION TREES FOR AI:

```
RULE OPERATION DECISION TREE:
IF need_to_understand_rules:
    IF detailed_info_needed:
        USE action="enhanced_info"
    ELSE:
        USE action="info"
ELIF modifying_rules:
    IF major_changes:
        FIRST: action="backup"
        THEN: action="analyze_hierarchy"
        THEN: make_changes
        FINALLY: action="validate_rule_hierarchy"
    ELSE:
        make_changes
        THEN: action="sync_client" (if clients exist)
ELIF investigating_issues:
    IF performance_issues:
        USE action="cache_status"
    ELIF hierarchy_issues:
        USE action="analyze_hierarchy"
    ELIF client_issues:
        USE action="client_status"
```

```
CLIENT SYNCHRONIZATION DECISION TREE:
IF new_client:
    USE action="register_client"
ELIF existing_client:
    IF authentication_needed:
        USE action="authenticate_client"
    IF checking_differences:
        USE action="client_diff"
    IF conflicts_exist:
        USE action="resolve_conflicts"
    ELSE:
        USE action="sync_client"
```

📊 WORKFLOW PATTERNS:

1. **Initial Rule System Setup**:
   ```
   action="load_core" → action="build_hierarchy" → action="enhanced_info"
   ```

2. **Rule Modification Workflow**:
   ```
   action="backup" → action="analyze_hierarchy" → modify_rules → 
   action="validate_rule_hierarchy" → action="sync_client"
   ```

3. **Client Onboarding Workflow**:
   ```
   action="register_client", content={"client_id": "new_client", "config": {...}} →
   action="authenticate_client", target="new_client" →
   action="sync_client", target="new_client"
   ```

4. **Troubleshooting Workflow**:
   ```
   action="enhanced_info" → action="analyze_hierarchy" → 
   action="get_dependencies", target="problematic_rule" →
   action="cache_status" → action="client_analytics"
   ```

5. **Rule Composition Workflow**:
   ```
   action="parse_rule", target="base_rule.mdc" →
   action="compose_nested_rules", target="derived_rule.mdc" →
   action="resolve_rule_inheritance", target="derived_rule.mdc"
   ```

💡 ENHANCED PARAMETERS:
• action: The rule management operation to perform (see table above)
• target: Specifies the rule, client, or resource for the action
  - For rule operations: rule file path (e.g., "rules/custom.mdc")
  - For client operations: client identifier (e.g., "client_123")
  - For hierarchy operations: rule name or path
• content: Additional data for the operation
  - For register_client: JSON with client configuration
  - For sync_client: JSON with sync options
  - For restore: backup identifier or path

📈 RESPONSE ENHANCEMENTS:
• workflow_guidance: AI-friendly next steps and recommendations
• metadata: Operation timestamp, affected resources, performance metrics
• diagnostics: Detailed information for troubleshooting
• suggestions: Proactive recommendations based on operation results
• impact_analysis: How the operation affects the system
• client_impact: Specific impacts on synchronized clients

🔄 CACHING AND PERFORMANCE:
• Rule cache automatically maintained for performance
• Use 'cache_status' to monitor cache health
• Cache invalidation happens automatically on rule changes
• Client-specific caches optimize synchronization

🔐 SECURITY CONSIDERATIONS:
• Client authentication required for sensitive operations
• Rule modifications tracked in audit log
• Backup/restore operations require elevated permissions
• Conflict resolution maintains data integrity

💡 BEST PRACTICES FOR AI:
• Always check current state before modifications (info/enhanced_info)
• Create backups before major changes
• Validate hierarchy after rule modifications
• Monitor client synchronization status regularly
• Use analytics to understand rule usage patterns
• Resolve conflicts promptly to maintain consistency
• Document rule changes in version control

⚠️ IMPORTANT NOTES:
• Rule changes may impact multiple clients - always check dependencies
• Hierarchical rules inherit properties - understand inheritance chains
• Client synchronization is asynchronous - check status after sync
• Cache warming may be needed after major changes
• Backup retention follows system policies

🛑 ERROR HANDLING:
• Missing required fields return clear error messages with field names
• Unknown actions return list of valid actions
• Validation failures include specific rule violations
• Client errors include synchronization state for recovery
• All errors include actionable resolution steps
"""

# Parameter descriptions for the cursor rules tool
CURSOR_RULES_PARAMETERS = {
    "action": "Rule management action to perform. Required. Valid actions include: list, backup, restore, clean, info, load_core, parse_rule, analyze_hierarchy, get_dependencies, enhanced_info, compose_nested_rules, resolve_rule_inheritance, validate_rule_hierarchy, build_hierarchy, load_nested, cache_status, register_client, authenticate_client, sync_client, client_diff, resolve_conflicts, client_status, client_analytics. (string)",
    "target": "Target for the action - can be a rule path, client ID, or specific resource depending on the action. Optional, defaults to empty string. Examples: 'rules/custom.mdc' for rule operations, 'client_123' for client operations. (string)",
    "content": "Additional content or configuration for the action. Format depends on action type. Optional, defaults to empty string. For register_client: JSON client config. For sync operations: JSON sync options. For restore: backup identifier. (string)"
}