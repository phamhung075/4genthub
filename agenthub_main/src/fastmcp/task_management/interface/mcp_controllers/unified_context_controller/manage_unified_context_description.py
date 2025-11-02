"""
Unified Context Management Description and Parameters

This module contains the complete description and parameter specifications
for the unified context management tool, supporting the 4-tier hierarchy:
GLOBAL → PROJECT → BRANCH → TASK
"""

MANAGE_UNIFIED_CONTEXT_DESCRIPTION = """
🔗 UNIFIED CONTEXT MANAGEMENT - 4-Tier Hierarchical Operations

**Purpose**: Manage contexts across 4 tiers (Global → Project → Branch → Task) with unified API, auto-inheritance, smart caching, per-user isolation.

**Use For**: Context operations, cross-session persistence, hierarchical data, agent coordination, multi-tier sharing.

**Hierarchy**: GLOBAL (per-user) → PROJECT → BRANCH → TASK (each inherits from parent)

| Action | Required | Optional | Description |
|--------|----------|----------|-------------|
| create | action, level, context_id | data, user_id, project_id, git_branch_id | Create context at level |
| get | action, level, context_id | include_inherited, user_id | Retrieve context with inheritance |
| update | action, level, context_id | data, propagate_changes, user_id | Update with propagation |
| delete | action, level, context_id | user_id | Remove context |
| resolve | action, level, context_id | force_refresh, include_inherited, user_id | Resolve full inheritance chain |
| delegate | action, level, context_id, delegate_to | delegate_data, delegation_reason, user_id | Move data between levels |
| add_insight | action, level, context_id, content | category, importance, agent, user_id | Add categorized insight |
| add_progress | action, level, context_id, content | agent, user_id | Add progress update |
| list | action, level | filters, user_id | List contexts with filtering |

**Level Values**: 'global' (user-scoped), 'project', 'branch', 'task'

**context_id Mapping**: user_id (global), project_id (project), git_branch_id (branch), task_id (task)

**Key Features**: Unified API | 4-tier inheritance | Auto-inheritance | Smart caching | Change propagation | Delegation queue | Backward compatible

**Critical Parameters**:
- force_refresh: Bypass cache, force fresh retrieval
- include_inherited: Access full parent chain
- propagate_changes: Cascade updates to children
- data/filters: JSON string or dict (auto-parsed)

**Usage Pattern**:
```python
manage_context(action="{action}", level="{global|project|branch|task}", context_id="{id}", data={...})
```

**Example**: `manage_context(action="create", level="project", context_id="proj123", data={"key": "value"})`

**Backward Compatibility**: Legacy params auto-convert (task_id→context_id, data_*→data object, etc.)

**Error Handling**: Validates level/context_id compatibility | Clear error messages | Auto-creation options | Detailed validation errors
"""

MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION = {
    "action": "Context management action to perform. Valid: 'create', 'get', 'update', 'delete', 'resolve', 'delegate', 'add_insight', 'add_progress', 'list'",
    "level": "[OPTIONAL] Context hierarchy level. Valid: 'global' (user-scoped), 'project', 'branch', 'task'. Determines inheritance scope and data isolation",
    "context_id": "[OPTIONAL] Context identifier appropriate for the level. Use user_id for global, project_id for project, git_branch_id for branch, task_id for task",
    "data": "[OPTIONAL] Context data as JSON string (automatically parsed). Supports nested structures, arrays, and complex data types",
    "user_id": "[OPTIONAL] User identifier for authentication and audit trails. Used for user-scoped global contexts and access control",
    "project_id": "[OPTIONAL] Project identifier for project-level context operations. Required for project, branch, and task level operations when not inferrable",
    "git_branch_id": "[OPTIONAL] Git branch identifier for branch-level context operations. Required for branch and task level operations",
    "force_refresh": "[OPTIONAL] Bypass cache and force fresh data retrieval. Use when cache consistency is critical. Accepts: 'true', 'false', '1', '0'",
    "include_inherited": "[OPTIONAL] Include inherited data from parent levels in response. Enables complete context resolution with inheritance chain. Accepts: 'true', 'false', '1', '0'",
    "propagate_changes": "[OPTIONAL] Automatically cascade changes to child levels in hierarchy. Maintains consistency across hierarchy. Accepts: 'true', 'false', '1', '0'",
    "delegate_to": "[OPTIONAL] Target level for context delegation operations. Valid: 'global', 'project', 'branch', 'task'. Used with delegate action",
    "delegate_data": "[OPTIONAL] Specific data to delegate to target level as JSON string. Can be subset of source context or completely new data",
    "delegation_reason": "[OPTIONAL] Reason for context delegation for audit trails and team communication. Helps track why data was moved between hierarchy levels",
    "content": "[OPTIONAL] Content for insight or progress operations. String content that will be categorized and added to the specified context level",
    "category": "[OPTIONAL] Insight category for add_insight operations. Valid: 'technical', 'business', 'performance', 'risk', 'discovery'",
    "importance": "[OPTIONAL] Importance level for insights and progress updates. Valid: 'low', 'medium', 'high', 'critical'",
    "agent": "[OPTIONAL] Agent identifier that created the insight or progress update. String identifier for tracking agent contributions",
    "filters": "[OPTIONAL] Filter criteria for list operations as JSON string. Supports filtering by data fields, creation dates, agents, and other metadata",
}

MANAGE_UNIFIED_CONTEXT_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION["action"],
        },
        # Context hierarchy parameters
        "level": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION["level"],
        },
        "context_id": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION["context_id"],
        },
        # Data and content parameters
        "data": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION["data"],
        },
        "content": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION["content"],
        },
        # Authentication and identification
        "user_id": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION["user_id"],
        },
        "project_id": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION["project_id"],
        },
        "git_branch_id": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION[
                "git_branch_id"
            ],
        },
        # Operation modifiers (handled as strings)
        "force_refresh": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION[
                "force_refresh"
            ],
        },
        "include_inherited": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION[
                "include_inherited"
            ],
        },
        "propagate_changes": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION[
                "propagate_changes"
            ],
        },
        # Delegation parameters
        "delegate_to": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION["delegate_to"],
        },
        "delegate_data": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION[
                "delegate_data"
            ],
        },
        "delegation_reason": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION[
                "delegation_reason"
            ],
        },
        # Insight and progress parameters
        "category": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION["category"],
        },
        "importance": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION["importance"],
        },
        "agent": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION["agent"],
        },
        # List and filter parameters
        "filters": {
            "type": "string",
            "description": MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION["filters"],
        },
    },
    "required": [
        "action"
    ],  # Only action required at schema level - business logic validates per action
    "additionalProperties": False,
}


def get_manage_unified_context_parameters():
    """Get manage unified context parameters for use in controller."""
    return MANAGE_UNIFIED_CONTEXT_PARAMS["properties"]


def get_manage_unified_context_description():
    """Get manage unified context description for use in controller."""
    return MANAGE_UNIFIED_CONTEXT_DESCRIPTION


# Legacy parameter descriptions for backward compatibility
MANAGE_UNIFIED_CONTEXT_PARAMETERS = {
    "action": "Context management action to perform. Valid: 'create', 'get', 'update', 'delete', 'resolve', 'delegate', 'add_insight', 'add_progress', 'list'. Each action operates within the specified hierarchy level",
    "level": "Context hierarchy level. Valid: 'global' (user-scoped), 'project' (project-specific), 'branch' (git branch), 'task' (task-specific). Determines inheritance scope and data isolation",
    "context_id": "Context identifier appropriate for the level. Use user_id for global, project_id for project, git_branch_id for branch, task_id for task. Must match the specified level",
    "data": "Context data as dictionary object or JSON string (automatically parsed). Supports nested structures, arrays, and complex data types. Legacy data_* parameters are automatically converted",
    "user_id": "User identifier for authentication and audit trails. Used for user-scoped global contexts and access control across all hierarchy levels",
    "project_id": "Project identifier for project-level context operations. Required for project, branch, and task level operations when not inferrable from context",
    "git_branch_id": "Git branch identifier for branch-level context operations. Required for branch and task level operations when creating branch-specific contexts",
    "force_refresh": "Bypass cache and force fresh data retrieval. Boolean, default: false. Use when cache consistency is critical or after external data changes",
    "include_inherited": "Include inherited data from parent levels in response. Boolean, default: false. Enables complete context resolution with inheritance chain",
    "propagate_changes": "Automatically cascade changes to child levels in hierarchy. Boolean, default: true. Maintains consistency across hierarchy when updating parent contexts",
    "delegate_to": "Target level for context delegation operations. Valid: 'global', 'project', 'branch', 'task'. Used with delegate action to move context data between levels",
    "delegate_data": "Specific data to delegate to target level as dictionary object or JSON string. Can be subset of source context or completely new data structure",
    "delegation_reason": "Reason for context delegation for audit trails and team communication. Helps track why data was moved between hierarchy levels",
    "content": "Content for insight or progress operations. String content that will be categorized and added to the specified context level",
    "category": "Insight category for add_insight operations. Valid: 'technical', 'business', 'performance', 'risk', 'discovery'. Helps organize and filter insights",
    # Legacy parameters (marked for backward compatibility)
    "task_id": "Legacy: Context identifier for task-specific contexts. Automatically converted to context_id with level='task'. Use context_id with level parameter instead",
    "data_title": "Legacy: Context title data. Automatically merged into data object as {'title': value}. Use data parameter with structured content instead",
    "data_description": "Legacy: Context description data. Automatically merged into data object as {'description': value}. Use data parameter with structured content instead",
    "data_status": "Legacy: Context status data. Automatically merged into data object as {'status': value}. Use data parameter with structured content instead",
    "data_priority": "Legacy: Context priority data. Automatically merged into data object as {'priority': value}. Use data parameter with structured content instead",
    "data_tags": "Legacy: Context tags data. Automatically merged into data object as {'tags': value}. Use data parameter with structured content instead",
    "data_metadata": "Legacy: Context metadata. Automatically merged into data object as {'metadata': value}. Use data parameter with structured content instead",
    "importance": "Importance level for insights and progress updates. Valid: 'low', 'medium', 'high', 'critical'. Used for prioritization and filtering",
    "agent": "Agent identifier that created the insight or progress update. String identifier for tracking agent contributions and coordination",
    "filters": "Filter criteria for list operations as dictionary object or JSON string. Supports filtering by data fields, creation dates, agents, and other metadata",
}
