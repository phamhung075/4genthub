"""
Token Cost Configuration

Defines token costs for all MCP operations.
Token costs are based on operation complexity and resource usage.
"""

# Token costs for each MCP operation
TOKEN_COSTS: dict[str, int] = {
    # Project operations
    "create_project": 10,  # Create new project with context initialization
    "update_project": 5,  # Update project metadata
    "delete_project": 5,  # Delete project and cleanup
    "list_projects": 1,  # List all projects
    "get_project": 1,  # Get single project details
    "project_health_check": 3,  # Health check analysis
    "cleanup_obsolete": 5,  # Cleanup obsolete resources
    "validate_integrity": 3,  # Validate project integrity
    "rebalance_agents": 5,  # Rebalance agent assignments
    # Git Branch operations
    "create_branch": 5,  # Create new git branch
    "update_branch": 3,  # Update branch metadata
    "delete_branch": 3,  # Delete git branch
    "list_branches": 1,  # List all branches
    "get_branch": 1,  # Get single branch details
    "assign_agent_branch": 3,  # Assign agent to branch
    "unassign_agent_branch": 2,  # Unassign agent from branch
    "get_branch_statistics": 2,  # Get branch statistics
    "archive_branch": 3,  # Archive branch
    "restore_branch": 3,  # Restore archived branch
    # Task operations
    "create_task": 5,  # Create new task
    "update_task": 3,  # Update task details
    "complete_task": 3,  # Mark task as complete
    "delete_task": 3,  # Delete task
    "list_tasks": 1,  # List all tasks
    "get_task": 1,  # Get single task details
    "search_tasks": 2,  # Search tasks with filters
    "next_task": 2,  # Get next recommended task
    "add_dependency": 2,  # Add task dependency
    "remove_dependency": 2,  # Remove task dependency
    "ai_plan": 15,  # AI-powered task planning
    "ai_create": 10,  # AI-enhanced task creation
    "ai_enhance": 8,  # AI task enhancement
    "ai_analyze": 7,  # AI requirements analysis
    "ai_suggest_agents": 5,  # AI agent suggestions
    # Subtask operations
    "create_subtask": 3,  # Create new subtask
    "update_subtask": 2,  # Update subtask details
    "complete_subtask": 2,  # Mark subtask as complete
    "delete_subtask": 2,  # Delete subtask
    "list_subtasks": 1,  # List all subtasks
    "get_subtask": 1,  # Get single subtask details
    # Agent operations
    "call_agent": 20,  # Call agent (most expensive - AI operation)
    "register_agent": 5,  # Register new agent
    "assign_agent": 3,  # Assign agent to task tree
    "unassign_agent": 2,  # Unassign agent
    "get_agent": 1,  # Get agent details
    "list_agents": 1,  # List all agents
    "update_agent": 3,  # Update agent metadata
    "unregister_agent": 3,  # Rebalance agent assignments
    # Context operations
    "create_context": 5,  # Create new context
    "update_context": 3,  # Update context data
    "delete_context": 3,  # Delete context
    "get_context": 1,  # Get context data
    "resolve_context": 2,  # Resolve context with inheritance
    "delegate_context": 4,  # Delegate context to different level
    "add_insight": 2,  # Add insight to context
    "add_progress": 2,  # Add progress to context
    "list_contexts": 1,  # List contexts
    # Authentication operations (free - should not consume tokens)
    "login": 0,
    "register": 0,
    "logout": 0,
    "refresh_token": 0,
    "verify_email": 0,
    "forgot_password": 0,
    "reset_password": 0,
    # Token balance operations (free - managing tokens shouldn't cost tokens)
    "get_balance": 0,
    "get_usage_stats": 0,
    "add_tokens": 0,
    "update_quota": 0,
}


def get_operation_cost(operation: str, default: int = 1) -> int:
    """
    Get token cost for an operation

    Args:
        operation: Operation name
        default: Default cost if operation not found (default: 1)

    Returns:
        Token cost for the operation
    """
    return TOKEN_COSTS.get(operation, default)


def get_all_costs() -> dict[str, int]:
    """
    Get all token costs

    Returns:
        Dictionary of all operation costs
    """
    return TOKEN_COSTS.copy()


def get_free_operations() -> list[str]:
    """
    Get list of operations that don't consume tokens

    Returns:
        List of operation names with zero cost
    """
    return [op for op, cost in TOKEN_COSTS.items() if cost == 0]


def get_expensive_operations(threshold: int = 10) -> dict[str, int]:
    """
    Get operations that cost more than threshold

    Args:
        threshold: Minimum cost to include (default: 10)

    Returns:
        Dictionary of expensive operations and their costs
    """
    return {op: cost for op, cost in TOKEN_COSTS.items() if cost >= threshold}
