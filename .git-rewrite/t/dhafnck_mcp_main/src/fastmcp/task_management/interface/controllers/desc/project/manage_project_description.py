"""
Project Management Tool Description

This module contains the comprehensive documentation for the manage_project MCP tool.
Separated from the controller logic for better maintainability and organization.
"""

MANAGE_PROJECT_DESCRIPTION = """
📁 PROJECT MANAGEMENT SYSTEM - Complete Project Lifecycle and Multi-Project Orchestration

⭐ WHAT IT DOES: Manages projects throughout their lifecycle with comprehensive CRUD operations, health monitoring, resource management, and cross-project coordination. Provides intelligent maintenance, agent assignment optimization, and multi-project prioritization.
📋 WHEN TO USE: Project creation, management, monitoring, maintenance, multi-project coordination, resource optimization, and organizational structure management.
🎯 CRITICAL FOR: Project lifecycle management, organizational hierarchy, resource allocation, cross-project learning, and enterprise-scale development coordination.

🤖 AI USAGE GUIDELINES:
• ALWAYS list projects on startup to understand organizational context
• USE health checks before critical operations to ensure system integrity
• COORDINATE across projects using priority scores and context switching
• OPTIMIZE agent assignments based on project workload and specialization
• SHARE reusable patterns between projects through global context delegation

| Action                | Required Parameters  | Optional Parameters      | Description                                      |
|-----------------------|---------------------|-------------------------|--------------------------------------------------|
| create                | name                | description, user_id     | Create new project with automatic context initialization |
| get                   | project_id OR name  |                         | Retrieve project details by ID or name           |
| list                  | (none)              |                         | List all projects with status and health info    |
| update                | project_id          | name, description       | Update project metadata and trigger sync         |
| project_health_check  | project_id          |                         | Comprehensive health analysis with metrics       |
| cleanup_obsolete      | project_id          | force                   | Remove obsolete tasks, files, and resources      |
| validate_integrity    | project_id          | force                   | Validate structure, dependencies, and consistency |
| rebalance_agents      | project_id          | force                   | Optimize agent assignments across task trees     |

💡 USAGE GUIDELINES:
• Provide all required identifiers for each action (see table above)
• Use either project_id OR name for 'get' action (not both)
• Optional parameters can be omitted unless overriding defaults
• The 'force' parameter bypasses safety checks for maintenance operations
• All operations return detailed success/error status with actionable messages
• Business logic is delegated to the project application facade

🔍 AI DECISION TREES:

PROJECT CREATION WORKFLOW:
```
IF new_feature_request:
    1. List existing projects
    2. Check for similar projects
    IF no_similar_project:
        Create new project
        Initialize project context
        Assign initial agents
    ELSE:
        Use existing project
        Create new git branch
```

PROJECT HEALTH MONITORING:
```
IF starting_work_on_project:
    Run project_health_check
    IF health_score < 70:
        IF critical_issues:
            Run cleanup_obsolete
            Run validate_integrity
        IF agent_imbalance:
            Run rebalance_agents
    PROCEED with work
```

MULTI-PROJECT COORDINATION:
```
IF multiple_projects_active:
    FOR each project:
        Get project health
        Calculate priority_score
    SORT by priority_score DESC
    WORK on highest_priority
    IF context_switch_needed:
        Save current context
        Switch to new project
        Restore project context
```

📊 WORKFLOW PATTERNS:

1. PROJECT INITIALIZATION:
   ```
   action: "create", name: "new-feature-x", description: "Implement feature X with Y requirements"
   → Creates project
   → Initializes hierarchical context
   → Sets up default git branches
   → Returns project_id for subsequent operations
   ```

2. HEALTH CHECK WORKFLOW:
   ```
   action: "project_health_check", project_id: "proj-123"
   → Analyzes task completion rates
   → Checks resource utilization
   → Validates data integrity
   → Returns health_score and recommendations
   ```

3. MAINTENANCE SEQUENCE:
   ```
   # When health_score < 70:
   action: "cleanup_obsolete", project_id: "proj-123", force: false
   action: "validate_integrity", project_id: "proj-123"
   action: "rebalance_agents", project_id: "proj-123"
   ```

4. CROSS-PROJECT PATTERN SHARING:
   ```
   # After successful implementation:
   1. Get project context
   2. Identify reusable patterns
   3. Delegate to global context
   4. Other projects inherit pattern
   ```

🎯 PRIORITY SCORING MATRIX:
```python
PRIORITY_FACTORS = {
    "blocked_tasks": 50,      # High-priority blockers
    "critical_bugs": 40,      # Production issues
    "deadline_proximity": 30, # Time-sensitive work
    "team_size": 20,         # Resource availability
    "business_value": 25,    # Strategic importance
    "dependencies": 15       # Blocking other work
}

# Priority > 200: IMMEDIATE attention
# Priority 150-200: URGENT (queue after current)
# Priority 100-150: HIGH (standard queue)
# Priority < 100: NORMAL (background work)
```

📈 HEALTH METRICS:
```python
HEALTH_INDICATORS = {
    "task_completion_rate": 30,     # % of completed vs total
    "blocker_count": 25,           # Number of blocked tasks
    "agent_utilization": 20,       # Agent workload balance
    "context_coherence": 15,       # Context data quality
    "resource_efficiency": 10      # Resource usage patterns
}

# Health > 85: EXCELLENT
# Health 70-85: GOOD
# Health 50-70: NEEDS ATTENTION
# Health < 50: CRITICAL
```

⚠️ IMPORTANT NOTES:
• Projects are the primary organizational unit in the system
• Each project maintains its own hierarchical context (inherits from global)
• Projects can have multiple git branches (task trees)
• Agent assignments are scoped to project-branch combinations
• Maintenance operations should be run periodically for optimal performance
• Cross-project patterns should be delegated to global context

🛠️ MAINTENANCE BEST PRACTICES:
• Run health checks weekly or before major operations
• Execute cleanup_obsolete monthly or when health < 70
• Validate integrity after major changes or migrations
• Rebalance agents when adding/removing team members
• Monitor health trends for early issue detection

🛑 ERROR HANDLING:
• Missing required fields return clear error with field name and action
• Unknown actions return error with list of valid actions
• Invalid project_id/name returns "not found" with search suggestions
• Force parameter warnings explain risks before proceeding
• All errors include actionable hints for resolution
"""

MANAGE_PROJECT_PARAMETERS = {
    "action": "Project management action to perform. Valid actions: 'create', 'get', 'list', 'update', 'project_health_check', 'cleanup_obsolete', 'validate_integrity', 'rebalance_agents' (string, required)",
    "project_id": "Unique identifier for the project. Required for most actions except create/list. Can use name instead for 'get' action. (string, optional)",
    "name": "Project name. Required for create action, optional for update. Can be used instead of project_id for 'get' action. (string, optional)",
    "description": "Project description explaining purpose and scope. Optional for create/update actions. (string, optional)",
    "user_id": "User identifier for access control and audit. Optional, defaults to system context. (string, optional)",
    "force": "Force operation flag to bypass safety checks. Use with caution for maintenance operations. Optional, defaults to false. (boolean, optional)"
} 