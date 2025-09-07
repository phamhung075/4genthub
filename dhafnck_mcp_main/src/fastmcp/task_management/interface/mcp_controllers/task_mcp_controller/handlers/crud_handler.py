"""
CRUD Handler for Task MCP Controller

Handles Create, Read, Update, Delete operations for tasks.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .....application.dtos.task.create_task_request import CreateTaskRequest
from .....application.dtos.task.update_task_request import UpdateTaskRequest
from .....application.facades.task_application_facade import TaskApplicationFacade
from ....utils.response_formatter import StandardResponseFormatter, ErrorCodes

logger = logging.getLogger(__name__)


class CRUDHandler:
    """Handles CRUD operations for tasks."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
    
    def create_task(self, facade: TaskApplicationFacade, 
                   git_branch_id: Optional[str] = None, 
                   title: Optional[str] = None, 
                   description: Optional[str] = None, 
                   status: Optional[str] = None, 
                   priority: Optional[str] = None, 
                   details: Optional[str] = None, 
                   estimated_effort: Optional[str] = None, 
                   assignees: Optional[List[str]] = None, 
                   labels: Optional[List[str]] = None, 
                   due_date: Optional[str] = None,
                   dependencies: Optional[List[str]] = None,
                   user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle task creation with validation and context setup."""
        if not title:
            return self._create_standardized_error(
                operation="create_task",
                field="title",
                expected="A valid title string",
                hint="Include 'title' in your request body"
            )
        
        if not git_branch_id:
            return self._create_standardized_error(
                operation="create_task",
                field="git_branch_id",
                expected="A valid git_branch_id string",
                hint="Include 'git_branch_id' in your request body"
            )
        
        request = CreateTaskRequest(
            title=title,
            description=description or f"Description for {title}",
            git_branch_id=git_branch_id,
            status=status,
            priority=priority,
            details=details or "",
            estimated_effort=estimated_effort,
            assignees=assignees or [],
            labels=labels or [],
            due_date=due_date,
            dependencies=dependencies or [],
            user_id=user_id
        )
        
        result = facade.create_task(request)
        
        # Ensure result is a dictionary before accessing it
        if not isinstance(result, dict):
            logger.error(f"create_task returned non-dict result: {type(result)}")
            return self._response_formatter.create_error_response(
                operation="create",
                error="Internal error: Invalid response format from task creation",
                error_code=ErrorCodes.INTERNAL_ERROR
            )
        
        return result
    
    def update_task(self, facade: TaskApplicationFacade, task_id: Optional[str], title: Optional[str], 
                   description: Optional[str], status: Optional[str], priority: Optional[str], 
                   details: Optional[str], estimated_effort: Optional[str], 
                   assignees: Optional[List[str]], labels: Optional[List[str]], 
                   due_date: Optional[str], context_id: Optional[str] = None, 
                   completion_summary: Optional[str] = None, 
                   testing_notes: Optional[str] = None) -> Dict[str, Any]:
        """Handle task update operations."""
        logger.info(f"update_task called with task_id={task_id}, type={type(task_id)}")
        
        if not task_id:
            return self._create_standardized_error(
                operation="update_task",
                field="task_id",
                expected="A valid task_id string",
                hint="Include 'task_id' in your request body"
            )
        
        # Create update request with provided fields
        request_data = {'task_id': task_id}  # task_id is required for UpdateTaskRequest
        
        if title is not None:
            request_data['title'] = title
        if description is not None:
            request_data['description'] = description
        if status is not None:
            request_data['status'] = status
        if priority is not None:
            request_data['priority'] = priority
        if details is not None:
            request_data['details'] = details
        if estimated_effort is not None:
            request_data['estimated_effort'] = estimated_effort
        if assignees is not None:
            request_data['assignees'] = assignees
        if labels is not None:
            request_data['labels'] = labels
        if due_date is not None:
            request_data['due_date'] = due_date
        if context_id is not None:
            request_data['context_id'] = context_id
        if completion_summary is not None:
            request_data['completion_summary'] = completion_summary
        if testing_notes is not None:
            request_data['testing_notes'] = testing_notes
        
        logger.info(f"Creating UpdateTaskRequest with data: {request_data}")
        try:
            request = UpdateTaskRequest(**request_data)
        except Exception as e:
            logger.error(f"Failed to create UpdateTaskRequest: {e}, request_data={request_data}")
            raise
        return facade.update_task(task_id, request)
    
    def get_task(self, facade: TaskApplicationFacade, task_id: str, 
                include_context: bool = False) -> Dict[str, Any]:
        """Handle task retrieval with optional context."""
        if not task_id:
            return self._create_standardized_error(
                operation="get_task",
                field="task_id",
                expected="A valid task_id string",
                hint="Include 'task_id' in your request"
            )
        
        result = facade.get_task(task_id)
        
        if result.get("success") and include_context and result.get("task"):
            # Add context information if requested
            task_data = result["task"]
            task_context_id = task_data.get("context_id")
            if task_context_id:
                result["include_context"] = True
                result["task"]["context_available"] = True
            else:
                result["task"]["context_available"] = False
        
        return result
    
    def delete_task(self, facade: TaskApplicationFacade, task_id: Optional[str]) -> Dict[str, Any]:
        """Handle task deletion."""
        if not task_id:
            return self._create_standardized_error(
                operation="delete_task",
                field="task_id",
                expected="A valid task_id string",
                hint="Include 'task_id' in your request"
            )
        
        return facade.delete_task(task_id)
    
    def complete_task(self, facade: TaskApplicationFacade, task_id: Optional[str], 
                     completion_summary: Optional[str] = None, 
                     testing_notes: Optional[str] = None) -> Dict[str, Any]:
        """Handle task completion with summary."""
        if not task_id:
            return self._create_standardized_error(
                operation="complete_task", 
                field="task_id",
                expected="A valid task_id string",
                hint="Include 'task_id' in your request"
            )
        
        # Create update request for completion
        request_data = {
            "task_id": task_id,  # task_id is required for UpdateTaskRequest
            "status": "done",
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        
        if completion_summary:
            request_data["completion_summary"] = completion_summary
        if testing_notes:
            request_data["testing_notes"] = testing_notes
        
        request = UpdateTaskRequest(**request_data)
        return facade.update_task(task_id, request)
    
    def _create_standardized_error(self, operation: str, field: str, 
                                 expected: str, hint: str) -> Dict[str, Any]:
        """Create standardized validation error."""
        return self._response_formatter.create_error_response(
            operation=operation,
            error=f"Missing required field: {field}. Expected: {expected}",
            error_code=ErrorCodes.VALIDATION_ERROR,
            metadata={"field": field, "hint": hint}
        )