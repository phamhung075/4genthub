"""
Unified Context Management Tool Description

This module contains the comprehensive documentation for the unified manage_context MCP tool.
Handles all context operations across the entire 4-tier hierarchy with a single, coherent API.
"""

MANAGE_UNIFIED_CONTEXT_DESCRIPTION = """
🔗 UNIFIED CONTEXT MANAGEMENT SYSTEM - Complete 4-Tier Context Operations

⭐ WHAT IT DOES: Manages contexts across Global → Project → Branch → Task hierarchy with full inheritance, delegation, caching, and validation support through a single, unified API.
📋 WHEN TO USE: Any context operation - creation, retrieval, updates, delegation, insights, progress tracking across all hierarchy levels.
🎯 CRITICAL FOR: Unified context management, hierarchical data organization, cross-level pattern sharing, and AI workflow orchestration.

🏗️ HIERARCHY STRUCTURE:

GLOBAL (User-scoped: per-user global context)
   ↓ inherits to
PROJECT (ID: project_id)  
   ↓ inherits to
BRANCH (ID: git_branch_id)
   ↓ inherits to
TASK (ID: task_id)


| Action              | Required Parameters         | Optional Parameters                | Description                                      |
|--------------------|----------------------------|------------------------------------|--------------------------------------------------|
| create             | level, context_id          | data, user_id, project_id, git_branch_id | Create new context at specified level            |
| get                | level, context_id          | include_inherited, force_refresh, user_id, project_id, git_branch_id | Retrieve context with optional inheritance       |
| update             | level, context_id          | data, propagate_changes, user_id, project_id, git_branch_id | Update context and optionally propagate          |
| delete             | level, context_id          | user_id, project_id, git_branch_id | Delete context at specified level                |
| resolve            | level, context_id          | force_refresh, user_id, project_id, git_branch_id | Get fully resolved context with inheritance chain |
| delegate           | level, context_id, delegate_to | delegate_data, delegation_reason, user_id, project_id, git_branch_id | Delegate context data to higher level |
| add_insight        | level, context_id, content | category, importance, agent, user_id, project_id, git_branch_id | Add insight to context |
| add_progress       | level, context_id, content | agent, user_id, project_id, git_branch_id | Add progress update to context |
| list               | level                      | filters, user_id, project_id, git_branch_id | List contexts at specified level |

🎯 LEVEL PARAMETER:
• 'global': User-scoped global context (each user has their own)
• 'project': Project-level contexts 
• 'branch': Git branch contexts
• 'task': Task-specific contexts

💡 USAGE GUIDELINES:
• Always specify 'level' parameter to indicate which hierarchy tier
• Use 'context_id' appropriate for the level (e.g., task_id for task level)
• Inheritance flows from higher to lower levels automatically
• Use 'resolve' action for complete context with all inherited data
• Delegate patterns upward when they're reusable at higher levels

🔄 KEY FEATURES:
• **Unified API**: Single tool for all context operations
• **Full Hierarchy Support**: Works seamlessly across all 4 tiers
• **Automatic Inheritance**: Lower levels inherit from higher levels
• **Smart Caching**: Performance optimization with dependency tracking
• **Change Propagation**: Updates can cascade to dependent contexts
• **Delegation Queue**: Manual review for upward delegations
• **Backward Compatible**: Supports legacy parameter formats

📊 ADVANCED PARAMETERS:
• force_refresh: Bypass cache for fresh data (default: false)
• include_inherited: Include inherited data in response (default: false)
• propagate_changes: Cascade updates to dependents (default: true)
• delegate_to: Target level for delegation ('global', 'project', 'branch')
• filters: JSON object for list filtering
• data: Accepts dictionary object OR JSON string (automatically parsed)

🚀 EXAMPLE USAGE:

# Create task context (Dictionary format)
action="create", level="task", context_id="task-123", data={"title": "Implement feature"}

# Create task context (JSON string format - NEW!)
action="create", level="task", context_id="task-123", data='{"title": "Implement feature"}'

# Create task context (Legacy parameter format)
action="create", level="task", context_id="task-123", data_title="Implement feature", data_description="Feature details"

# Get with inheritance
action="get", level="task", context_id="task-123", include_inherited=true

# Update with JSON string
action="update", level="task", context_id="task-123", data='{"status": "completed", "progress": 100}'

# Delegate pattern to project
action="delegate", level="task", context_id="task-123", delegate_to="project", 
delegate_data={"pattern": "auth_flow"}, delegation_reason="Reusable across tasks"

# Add insight
action="add_insight", level="task", context_id="task-123", 
content="Found optimization", category="performance", importance="high"


⚠️ BACKWARD COMPATIBILITY:
The tool maintains compatibility with legacy parameters:
• task_id → context_id (when level="task")
• data_title, data_description, etc. → reconstructed into data object
• Legacy actions mapped to new unified operations

🛡️ ERROR HANDLING:
• Validates level and context_id combinations
• Checks required parameters per action
• Provides clear error messages with suggestions
• Maintains transactional integrity
"""

# Parameter descriptions for Pydantic field annotations
MANAGE_UNIFIED_CONTEXT_PARAMETERS = {
    "action": "Context operation to perform. Valid: create, get, update, delete, resolve, delegate, add_insight, add_progress, list",
    "level": "Context hierarchy level: global, project, branch, task. Default: task",
    "context_id": "Context identifier appropriate for the level (e.g., task_id for task level, project_id for project level)",
    "data": "Context data for create/update operations. Accepts dictionary object OR JSON string (automatically parsed). Structure varies by level",
    "user_id": "User identifier for context scoping. Optional, uses default if not provided",
    "project_id": "Project identifier for scoping. Auto-detected from task/branch if not provided",
    "git_branch_id": "Git branch UUID for scoping. Auto-detected from task if not provided",
    "force_refresh": "Force refresh from source, bypassing cache. Boolean. Default: false",
    "include_inherited": "Include inherited context data from parent levels. Boolean. Default: false",
    "propagate_changes": "Propagate changes to dependent contexts. Boolean. Default: true",
    "delegate_to": "Target level for delegation: global, project, branch. Must be higher than source level",
    "delegate_data": "Data to delegate to higher level. Dictionary format. Usually patterns or reusable components",
    "delegation_reason": "Explanation for why this delegation is valuable at the higher level",
    "content": "Content for add_insight/add_progress operations. String",
    "category": "Category for insights: technical, business, performance, risk, discovery",
    "importance": "Importance level: low, medium, high, critical. Default: medium",
    "agent": "Agent identifier performing the operation",
    "filters": "Filter criteria for list operation. Dictionary format",
    # Legacy parameters for backward compatibility
    "task_id": "Legacy: Task ID (use context_id with level='task' instead)",
    "data_title": "Legacy: Context title (use data.title instead)",
    "data_description": "Legacy: Context description (use data.description instead)",
    "data_status": "Legacy: Context status (use data.status instead)",
    "data_priority": "Legacy: Context priority (use data.priority instead)",
    "data_tags": "Legacy: Context tags (use data.tags instead)",
    "data_metadata": "Legacy: Context metadata (use data.metadata instead)"
}

# Export convenience function
def get_unified_context_description():
    """Get the complete unified context management description."""
    return MANAGE_UNIFIED_CONTEXT_DESCRIPTION

def get_unified_context_parameters():
    """Get the parameter descriptions for unified context management."""
    return MANAGE_UNIFIED_CONTEXT_PARAMETERS