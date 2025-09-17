"""
Parameter Validator for Task MCP Controller

Validates input parameters for task operations.
"""

import logging
import re
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from ....utils.response_formatter import StandardResponseFormatter, ErrorCodes

logger = logging.getLogger(__name__)


class ParameterValidator:
    """Validates parameters for task operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
    
    def validate_create_task_params(self, title: Optional[str], git_branch_id: Optional[str],
                                  description: Optional[str] = None,
                                  status: Optional[str] = None,
                                  priority: Optional[str] = None,
                                  due_date: Optional[str] = None,
                                  assignees: Optional[List[str]] = None,
                                  labels: Optional[List[str]] = None,
                                  dependencies: Optional[List[str]] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate parameters for task creation."""
        
        # Validate required fields
        if not title or not title.strip():
            return False, self._create_validation_error(
                "title", "A non-empty title string", "Include 'title' in your request"
            )
        
        if not git_branch_id:
            return False, self._create_validation_error(
                "git_branch_id", "A valid git_branch_id string", 
                "Include 'git_branch_id' in your request"
            )
        
        # Validate git_branch_id format (should be UUID)
        if not self._is_valid_uuid(git_branch_id):
            return False, self._create_validation_error(
                "git_branch_id", "A valid UUID format",
                "git_branch_id should be a valid UUID"
            )
        
        # Validate optional fields
        if status and not self._is_valid_status(status):
            return False, self._create_validation_error(
                "status", "One of: todo, in_progress, blocked, review, testing, done, cancelled, archived",
                "Use a valid task status"
            )
        
        if priority and not self._is_valid_priority(priority):
            return False, self._create_validation_error(
                "priority", "One of: low, medium, high, urgent, critical",
                "Use a valid priority level"
            )
        
        if due_date and not self._is_valid_date_format(due_date):
            return False, self._create_validation_error(
                "due_date", "ISO format date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
                "Use ISO date format"
            )
        
        if assignees and not self._is_valid_assignees_list(assignees):
            return False, self._create_validation_error(
                "assignees", "A list of valid agent identifiers or user IDs",
                "Assignees should be agent identifiers (e.g., 'coding-agent') or user IDs (e.g., 'user123')"
            )
        
        if labels and not self._is_valid_labels_list(labels):
            return False, self._create_validation_error(
                "labels", "A list of valid label strings",
                "Labels should be a list of strings"
            )
        
        if dependencies and not self._is_valid_dependencies_list(dependencies):
            return False, self._create_validation_error(
                "dependencies", "A list of valid task IDs",
                "Dependencies should be a list of valid UUIDs"
            )
        
        return True, None
    
    def validate_update_task_params(self, task_id: Optional[str], **kwargs) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate parameters for task update."""
        
        if not task_id:
            return False, self._create_validation_error(
                "task_id", "A valid task_id string",
                "Include 'task_id' in your request"
            )
        
        if not self._is_valid_uuid(task_id):
            return False, self._create_validation_error(
                "task_id", "A valid UUID format",
                "task_id should be a valid UUID"
            )
        
        # Validate optional update fields
        if 'status' in kwargs and kwargs['status'] and not self._is_valid_status(kwargs['status']):
            return False, self._create_validation_error(
                "status", "One of: todo, in_progress, blocked, review, testing, done, cancelled, archived",
                "Use a valid task status"
            )
        
        if 'priority' in kwargs and kwargs['priority'] and not self._is_valid_priority(kwargs['priority']):
            return False, self._create_validation_error(
                "priority", "One of: low, medium, high, urgent, critical",
                "Use a valid priority level"
            )
        
        if 'due_date' in kwargs and kwargs['due_date'] and not self._is_valid_date_format(kwargs['due_date']):
            return False, self._create_validation_error(
                "due_date", "ISO format date string",
                "Use ISO date format"
            )
        
        return True, None
    
    def validate_search_params(self, query: Optional[str] = None, 
                             **filters) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate parameters for task search."""
        
        # For search operations, query is required
        if query is not None and (not query or not query.strip()):
            return False, self._create_validation_error(
                "query", "A non-empty search query string",
                "Include a valid 'query' in your request"
            )
        
        # Validate filter parameters
        if 'status' in filters and filters['status'] and not self._is_valid_status(filters['status']):
            return False, self._create_validation_error(
                "status", "One of: todo, in_progress, blocked, review, testing, done, cancelled, archived",
                "Use a valid task status for filtering"
            )
        
        if 'priority' in filters and filters['priority'] and not self._is_valid_priority(filters['priority']):
            return False, self._create_validation_error(
                "priority", "One of: low, medium, high, urgent, critical",
                "Use a valid priority level for filtering"
            )
        
        if 'limit' in filters and filters['limit'] is not None:
            if not isinstance(filters['limit'], int) or filters['limit'] < 0 or filters['limit'] > 1000:
                return False, self._create_validation_error(
                    "limit", "An integer between 0 and 1000",
                    "Use a reasonable limit for results"
                )
        
        if 'offset' in filters and filters['offset'] is not None:
            if not isinstance(filters['offset'], int) or filters['offset'] < 0:
                return False, self._create_validation_error(
                    "offset", "A non-negative integer",
                    "Offset should be 0 or greater"
                )
        
        return True, None
    
    def _is_valid_uuid(self, value: str) -> bool:
        """Check if string is a valid UUID."""
        try:
            uuid.UUID(value)
            return True
        except (ValueError, TypeError):
            return False
    
    def _is_valid_status(self, status: str) -> bool:
        """Check if status is valid."""
        # CRITICAL FIX: Updated to match domain model TaskStatusEnum values
        valid_statuses = {"todo", "in_progress", "blocked", "review", "testing", "done", "cancelled", "archived"}
        return status.lower() in valid_statuses
    
    def _is_valid_priority(self, priority: str) -> bool:
        """Check if priority is valid."""
        valid_priorities = {"low", "medium", "high", "urgent", "critical"}
        return priority.lower() in valid_priorities
    
    def _is_valid_date_format(self, date_str: str) -> bool:
        """Check if date string is in valid ISO format."""
        try:
            # Try parsing as datetime
            datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return True
        except ValueError:
            try:
                # Try parsing as date only
                datetime.strptime(date_str, '%Y-%m-%d')
                return True
            except ValueError:
                return False
    
    def _is_valid_assignees_list(self, assignees: List[str]) -> bool:
        """Check if assignees list is valid.
        
        Accepts various assignee formats:
        - Agent identifiers with @ prefix (e.g., "coding-agent")
        - Agent identifiers without @ prefix (e.g., "coding-agent") 
        - User IDs (e.g., "user123")
        """
        if not isinstance(assignees, list):
            return False
        
        for assignee in assignees:
            if not isinstance(assignee, str) or not assignee.strip():
                return False
                
            # Allow agent identifiers with/without @ prefix and user IDs
            # Basic validation: non-empty string with valid characters
            clean_assignee = assignee.strip()
            if not clean_assignee:
                return False
                
            # Allow alphanumeric characters, hyphens, underscores, and @ prefix
            import re
            if not re.match(r'^@?[a-zA-Z0-9_-]+$', clean_assignee):
                return False
        
        return True
    
    def _is_valid_labels_list(self, labels: List[str]) -> bool:
        """Check if labels list is valid."""
        if not isinstance(labels, list):
            return False
        
        for label in labels:
            if not isinstance(label, str) or not label.strip():
                return False
            # Labels should be alphanumeric with hyphens/underscores
            if not re.match(r'^[a-zA-Z0-9_-]+$', label.strip()):
                return False
        
        return True
    
    def _is_valid_dependencies_list(self, dependencies: List[str]) -> bool:
        """Check if dependencies list contains valid UUIDs."""
        if not isinstance(dependencies, list):
            return False
        
        for dep_id in dependencies:
            if not isinstance(dep_id, str) or not self._is_valid_uuid(dep_id):
                return False
        
        return True
    
    def _create_validation_error(self, field: str, expected: str, hint: str) -> Dict[str, Any]:
        """Create standardized validation error."""
        return self._response_formatter.create_error_response(
            operation="validate_parameters",
            error=f"Invalid field: {field}. Expected: {expected}",
            error_code=ErrorCodes.VALIDATION_ERROR,
            metadata={"field": field, "hint": hint}
        )