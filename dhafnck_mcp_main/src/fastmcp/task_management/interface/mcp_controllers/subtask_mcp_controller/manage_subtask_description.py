"""
Subtask Management Tool Description

This module contains the comprehensive documentation for the manage_subtask MCP tool.
Separated from the controller logic for better maintainability and organization.
"""

def get_subtask_description() -> str:
    """Get the subtask management tool description"""
    return MANAGE_SUBTASK_DESCRIPTION


MANAGE_SUBTASK_DESCRIPTION = """
🔧 SUBTASK MANAGEMENT SYSTEM - Hierarchical Task Decomposition with Automatic Context Updates

⭐ WHAT IT DOES: Manages subtasks within parent tasks for hierarchical task breakdown and granular progress tracking. All actions automatically update parent task context and progress.
📋 WHEN TO USE: Breaking down complex tasks, detailed workflow management, and team coordination on multi-step processes.
🎯 CRITICAL FOR: Task decomposition, progress tracking, hierarchical project organization, and maintaining parent-subtask synchronization.
🚀 ENHANCED FEATURES: Integrated progress tracking, automatic parent context updates, blocker management, insight propagation, and intelligent workflow hints.

🤖 AI USAGE GUIDELINES:
• ALWAYS use subtasks when a task has multiple distinct steps or components
• CREATE subtasks immediately after creating a parent task that requires multiple steps
• UPDATE subtasks with progress_percentage as you work (maps automatically to status)
• COMPLETE subtasks with detailed completion_summary to maintain context
• LIST subtasks regularly to check overall progress before completing parent task

| Action   | Required Parameters         | Optional Parameters                | Description                                      |
|----------|----------------------------|------------------------------------|--------------------------------------------------|
| create   | task_id, title             | description, status, priority, assignees, progress_notes | Create subtask (inherits agents if none specified) |
| update   | task_id, subtask_id        | title, description, status, priority, assignees, progress_notes, progress_percentage, blockers, insights_found | Modify subtask with progress tracking |
| delete   | task_id, subtask_id        |                                    | Remove subtask from parent task                  |
| get      | task_id, subtask_id        |                                    | Retrieve specific subtask details                |
| list     | task_id                    |                                    | List all subtasks with progress summary          |
| complete | task_id, subtask_id, completion_summary | impact_on_parent, insights_found | Complete subtask with context update |

📝 PRACTICAL EXAMPLES FOR AI:
1. Breaking down a feature implementation:
   - Parent task: "Implement user authentication" (assigned to: coding-agent, @security-auditor-agent)
   - Subtasks (auto-inherit both agents if not specified):
     • "Create login UI" - inherits both agents
     • "Add password validation" - inherits both agents  
     • "Implement JWT tokens" - can override with: assignees: "@security-auditor-agent"
     • "Add session management" - inherits both agents

2. Updating progress while working:
   - action: "update", task_id: "parent-id", subtask_id: "sub-id", progress_percentage: 50, progress_notes: "Login UI complete, working on validation"

3. Completing with context:
   - action: "complete", task_id: "parent-id", subtask_id: "sub-id", completion_summary: "JWT implementation complete with refresh token support", impact_on_parent: "Authentication backend 75% complete"

💡 ENHANCED PARAMETERS:
• completion_summary: Summary of what was accomplished (REQUIRED for complete action - be specific!)
• progress_notes: Brief description of work done (use for create/update to track what you did)
• progress_percentage: 0-100 (automatically sets status: 0=todo, 1-99=in_progress, 100=done)
• blockers: Any issues preventing progress (e.g., "Missing API documentation")
• impact_on_parent: How completing this subtask affects the parent task
• insights_found: Important discoveries (e.g., "Found existing utility function for validation")

🔄 AUTOMATIC FEATURES:
• **Agent Inheritance**: Subtasks automatically inherit parent task agents when none specified
• Parent task progress recalculation on all modifications
• Context updates with timestamps for all actions
• Progress percentage mapping: 0% → todo, 1-99% → in_progress, 100% → done
• Blocker escalation to parent task
• Insight propagation from subtasks to parent
• Progress summaries in list responses
• Workflow hints tailored to current subtask state and action
• Next action suggestions with examples
• Rule reminders for current workflow phase

📊 RESPONSE ENHANCEMENTS:
• parent_progress: Updated parent task progress after actions
• progress_summary: Detailed breakdown for list operations
• hint: Helpful suggestions (e.g., "All subtasks complete! Parent task ready for completion.")
• workflow_guidance: Intelligent hints, next actions, rules, and recommendations based on current state

💡 BEST PRACTICES FOR AI:
• Create subtasks BEFORE starting work on a complex task
• Update progress_percentage regularly (every 25% increment is good)
• Always provide completion_summary when completing subtasks
• Use insights_found to share important discoveries with future work
• Check parent progress with 'list' action before completing parent task
• Use blockers field to document any impediments

🛑 ERROR HANDLING:
• If required fields are missing, a clear error message is returned specifying which fields are needed
• Unknown actions return an error listing valid actions
• Internal errors are logged and returned with a generic error message
• Context update failures don't block the main operation
"""

MANAGE_SUBTASK_PARAMETERS_DESCRIPTION = {
    "action": "Subtask management action to perform. Valid values: create, update, delete, get, list, complete",
    "task_id": "[OPTIONAL] Parent task identifier (UUID). Required for all actions",
    "subtask_id": "[OPTIONAL] Subtask identifier (UUID). Required for update, delete, get, complete actions",
    "title": "[OPTIONAL] Subtask title. Required for create, optional for update",
    "description": "[OPTIONAL] Detailed subtask description explaining what needs to be done. Include acceptance criteria if relevant",
    "status": "[OPTIONAL] Subtask status: 'todo', 'in_progress', 'done'. Note: use progress_percentage instead for automatic status mapping",
    "priority": "[OPTIONAL] Subtask priority: 'low', 'medium', 'high', 'urgent', 'critical'. Default: inherits from parent",
    "assignees": "[OPTIONAL] Agent identifiers - **Inherits from parent task if not specified**. Use @agent-name format. Comma-separated for multiple: 'coding-agent,@test-orchestrator-agent'. Leave empty to inherit parent's agents automatically.",
    "progress_percentage": "[OPTIONAL] Integer 0-100 representing completion. Automatically maps to status (0=todo, 1-99=in_progress, 100=done). Use this instead of status field",
    "progress_notes": "[OPTIONAL] Brief description of current work status. Use this to track what you're doing. Example: 'Completed UI mockup, starting on API integration'",
    "completion_summary": "[OPTIONAL] Detailed summary of what was accomplished. BE SPECIFIC! Required for complete action. Example: 'Implemented JWT authentication with refresh tokens, 2-hour expiry, and secure httpOnly cookies'",
    "testing_notes": "[OPTIONAL] Notes about testing performed. Example: 'Tested login flow with valid/invalid credentials, verified token refresh'",
    "insights_found": "[OPTIONAL] Important discoveries or learnings. Comma-separated string or JSON array. Example: 'Found existing utility function for validation,Discovered performance bottleneck in query'",
    "challenges_overcome": "[OPTIONAL] Challenges faced and how they were resolved. Comma-separated string or JSON array",
    "skills_learned": "[OPTIONAL] New skills or knowledge gained. Comma-separated string or JSON array",
    "next_recommendations": "[OPTIONAL] Suggestions for future work. Comma-separated string or JSON array",
    "deliverables": "[OPTIONAL] Artifacts or outputs created. Comma-separated string or JSON array",
    "completion_quality": "[OPTIONAL] Quality assessment of work completed. Example: 'Production-ready', 'Requires review', 'Prototype only'",
    "blockers": "[OPTIONAL] Issues preventing progress. Comma-separated string or JSON array. Example: 'Missing API documentation,Waiting for database schema approval'",
    "impact_on_parent": "[OPTIONAL] How completing this subtask affects the parent task. Required for complete action",
    "user_id": "[OPTIONAL] User identifier for authentication and audit trails"
}

MANAGE_SUBTASK_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["action"]
        },
        
        # Task hierarchy parameters
        "task_id": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["task_id"]
        },
        "subtask_id": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["subtask_id"]
        },
        
        # Basic subtask parameters
        "title": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["title"]
        },
        "description": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["description"]
        },
        
        # Status and priority parameters
        "status": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["status"]
        },
        "priority": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["priority"]
        },
        
        # Assignment and progress parameters
        "assignees": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["assignees"]
        },
        "progress_percentage": {
            "type": "integer",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["progress_percentage"]
        },
        "progress_notes": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["progress_notes"]
        },
        
        # Completion parameters
        "completion_summary": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["completion_summary"]
        },
        "testing_notes": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["testing_notes"]
        },
        
        # Enhancement parameters (handled as strings with comma-separation)
        "insights_found": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["insights_found"]
        },
        "challenges_overcome": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["challenges_overcome"]
        },
        "skills_learned": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["skills_learned"]
        },
        "next_recommendations": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["next_recommendations"]
        },
        "deliverables": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["deliverables"]
        },
        
        # Quality and blocker parameters
        "completion_quality": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["completion_quality"]
        },
        "blockers": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["blockers"]
        },
        "impact_on_parent": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["impact_on_parent"]
        },
        
        # Authentication parameters
        "user_id": {
            "type": "string",
            "description": MANAGE_SUBTASK_PARAMETERS_DESCRIPTION["user_id"]
        }
    },
    "required": ["action"],  # Only action required at schema level - business logic validates per action
    "additionalProperties": False
}

def get_manage_subtask_parameters():
    """Get manage subtask parameters for use in controller."""
    return MANAGE_SUBTASK_PARAMS["properties"]

def get_manage_subtask_description():
    """Get manage subtask description for use in controller."""
    return MANAGE_SUBTASK_DESCRIPTION

# Backward compatibility constants
SUBTASK_DESCRIPTION = MANAGE_SUBTASK_DESCRIPTION
PARAMETER_DESCRIPTIONS = MANAGE_SUBTASK_PARAMETERS_DESCRIPTION

# Legacy parameter descriptions for backward compatibility
MANAGE_SUBTASK_PARAMETERS = {
    "action": "Action: create, update, delete, get, list, complete. Required. (string)",
    "task_id": "Parent task ID. Required for all actions. (string)", 
    "subtask_id": "Subtask ID for operations. Required for update, delete, get, complete actions. (string)",
    "title": "Subtask title. Required for create, optional for update. (string)",
    "description": "Detailed subtask description explaining what needs to be done. Include acceptance criteria if relevant. Optional for: create, update",
    "status": "Subtask status: 'todo', 'in_progress', 'done'. Optional - use progress_percentage instead for automatic status mapping.",
    "priority": "Subtask priority: 'low', 'medium', 'high', 'urgent', 'critical'. Optional for: create, update. Default: inherits from parent",
    "assignees": "List of assignee identifiers. Optional for: create, update. Example: ['user1', 'user2']",
    "completion_summary": "Detailed summary of what was accomplished. BE SPECIFIC! Required for complete action. Example: 'Implemented JWT authentication with refresh tokens, 2-hour expiry, and secure httpOnly cookies'",
    "progress_notes": "Brief description of current work status. Use this to track what you're doing. Optional for: create, update. Example: 'Completed UI mockup, starting on API integration'",
    "progress_percentage": "Integer 0-100 representing completion. Automatically maps to status (0=todo, 1-99=in_progress, 100=done). Use this instead of status field. Optional for: update",
    "blockers": "List any impediments or issues. Optional for: create, update. Example: ['Missing API documentation', 'Waiting for design approval']",
    "impact_on_parent": "How completing this subtask affects the parent task. Required for: complete. Example: 'Authentication backend now 75% complete, ready for testing phase'",
    "insights_found": "Important discoveries during subtask work. Optional for: create, update, complete. Example: ['Found existing utility function for validation', 'Discovered performance bottleneck in current approach']",
    "challenges_overcome": "Challenges faced and how they were resolved. Optional for: create, update, complete. Example: ['Resolved API timeout by implementing retry mechanism', 'Fixed authentication flow by updating token validation']",
    "skills_learned": "New skills or knowledge gained. Optional for: create, update, complete. Example: ['Learned advanced React hooks patterns', 'Mastered JWT token implementation']",
    "next_recommendations": "Suggestions for future work based on experience. Optional for: create, update, complete. Example: ['Consider implementing caching for API calls', 'Add comprehensive error logging']",
    "deliverables": "Specific artifacts or outputs created. Optional for: create, update, complete. Example: ['User authentication module', 'API endpoint documentation', 'Unit test suite']",
    "completion_quality": "Assessment of work quality. Optional for: complete. Example: 'Production-ready', 'Requires review', 'Prototype only'",
    "testing_notes": "Notes about testing performed. Optional for: complete. Example: 'Tested login flow with valid/invalid credentials, verified token refresh mechanism'"
}