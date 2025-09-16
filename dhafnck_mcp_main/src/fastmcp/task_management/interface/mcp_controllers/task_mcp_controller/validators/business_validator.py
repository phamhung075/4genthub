"""
Business Validator for Task MCP Controller

Validates business rules and logic for task operations.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

from ....utils.response_formatter import StandardResponseFormatter, ErrorCodes

logger = logging.getLogger(__name__)


class BusinessValidator:
    """Validates business rules for task operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
    
    def validate_task_creation_rules(self, title: str, git_branch_id: str,
                                   priority: Optional[str] = None,
                                   due_date: Optional[str] = None,
                                   dependencies: Optional[List[str]] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate business rules for task creation."""
        
        # Rule: Task title should be meaningful
        if len(title.strip()) < 3:
            return False, self._create_business_error(
                "title_length",
                "Task title must be at least 3 characters long",
                "Provide a more descriptive title for the task"
            )
        
        # Rule: Critical tasks should have due dates
        if priority and priority.lower() == "critical" and not due_date:
            logger.warning(f"Critical task '{title}' created without due date")
            # This is a warning, not a blocking error
        
        # Rule: Due date should not be in the past (with some tolerance)
        if due_date:
            try:
                due_datetime = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                
                # Allow up to 1 hour in the past to account for timezone differences
                if due_datetime < now and (now - due_datetime).total_seconds() > 3600:
                    return False, self._create_business_error(
                        "due_date_past",
                        "Due date cannot be significantly in the past",
                        "Set a due date in the future or remove the due date"
                    )
            except ValueError:
                pass  # Date format validation handled elsewhere
        
        # Rule: Self-dependency check (if dependencies provided)
        # Note: We can't check this at creation since task ID doesn't exist yet
        
        return True, None
    
    def validate_task_update_rules(self, task_id: str, current_task_data: Optional[Dict[str, Any]] = None,
                                 status: Optional[str] = None,
                                 priority: Optional[str] = None,
                                 due_date: Optional[str] = None,
                                 dependencies: Optional[List[str]] = None,
                                 completion_summary: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate business rules for task updates."""
        
        # Rule: Cannot self-reference in dependencies
        if dependencies and task_id in dependencies:
            return False, self._create_business_error(
                "self_dependency",
                "Task cannot depend on itself",
                "Remove the task's own ID from the dependencies list"
            )
        
        # Rule: Completion requires summary for important tasks
        if status and status.lower() == "completed" and current_task_data:
            current_priority = current_task_data.get("priority", "medium")
            
            if current_priority.lower() in ["high", "critical"] and not completion_summary:
                logger.warning(f"High/critical priority task {task_id} completed without summary")
                # This is a warning, not a blocking error for flexibility
        
        # Rule: Status transition validation
        if status and current_task_data:
            current_status = current_task_data.get("status", "pending")
            if not self._is_valid_status_transition(current_status, status):
                return False, self._create_business_error(
                    "invalid_status_transition",
                    f"Cannot transition from '{current_status}' to '{status}'",
                    f"Valid transitions from '{current_status}': {self._get_valid_transitions(current_status)}"
                )
        
        # Rule: Due date changes on completed tasks
        if due_date and current_task_data and current_task_data.get("status") == "completed":
            return False, self._create_business_error(
                "completed_task_due_date",
                "Cannot change due date of completed task",
                "Reopen the task before changing the due date"
            )
        
        return True, None
    
    def validate_task_deletion_rules(self, task_id: str, 
                                   current_task_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate business rules for task deletion."""
        
        if not current_task_data:
            return True, None  # Cannot validate without current data
        
        # Rule: Cannot delete tasks with active dependencies
        # This would require checking other tasks that depend on this one
        # For now, we'll log a warning and allow the deletion
        status = current_task_data.get("status", "pending")
        
        if status == "in_progress":
            logger.warning(f"Deleting in-progress task {task_id}")
            # Allow but warn - business might want to block this
        
        return True, None
    
    def validate_completion_requirements(self, task_data: Dict[str, Any],
                                       completion_summary: Optional[str] = None,
                                       testing_notes: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate requirements for task completion."""
        
        priority = task_data.get("priority", "medium")
        title = task_data.get("title", "Unknown task")
        
        # Rule: High priority tasks should have completion summaries
        if priority.lower() in ["high", "critical"]:
            if not completion_summary or len(completion_summary.strip()) < 10:
                return False, self._create_business_error(
                    "completion_summary_required",
                    f"High/critical priority tasks require detailed completion summary (minimum 10 characters)",
                    "Add a meaningful completion summary explaining what was accomplished"
                )
        
        # Rule: Tasks with 'test' or 'bug' in title should have testing notes
        if any(keyword in title.lower() for keyword in ['test', 'bug', 'fix', 'issue']):
            if not testing_notes:
                logger.warning(f"Task '{title}' appears to be test/bug-related but has no testing notes")
                # This is a warning, not a blocking error
        
        return True, None
    
    def _is_valid_status_transition(self, from_status: str, to_status: str) -> bool:
        """Check if status transition is valid according to business rules."""
        
        # Define valid transitions
        valid_transitions = {
            "pending": ["in_progress", "blocked", "cancelled"],
            "in_progress": ["completed", "blocked", "pending", "in_progress"],
            "blocked": ["pending", "in_progress", "cancelled"],
            "completed": ["pending", "in_progress"],  # Allow reopening
            "cancelled": ["pending"]  # Allow reactivation
        }
        
        from_status_lower = from_status.lower()
        to_status_lower = to_status.lower()
        
        if from_status_lower not in valid_transitions:
            return True  # Unknown status, allow transition
        
        return to_status_lower in valid_transitions[from_status_lower]
    
    def _get_valid_transitions(self, from_status: str) -> List[str]:
        """Get list of valid status transitions from current status."""
        
        valid_transitions = {
            "pending": ["in_progress", "blocked", "cancelled"],
            "in_progress": ["completed", "blocked", "pending", "in_progress"],
            "blocked": ["pending", "in_progress", "cancelled"],
            "completed": ["pending", "in_progress"],
            "cancelled": ["pending"]
        }
        
        return valid_transitions.get(from_status.lower(), [])
    
    def _create_business_error(self, rule_name: str, message: str, hint: str) -> Dict[str, Any]:
        """Create standardized business rule validation error."""
        return self._response_formatter.create_error_response(
            operation="validate_business_rules",
            error=f"Business rule violation ({rule_name}): {message}",
            error_code=ErrorCodes.BUSINESS_RULE_VIOLATION,
            metadata={"rule": rule_name, "hint": hint}
        )