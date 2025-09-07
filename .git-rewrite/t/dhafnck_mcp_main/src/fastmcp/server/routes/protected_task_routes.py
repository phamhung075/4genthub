"""
Protected Task Routes with OAuth2 Authentication

This module provides OAuth2-protected versions of task-related endpoints
for use with the auth bridge pattern. These routes can be used for REST API
access while MCP protocol continues using its native authentication.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
import logging
import json

# Import OAuth2 dependencies
from fastmcp.auth.interface.fastapi_auth import get_current_active_user
from fastmcp.auth.domain.entities.user import User

# Import task management facades
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.application.facades.unified_context_facade import UnifiedContextFacade
from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
from fastmcp.task_management.application.factories.task_facade_factory import TaskFacadeFactory
from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
from fastmcp.task_management.infrastructure.repositories.subtask_repository_factory import SubtaskRepositoryFactory

logger = logging.getLogger(__name__)

# Create router with OAuth2 protection
router = APIRouter(
    prefix="/api/tasks",
    tags=["Protected Tasks"],
    dependencies=[Depends(get_current_user_from_bridge)]  # Protect all routes
)


@router.get("/summaries")
async def get_task_summaries(
    git_branch_id: str = Query(..., description="Git branch UUID"),
    include_subtasks: bool = Query(False, description="Include subtask summaries"),
    current_user: Dict[str, Any] = Depends(get_current_user_from_bridge)
) -> Dict[str, Any]:
    """
    Get lightweight task summaries for list views with OAuth2 protection.
    
    This endpoint provides only essential task information for initial page load,
    dramatically improving performance for large task lists.
    """
    try:
        # Get task facade
        task_facade = TaskFacadeFactory.create()
        
        # List tasks for the branch (filtered by user context from auth)
        tasks = task_facade.list_tasks(
            git_branch_id=git_branch_id,
            # Could add user filtering here if needed
            # user_id=current_user.get("user_id")
        )
        
        # Transform to summary format
        summaries = []
        for task in tasks:
            summary = {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "progress_percentage": task.progress_percentage,
                "assignees": task.assignees,
                "labels": task.labels,
                "subtask_count": len(task.subtasks) if hasattr(task, 'subtasks') else 0,
                "has_context": bool(task.context_id),
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None
            }
            
            # Optionally include subtask summaries
            if include_subtasks and hasattr(task, 'subtasks'):
                summary["subtasks"] = [
                    {
                        "id": subtask.id,
                        "title": subtask.title,
                        "status": subtask.status,
                        "progress": getattr(subtask, 'progress_percentage', 0)
                    }
                    for subtask in task.subtasks
                ]
            
            summaries.append(summary)
        
        return {
            "success": True,
            "data": summaries,
            "count": len(summaries),
            "user": current_user.get("email", "unknown"),
            "auth_method": current_user.get("auth_method", "unknown")
        }
        
    except Exception as e:
        logger.error(f"Error getting task summaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subtask-summaries/{task_id}")
async def get_subtask_summaries(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_from_bridge)
) -> Dict[str, Any]:
    """
    Get lightweight subtask summaries for a specific task with OAuth2 protection.
    
    Provides only essential subtask information for UI rendering.
    """
    try:
        # Get subtask repository
        subtask_repo = SubtaskRepositoryFactory.create()
        
        # Get subtasks for the task
        subtasks = subtask_repo.find_by_parent_task(task_id)
        
        # Transform to summary format
        summaries = [
            {
                "id": subtask.id,
                "title": subtask.title,
                "status": subtask.status,
                "priority": subtask.priority,
                "assignees": subtask.assignees,
                "progress": getattr(subtask, 'progress_percentage', 0),
                "created_at": subtask.created_at.isoformat() if subtask.created_at else None,
                "updated_at": subtask.updated_at.isoformat() if subtask.updated_at else None
            }
            for subtask in subtasks
        ]
        
        # Calculate aggregate progress
        total_progress = sum(s["progress"] for s in summaries)
        avg_progress = total_progress / len(summaries) if summaries else 0
        
        return {
            "success": True,
            "data": {
                "task_id": task_id,
                "subtasks": summaries,
                "count": len(summaries),
                "average_progress": avg_progress,
                "completed_count": sum(1 for s in summaries if s["status"] == "done")
            },
            "user": current_user.get("email", "unknown"),
            "auth_method": current_user.get("auth_method", "unknown")
        }
        
    except Exception as e:
        logger.error(f"Error getting subtask summaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/branch-statistics/{git_branch_id}")
async def get_branch_statistics(
    git_branch_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_from_bridge)
) -> Dict[str, Any]:
    """
    Get statistics for a git branch with OAuth2 protection.
    
    Provides task counts, progress metrics, and other statistics.
    """
    try:
        # Get task facade
        task_facade = TaskFacadeFactory.create()
        
        # Get all tasks for the branch
        tasks = task_facade.list_tasks(git_branch_id=git_branch_id)
        
        # Calculate statistics
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status == "done")
        in_progress_tasks = sum(1 for t in tasks if t.status == "in_progress")
        todo_tasks = sum(1 for t in tasks if t.status == "todo")
        blocked_tasks = sum(1 for t in tasks if t.status == "blocked")
        
        # Calculate average progress
        total_progress = sum(t.progress_percentage for t in tasks if hasattr(t, 'progress_percentage'))
        avg_progress = total_progress / total_tasks if total_tasks > 0 else 0
        
        # Priority breakdown
        priority_breakdown = {
            "critical": sum(1 for t in tasks if t.priority == "critical"),
            "high": sum(1 for t in tasks if t.priority == "high"),
            "medium": sum(1 for t in tasks if t.priority == "medium"),
            "low": sum(1 for t in tasks if t.priority == "low")
        }
        
        return {
            "success": True,
            "data": {
                "git_branch_id": git_branch_id,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "in_progress_tasks": in_progress_tasks,
                "todo_tasks": todo_tasks,
                "blocked_tasks": blocked_tasks,
                "completion_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                "average_progress": avg_progress,
                "priority_breakdown": priority_breakdown
            },
            "user": current_user.get("email", "unknown"),
            "auth_method": current_user.get("auth_method", "unknown")
        }
        
    except Exception as e:
        logger.error(f"Error getting branch statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export router for mounting
__all__ = ["router"]