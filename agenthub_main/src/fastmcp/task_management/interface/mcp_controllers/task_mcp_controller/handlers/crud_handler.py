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
        """Handle task creation with validation and context setup.
        
        Enhanced to support multiple agent assignment at creation time.
        Validates all assignees using AgentRole enum before task creation.
        """
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
        
        # Validate that at least one agent is assigned
        if not assignees or len(assignees) == 0:
            return self._create_standardized_error(
                operation="create_task",
                field="assignees",
                expected="At least one agent must be assigned to the task",
                hint="Include 'assignees' with at least one valid agent (e.g., ['coding-agent'] or ['@test-orchestrator-agent'])"
            )
        
        # Validate assignees if provided
        if assignees:
            try:
                # Import domain validation functions directly without creating a dummy task
                from .....domain.enums.agent_roles import AgentRole, resolve_legacy_role
                
                validated_assignees = []
                invalid_assignees = []
                
                for assignee in assignees:
                    if assignee and assignee.strip():
                        # Clean the assignee string
                        clean_assignee = assignee.strip()
                        
                        # Try to resolve legacy role names
                        resolved_assignee = resolve_legacy_role(clean_assignee)
                        if resolved_assignee:
                            # Ensure resolved assignee has @ prefix
                            if not resolved_assignee.startswith("@"):
                                resolved_assignee = f"@{resolved_assignee}"
                            validated_assignees.append(resolved_assignee)
                            logger.info(f"Resolved legacy assignee '{assignee}' to '{resolved_assignee}'")
                        elif AgentRole.is_valid_role(clean_assignee.lstrip('@')):
                            # Valid agent role - ensure @ prefix
                            if not clean_assignee.startswith("@"):
                                clean_assignee = f"@{clean_assignee}"
                            validated_assignees.append(clean_assignee)
                            logger.info(f"Validated assignee: '{clean_assignee}'")
                        elif clean_assignee.startswith("@") and AgentRole.is_valid_role(clean_assignee[1:]):
                            # Already has @ prefix and is valid
                            validated_assignees.append(clean_assignee)
                            logger.info(f"Validated assignee with @ prefix: '{clean_assignee}'")
                        else:
                            # Invalid assignee
                            invalid_assignees.append(assignee)
                            logger.warning(f"Invalid assignee: '{assignee}'")
                
                if invalid_assignees:
                    return self._create_standardized_error(
                        operation="create_task",
                        field="assignees",
                        expected="Valid agent roles from AgentRole enum",
                        hint=f"Invalid assignees: {invalid_assignees}. Use valid agent roles like 'coding-agent', 'test-orchestrator-agent'"
                    )
                
                if not validated_assignees:
                    return self._create_standardized_error(
                        operation="create_task",
                        field="assignees",
                        expected="At least one valid agent must be assigned",
                        hint="Provide at least one valid agent role like 'coding-agent' or 'test-orchestrator-agent'"
                    )
                
                assignees = validated_assignees
                logger.info(f"Validated {len(assignees)} assignees for task creation: {assignees}")
                
            except Exception as e:
                logger.error(f"Unexpected error during assignee validation: {str(e)}")
                return self._create_standardized_error(
                    operation="create_task",
                    field="assignees",
                    expected="Valid agent roles from AgentRole enum",
                    hint=f"Error validating assignees: {str(e)}. Use valid agent roles like 'coding-agent', 'test-orchestrator-agent'"
                )
        
        request = CreateTaskRequest(
            title=title,
            description=description or f"Description for {title}",
            git_branch_id=git_branch_id,
            status=status,
            priority=priority,
            details=details or "",
            estimated_effort=estimated_effort,
            assignees=assignees or [],  # Use validated assignees
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
    
    def update_task(self, facade: TaskApplicationFacade, task_id: Optional[str] = None, title: Optional[str] = None,
                   description: Optional[str] = None, status: Optional[str] = None, priority: Optional[str] = None,
                   details: Optional[str] = None, estimated_effort: Optional[str] = None,
                   assignees: Optional[List[str]] = None, labels: Optional[List[str]] = None,
                   due_date: Optional[str] = None, context_id: Optional[str] = None,
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
                include_context: bool = True) -> Dict[str, Any]:
        """Handle task retrieval with optional context (defaults to True)."""
        logger.info(f"DEBUG: CRUDHandler.get_task called - task_id={task_id}, include_context={include_context}")
        print(f"[CRUD DEBUG] get_task called with task_id={task_id}, include_context={include_context}")
        if not task_id:
            return self._create_standardized_error(
                operation="get_task",
                field="task_id",
                expected="A valid task_id string",
                hint="Include 'task_id' in your request"
            )
        
        result = facade.get_task(task_id)
        
        if result.get("success") and include_context and result.get("task"):
            # Add context information if requested - FETCH INHERITED CONTEXT
            task_data = result["task"]
            task_context_id = task_data.get("context_id")
            logger.info(f"DEBUG: get_task - include_context={include_context}, task_context_id={task_context_id}")
            
            if task_context_id:
                try:
                    # Use the existing facade service to get context facade
                    from .....application.services.facade_service import FacadeService
                    facade_service = FacadeService.get_instance()
                    
                    # Get git_branch_id from task data for proper context scoping
                    git_branch_id = task_data.get("git_branch_id")
                    
                    # Get unified context facade for inheritance resolution
                    context_facade = facade_service.get_unified_context_facade()
                    
                    # Resolve task context with full inheritance using facade
                    inherited_context_result = context_facade.resolve_context(
                        level="task", 
                        context_id=task_context_id,
                        include_inherited=True
                    )
                    
                    inherited_context = {
                        "success": inherited_context_result.get("success", False),
                        "data": inherited_context_result
                    }
                    
                    if inherited_context.get("success") and inherited_context.get("data"):
                        # Check if we have resolved_context data
                        context_data = inherited_context["data"]
                        if "resolved_context" in context_data:
                            task_data["inherited_context"] = context_data["resolved_context"]
                        elif "context" in context_data:
                            task_data["inherited_context"] = context_data["context"]
                        else:
                            # Use the entire data as inherited context
                            task_data["inherited_context"] = context_data
                        result["include_context"] = True
                        result["task"]["context_available"] = True
                        result["task"]["inherited_context_available"] = True
                    else:
                        result["task"]["context_available"] = True
                        result["task"]["inherited_context_available"] = False
                
                except Exception as e:
                    logger.error(f"Failed to fetch inherited context for task {task_id}: {e}")
                    result["task"]["context_available"] = True
                    result["task"]["inherited_context_available"] = False
            else:
                result["task"]["context_available"] = False
                result["task"]["inherited_context_available"] = False
        
        return result
    
    def delete_task(self, facade: TaskApplicationFacade, task_id: Optional[str], user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle task deletion with authenticated user_id."""
        if not task_id:
            return self._create_standardized_error(
                operation="delete_task",
                field="task_id",
                expected="A valid task_id string",
                hint="Include 'task_id' in your request"
            )

        # Use the provided authenticated user_id instead of extracting from repository
        # This ensures WebSocket messages are sent with the correct user_id for authorization
        return facade.delete_task(task_id, user_id)
    
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

        # Extract user_id from facade's repository if available
        user_id = None
        if hasattr(facade, '_task_repository') and hasattr(facade._task_repository, '_user_id'):
            user_id = facade._task_repository._user_id

        # Use the facade's complete_task method directly
        # This properly handles both transitioning to done and updating already-done tasks
        return facade.complete_task(task_id, completion_summary, testing_notes, user_id)
    
    def _create_standardized_error(self, operation: str, field: str, 
                                 expected: str, hint: str) -> Dict[str, Any]:
        """Create standardized validation error."""
        return self._response_formatter.create_error_response(
            operation=operation,
            error=f"Missing required field: {field}. Expected: {expected}",
            error_code=ErrorCodes.VALIDATION_ERROR,
            metadata={"field": field, "hint": hint}
        )