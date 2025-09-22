"""
User-Scoped Task Routes with Authentication

This module demonstrates how to implement user-based data isolation
in API routes using JWT authentication and user-scoped repositories.
"""

import logging
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ...auth.interface.fastapi_auth import get_db, get_current_user
from ...auth.domain.entities.user import User
from ...task_management.interface.api_controllers.task_api_controller import TaskAPIController
from ...task_management.interface.api_controllers.subtask_api_controller import SubtaskAPIController
from ...task_management.application.dtos.task.create_task_request import CreateTaskRequest
from ...task_management.application.dtos.task.update_task_request import UpdateTaskRequest
from ...task_management.application.dtos.task.list_tasks_request import ListTasksRequest

# Import debug service
from ...utilities.debug_service import debug_service, log_api_v2_request, log_api_v2_response, log_auth_event, log_frontend_issue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/tasks", tags=["User-Scoped Tasks"])


# Initialize the API controllers
task_controller = TaskAPIController()
subtask_controller = SubtaskAPIController()


@router.post("/", response_model=dict)
async def create_task(
    request: CreateTaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new task for the authenticated user.
    
    The task will be automatically associated with the current user,
    ensuring data isolation.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} creating task: {request.title}")
        
        # Delegate to API controller
        result = task_controller.create_task(request, current_user.id, db)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to create task")
            )
        
        return {
            "success": True,
            "task": result.get("task"),
            "message": f"Task created successfully for user {current_user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating task for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )


@router.get("/", response_model=dict)
async def list_tasks(
    task_status: Optional[str] = None,
    priority: Optional[str] = None,
    git_branch_id: Optional[str] = None,  # Add git_branch_id parameter for branch filtering
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all tasks for the authenticated user.
    
    Only returns tasks that belong to the current user,
    ensuring data isolation. Can be filtered by git_branch_id
    to show tasks from a specific branch only.
    
    Args:
        task_status: Optional task status filter (todo, in_progress, done, etc.)
        priority: Optional priority filter (low, medium, high, urgent, critical)
        git_branch_id: Optional git branch UUID to filter tasks by specific branch
        limit: Maximum number of tasks to return (default 50)
    """
    try:
        # Enhanced debug logging for task listing
        logger.debug("=" * 80)
        logger.debug(f"🔍 TASK LISTING REQUEST")
        logger.debug(f"📧 User: {current_user.email} (ID: {current_user.id})")
        logger.debug(f"🎯 Filters: status={task_status}, priority={priority}, git_branch_id={git_branch_id}, limit={limit}")
        logger.debug(f"💾 Database session: {type(db)}")
        
        # Build request
        logger.debug("📋 Building list request...")
        list_request = ListTasksRequest(
            git_branch_id=git_branch_id,
            status=task_status,
            priority=priority,
            limit=limit
        )
        logger.debug(f"✅ List request built: {list_request}")
        
        # Delegate to API controller
        logger.debug("🔍 Fetching tasks from controller...")
        controller_result = task_controller.list_tasks(list_request, current_user.id, db)
        logger.debug(f"✅ Controller result type: {type(controller_result)}")
        
        # Extract the actual tasks array from the controller response
        if controller_result.get("success") and "tasks" in controller_result:
            tasks = controller_result["tasks"]
            logger.debug(f"✅ Tasks extracted: {len(tasks)} tasks found")
        else:
            logger.error(f"❌ Controller result error: {controller_result.get('error', 'Unknown error')}")
            tasks = []
        
        # Log each task for debugging
        if tasks:
            logger.debug("📝 Task details:")
            try:
                for i, task in enumerate(tasks[:5]):  # Log first 5 tasks only
                    if isinstance(task, dict):
                        logger.debug(f"   Task {i+1}: ID={task.get('id', 'N/A')}, Title={task.get('title', 'N/A')}, Status={task.get('status', 'N/A')}")
                    else:
                        logger.debug(f"   Task {i+1}: ID={getattr(task, 'id', 'N/A')}, Title={getattr(task, 'title', 'N/A')}, Status={getattr(task, 'status', 'N/A')}")
                if len(tasks) > 5:
                    logger.debug(f"   ... and {len(tasks) - 5} more tasks")
            except Exception as debug_error:
                logger.debug(f"📝 Debug logging error: {debug_error}, tasks type: {type(tasks)}")
        else:
            logger.debug("📝 No tasks found for user")
        
        # Prepare response - now using the extracted tasks array
        response_data = {
            "success": True,
            "tasks": tasks,
            "count": len(tasks),
            "user": current_user.email
        }
        
        logger.info(f"User {current_user.email} retrieved {len(tasks)} tasks")
        logger.debug(f"✅ TASK LISTING COMPLETED - Returning {len(tasks)} tasks")
        logger.debug("=" * 80)
        
        return response_data
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ ERROR in task listing for user {current_user.id}")
        logger.error(f"❌ User: {current_user.email}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        logger.error(f"❌ Error message: {str(e)}")
        
        # Log stack trace for debugging
        import traceback
        logger.error(f"❌ Stack trace:")
        for line in traceback.format_exc().splitlines():
            logger.error(f"   {line}")
        
        logger.error("=" * 80)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tasks"
        )


@router.get("/{task_id}", response_model=dict)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific task for the authenticated user.
    
    Returns 404 if the task doesn't exist or doesn't belong to the user.
    """
    try:
        # Delegate to API controller
        result = task_controller.get_task(task_id, current_user.id, db)
        
        if not result.get("success"):
            logger.warning(f"User {current_user.email} attempted to access non-existent or unauthorized task {task_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        logger.info(f"User {current_user.email} accessed task {task_id}")
        
        return {
            "success": True,
            "task": result.get("task")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task {task_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task"
        )


@router.put("/{task_id}", response_model=dict)
async def update_task(
    task_id: str,
    request: UpdateTaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a task for the authenticated user.
    
    Only allows updating tasks that belong to the current user.
    """
    try:
        # Delegate to API controller
        result = task_controller.update_task(task_id, request, current_user.id, db)
        
        if not result.get("success"):
            if "not found" in result.get("error", "").lower():
                logger.warning(f"User {current_user.email} attempted to update non-existent or unauthorized task {task_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "Failed to update task")
                )
        
        logger.info(f"User {current_user.email} updated task {task_id}")
        
        return {
            "success": True,
            "task": result.get("task"),
            "message": "Task updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task {task_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )


@router.delete("/{task_id}", response_model=dict)
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a task for the authenticated user.
    
    Only allows deleting tasks that belong to the current user.
    """
    try:
        # Delegate to API controller
        result = task_controller.delete_task(task_id, current_user.id, db)
        
        if not result.get("success"):
            if "not found" in result.get("error", "").lower():
                logger.warning(f"User {current_user.email} attempted to delete non-existent or unauthorized task {task_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "Failed to delete task")
                )
        
        logger.info(f"User {current_user.email} deleted task {task_id}")
        
        return {
            "success": True,
            "message": "Task deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task {task_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )


@router.post("/{task_id}/complete", response_model=dict)
async def complete_task(
    task_id: str,
    completion_summary: str,
    testing_notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a task as completed for the authenticated user.
    
    Only allows completing tasks that belong to the current user.
    """
    try:
        # Delegate to API controller
        result = task_controller.complete_task(task_id, completion_summary, testing_notes, current_user.id, db)
        
        if not result.get("success"):
            if "not found" in result.get("error", "").lower():
                logger.warning(f"User {current_user.email} attempted to complete non-existent or unauthorized task {task_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "Failed to complete task")
                )
        
        logger.info(f"User {current_user.email} completed task {task_id}")
        
        return {
            "success": True,
            "task": result.get("task"),
            "message": "Task completed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing task {task_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete task"
        )


@router.get("/stats/summary", response_model=dict)
async def get_user_task_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get task statistics for the authenticated user.
    
    Returns summary statistics only for the user's own tasks.
    """
    try:
        # Delegate to API controller
        result = task_controller.get_task_statistics(current_user.id, db)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to get task statistics")
            )
        
        # Add user email to stats
        stats = result.get("stats", {})
        stats["user"] = current_user.email
        
        logger.info(f"User {current_user.email} retrieved task statistics")
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting task stats for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task statistics"
        )


@router.post("/{task_id}/subtasks/summaries", response_model=dict)
async def get_subtask_summaries(
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get lightweight subtask summaries for a parent task.
    
    This endpoint provides subtask information without loading full details,
    improving performance when expanding tasks in the UI.
    """
    try:
        # Parse request body if present
        try:
            body = await request.body()
            data = json.loads(body) if body else {}
            include_counts = data.get("include_counts", True)
        except:
            include_counts = True
        
        logger.info(f"Loading subtask summaries for task {task_id} by user {current_user.email}")
        
        # Delegate to API controller
        result = subtask_controller.list_subtasks(task_id, current_user.id, db)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to fetch subtasks")
            )
        
        subtasks_data = result.get("subtasks", [])
        
        # Convert to subtask summaries
        subtask_summaries = []
        status_counts = {"todo": 0, "in_progress": 0, "done": 0, "blocked": 0}
        
        for subtask_data in subtasks_data:
            # Extract values from value objects if needed
            subtask_id = subtask_data["id"]
            if isinstance(subtask_id, dict) and "value" in subtask_id:
                subtask_id = subtask_id["value"]
            elif hasattr(subtask_id, "value"):
                subtask_id = subtask_id.value
                
            status = subtask_data["status"]
            if isinstance(status, dict) and "value" in status:
                status = status["value"]
            elif hasattr(status, "value"):
                status = status.value
                
            priority = subtask_data["priority"]
            if isinstance(priority, dict) and "value" in priority:
                priority = priority["value"]
            elif hasattr(priority, "value"):
                priority = priority.value
            
            summary = {
                "id": str(subtask_id),
                "title": subtask_data["title"],
                "status": str(status),
                "priority": str(priority),
                "assignees_count": len(subtask_data.get("assignees", [])),
                "progress_percentage": subtask_data.get("progress_percentage", 0)
            }
            subtask_summaries.append(summary)
            
            # Count statuses for progress summary
            if status in status_counts:
                status_counts[status] += 1
        
        # Calculate progress summary
        total_subtasks = len(subtask_summaries)
        progress_summary = {
            "total": total_subtasks,
            "completed": status_counts["done"],
            "in_progress": status_counts["in_progress"],
            "todo": status_counts["todo"],
            "blocked": status_counts["blocked"],
            "completion_percentage": round((status_counts["done"] / total_subtasks) * 100) if total_subtasks > 0 else 0
        }
        
        response = {
            "subtasks": subtask_summaries,
            "parent_task_id": task_id,
            "total_count": total_subtasks,
            "progress_summary": progress_summary
        }
        
        logger.info(f"Returned {len(subtask_summaries)} subtask summaries for task {task_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching subtask summaries for task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Nested subtask endpoint removed - using simple /api/v2/subtasks/{subtask_id} instead


# Register the router in your main app
# app.include_router(router)