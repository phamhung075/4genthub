"""
Subtask Management Tool Description

This module contains the comprehensive documentation for the manage_subtask MCP tool.
Separated from the controller logic for better maintainability and organization.
"""

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
| create   | task_id, title             | description, status, priority, assignees, progress_notes | Create new subtask under parent task             |
| update   | task_id, subtask_id        | title, description, status, priority, assignees, progress_notes, progress_percentage, blockers, insights_found | Modify subtask with progress tracking |
| delete   | task_id, subtask_id        |                                    | Remove subtask from parent task                  |
| get      | task_id, subtask_id        |                                    | Retrieve specific subtask details                |
| list     | task_id                    |                                    | List all subtasks with progress summary          |
| complete | task_id, subtask_id, completion_summary | impact_on_parent, insights_found | Complete subtask with context update |

📝 PRACTICAL EXAMPLES FOR AI:
1. Breaking down a feature implementation:
   - Parent task: "Implement user authentication"
   - Subtasks: "Create login UI", "Add password validation", "Implement JWT tokens", "Add session management"

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

# Parameter descriptions for the manage_subtask tool
MANAGE_SUBTASK_PARAMETERS = {
    "action": "Subtask management action. Required. Valid: 'create', 'update', 'delete', 'list', 'get', 'complete'. Use 'create' when breaking down tasks, 'update' while working, 'complete' when done.",
    "task_id": "Parent task identifier (UUID). Required for all actions. Get this from the parent task you want to add subtasks to.",
    "subtask_id": "Subtask ID (UUID). Required for: update, delete, get, complete. Get this from list action or create response.",
    "title": "Subtask title - be specific and actionable (e.g., 'Implement user login form' not just 'Login'). Required for: create. Optional for: update",
    "description": "Detailed subtask description explaining what needs to be done. Include acceptance criteria if relevant. Optional for: create, update",
    "status": "Subtask status: 'todo', 'in_progress', 'done'. Optional - use progress_percentage instead for automatic status mapping.",
    "priority": "Subtask priority: 'low', 'medium', 'high', 'urgent', 'critical'. Optional for: create, update. Default: inherits from parent",
    "assignees": "List of assignee identifiers. Optional for: create, update. Example: ['user1', 'user2']",
    "completion_summary": "Detailed summary of what was accomplished. BE SPECIFIC! Required for complete action. Example: 'Implemented JWT authentication with refresh tokens, 2-hour expiry, and secure httpOnly cookies'",
    "progress_notes": "Brief description of current work status. Use this to track what you're doing. Optional for: create, update. Example: 'Completed UI mockup, starting on API integration'",
    "progress_percentage": "Integer 0-100 representing completion. Automatically maps to status (0=todo, 1-99=in_progress, 100=done). Use this instead of status field. Optional for: update",
    "blockers": "List any impediments or issues. Optional for: update. Example: 'Waiting for API documentation from backend team'",
    "impact_on_parent": "Explain how completing this subtask affects the parent task. Optional for: complete. Example: 'Authentication flow 50% complete, login working but password reset pending'",
    "insights_found": "Important discoveries or learnings. Share knowledge for future work. Optional for: update, complete. Example: 'Found existing validation library that saves 200 lines of code'"
}