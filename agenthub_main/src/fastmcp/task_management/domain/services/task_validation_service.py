"""Task Validation Service - Domain Service for Complex Task Business Validation"""

import logging
from typing import List, Dict, Any, Optional, Protocol, Tuple
from datetime import datetime, timezone

from ..entities.task import Task
from ..value_objects.task_id import TaskId
from ..value_objects.task_status import TaskStatus
from ..value_objects.priority import Priority
from ..exceptions.task_exceptions import TaskValidationError
from ....utilities.id_validator import IDValidator, IDValidationError, prevent_id_confusion

logger = logging.getLogger(__name__)


class GitBranchRepositoryProtocol(Protocol):
    """Protocol for git branch repository to avoid infrastructure dependency."""
    
    def exists(self, branch_id: str) -> bool:
        """Check if git branch exists."""
        pass
    
    def get_branch_info(self, branch_id: str) -> Optional[Dict[str, Any]]:
        """Get git branch information."""
        pass


class ProjectRepositoryProtocol(Protocol):
    """Protocol for project repository to avoid infrastructure dependency."""
    
    def exists(self, project_id: str) -> bool:
        """Check if project exists."""
        pass


class TaskValidationService:
    """
    Domain service that handles complex business validation rules for tasks.
    
    This service centralizes validation logic that goes beyond simple field validation,
    implementing business rules that span multiple entities and require domain knowledge.
    
    Validation Categories:
    - Relationship validation (git branch, project existence)
    - Business rule validation (title length, content appropriateness)
    - Constraint validation (assignee limits, label restrictions)
    - Consistency validation (status transitions, priority constraints)
    """
    
    def __init__(self,
                 git_branch_repository: Optional[GitBranchRepositoryProtocol] = None,
                 project_repository: Optional[ProjectRepositoryProtocol] = None,
                 id_validator: Optional[IDValidator] = None):
        """
        Initialize the task validation service.

        Args:
            git_branch_repository: Repository for git branch validation (optional)
            project_repository: Repository for project validation (optional)
            id_validator: ID validation service to prevent MCP/Application ID confusion (optional)
        """
        self._git_branch_repository = git_branch_repository
        self._project_repository = project_repository
        self._id_validator = id_validator or IDValidator()
    
    def validate_task_creation(self, task: Task, additional_context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Perform comprehensive validation for task creation.
        
        Args:
            task: The task to validate
            additional_context: Additional context for validation
            
        Returns:
            List of validation error messages (empty if valid)
        """
        try:
            errors = []
            additional_context = additional_context or {}
            
            # Core field validation
            errors.extend(self._validate_core_fields(task))
            
            # Relationship validation
            errors.extend(self._validate_relationships(task))
            
            # Business rule validation
            errors.extend(self._validate_business_rules(task, 'create'))
            
            # Content validation
            errors.extend(self._validate_content(task))
            
            # Context-specific validation
            errors.extend(self._validate_creation_context(task, additional_context))
            
            return errors
            
        except Exception as e:
            logger.error(f"Error during task creation validation: {e}")
            return [f"Validation system error: {str(e)}"]
    
    def validate_task_update(self, current_task: Task, updated_task: Task, additional_context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Perform comprehensive validation for task updates.
        
        Args:
            current_task: The current task state
            updated_task: The proposed updated task state
            additional_context: Additional context for validation
            
        Returns:
            List of validation error messages (empty if valid)
        """
        try:
            errors = []
            additional_context = additional_context or {}
            
            # Core field validation for updated task
            errors.extend(self._validate_core_fields(updated_task))
            
            # Update-specific validation
            errors.extend(self._validate_update_constraints(current_task, updated_task))
            
            # Business rule validation
            errors.extend(self._validate_business_rules(updated_task, 'update'))
            
            # Content validation
            errors.extend(self._validate_content(updated_task))
            
            # Transition validation
            errors.extend(self._validate_status_transition(current_task, updated_task))
            
            return errors
            
        except Exception as e:
            logger.error(f"Error during task update validation: {e}")
            return [f"Validation system error: {str(e)}"]
    
    def validate_task_relationships(self, task: Task) -> Tuple[bool, List[str]]:
        """
        Validate task relationships (git branch, project, dependencies).
        
        Args:
            task: The task to validate relationships for
            
        Returns:
            Tuple of (is_valid: bool, error_messages: List[str])
        """
        try:
            errors = []
            
            # Validate git branch exists
            if hasattr(task, 'git_branch_id') and task.git_branch_id:
                if self._git_branch_repository and not self._git_branch_repository.exists(task.git_branch_id):
                    errors.append(f"Git branch '{task.git_branch_id}' does not exist")
            else:
                errors.append("Task must be associated with a valid git branch")
            
            # Validate project exists (if available)
            if hasattr(task, 'project_id') and task.project_id:
                if self._project_repository and not self._project_repository.exists(task.project_id):
                    errors.append(f"Project '{task.project_id}' does not exist")
            
            # Validate dependencies (circular dependency check would require additional context)
            if hasattr(task, 'dependencies') and task.dependencies:
                # Basic dependency validation
                if len(task.dependencies) > 10:  # Business rule: max 10 dependencies
                    errors.append("Task cannot have more than 10 dependencies")
                
                # Check for self-dependency
                task_id_str = str(task.id)
                for dep_id in task.dependencies:
                    if str(dep_id) == task_id_str:
                        errors.append("Task cannot depend on itself")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Error validating task relationships for task {task.id}: {e}")
            return False, [f"Relationship validation error: {str(e)}"]
    
    def validate_business_constraints(self, task: Task, operation_type: str = 'general') -> List[str]:
        """
        Validate business-specific constraints.
        
        Args:
            task: The task to validate
            operation_type: Type of operation ('create', 'update', 'complete')
            
        Returns:
            List of validation error messages
        """
        try:
            errors = []
            
            # Title constraints
            if not task.title or len(task.title.strip()) == 0:
                errors.append("Task title cannot be empty")
            elif len(task.title) > 200:
                errors.append("Task title cannot exceed 200 characters")
            elif len(task.title.strip()) < 3:
                errors.append("Task title must be at least 3 characters long")
            
            # Description constraints
            if hasattr(task, 'description') and task.description:
                if len(task.description) > 2000:
                    errors.append("Task description cannot exceed 2000 characters")
            
            # Assignee constraints
            if hasattr(task, 'assignees') and task.assignees:
                if len(task.assignees) > 5:  # Business rule: max 5 assignees
                    errors.append("Task cannot have more than 5 assignees")
                
                # Validate assignee format (basic validation)
                for assignee in task.assignees:
                    if not assignee or len(assignee.strip()) == 0:
                        errors.append("Assignee names cannot be empty")
                    elif len(assignee) > 50:
                        errors.append("Assignee names cannot exceed 50 characters")
            
            # Label constraints
            if hasattr(task, 'labels') and task.labels:
                if len(task.labels) > 10:  # Business rule: max 10 labels
                    errors.append("Task cannot have more than 10 labels")
                
                for label in task.labels:
                    if not label or len(label.strip()) == 0:
                        errors.append("Labels cannot be empty")
                    elif len(label) > 30:
                        errors.append("Labels cannot exceed 30 characters")
            
            # Due date constraints
            if hasattr(task, 'due_date') and task.due_date:
                now = datetime.now(timezone.utc)
                due_date = task.due_date
                
                # Ensure due_date is timezone-aware
                if due_date.tzinfo is None:
                    due_date = due_date.replace(tzinfo=timezone.utc)
                
                # Business rule: due date cannot be more than 2 years in the future
                max_future_date = now.replace(year=now.year + 2)
                if due_date > max_future_date:
                    errors.append("Due date cannot be more than 2 years in the future")
            
            # Priority and status combination validation
            if operation_type in ['create', 'update']:
                errors.extend(self._validate_priority_status_combination(task))
            
            return errors
            
        except Exception as e:
            logger.error(f"Error validating business constraints for task {task.id}: {e}")
            return [f"Business constraint validation error: {str(e)}"]
    
    def validate_content_appropriateness(self, task: Task) -> List[str]:
        """
        Validate content appropriateness and quality.
        
        Args:
            task: The task to validate
            
        Returns:
            List of validation error messages
        """
        try:
            errors = []
            
            # Title quality checks
            if task.title:
                title_lower = task.title.lower().strip()
                
                # Check for common placeholder text
                placeholders = ['todo', 'fix this', 'test', 'placeholder', 'tbd', 'to be done']
                if any(placeholder in title_lower for placeholder in placeholders):
                    errors.append("Task title appears to be placeholder text. Please provide a descriptive title.")
                
                # Check for excessive repetition
                words = title_lower.split()
                if len(words) > 1:
                    word_counts = {}
                    for word in words:
                        word_counts[word] = word_counts.get(word, 0) + 1
                    
                    max_repetition = max(word_counts.values())
                    if max_repetition > len(words) / 2:
                        errors.append("Task title contains too much repetition")
            
            # Description quality checks
            if hasattr(task, 'description') and task.description:
                desc_lower = task.description.lower().strip()
                
                # Check for meaningful content
                if len(desc_lower) < 10 and task.description.strip() not in ['', 'n/a', 'na', 'none']:
                    errors.append("Task description is too brief to be meaningful")
            
            # Estimated effort validation
            if hasattr(task, 'estimated_effort') and task.estimated_effort:
                effort = task.estimated_effort.strip().lower()
                
                # Validate effort format (basic patterns)
                valid_patterns = ['hour', 'day', 'week', 'month', 'minute', 'sprint', 'story point']
                if not any(pattern in effort for pattern in valid_patterns):
                    errors.append("Estimated effort should include time units (e.g., '2 hours', '1 day', '3 weeks')")
            
            return errors
            
        except Exception as e:
            logger.error(f"Error validating content appropriateness for task {task.id}: {e}")
            return [f"Content validation error: {str(e)}"]
    
    def _validate_core_fields(self, task: Task) -> List[str]:
        """Validate core required fields."""
        errors = []

        # Task ID validation with IDValidator
        if not task.id:
            errors.append("Task ID is required")
        else:
            task_id_str = str(task.id)
            id_result = self._id_validator.detect_id_type(task_id_str, "task_id")
            if not id_result.is_valid:
                errors.append(f"Invalid task ID format: {id_result.error_message}")
            elif id_result.warnings:
                # Log warnings but don't add as validation errors
                for warning in id_result.warnings:
                    logger.warning(f"Task ID validation warning: {warning}")

        # Title validation
        if not hasattr(task, 'title') or not task.title:
            errors.append("Task title is required")

        # Status validation
        if not hasattr(task, 'status') or not task.status:
            errors.append("Task status is required")

        # Priority validation
        if not hasattr(task, 'priority') or not task.priority:
            errors.append("Task priority is required")

        return errors
    
    def _validate_relationships(self, task: Task) -> List[str]:
        """Validate task relationships."""
        errors = []

        # Git branch relationship with ID validation
        if hasattr(task, 'git_branch_id'):
            if not task.git_branch_id:
                errors.append("Git branch ID is required")
            else:
                # Validate git branch ID format
                git_branch_result = self._id_validator.detect_id_type(task.git_branch_id, "git_branch_id")
                if not git_branch_result.is_valid:
                    errors.append(f"Invalid git branch ID format: {git_branch_result.error_message}")

                # Check if repository exists
                if self._git_branch_repository and not self._git_branch_repository.exists(task.git_branch_id):
                    errors.append(f"Git branch '{task.git_branch_id}' does not exist")

                # Critical: Prevent task_id being used as git_branch_id (common bug)
                if hasattr(task, 'id') and task.id and str(task.id) == str(task.git_branch_id):
                    errors.append(
                        "CRITICAL: Task ID and Git Branch ID are identical. "
                        "This indicates parameter confusion that leads to data integrity issues."
                    )

        # Project relationship with ID validation
        if hasattr(task, 'project_id') and task.project_id:
            project_result = self._id_validator.detect_id_type(task.project_id, "project_id")
            if not project_result.is_valid:
                errors.append(f"Invalid project ID format: {project_result.error_message}")
            elif self._project_repository and not self._project_repository.exists(task.project_id):
                errors.append(f"Project '{task.project_id}' does not exist")

        return errors
    
    def _validate_business_rules(self, task: Task, operation_type: str) -> List[str]:
        """Validate business-specific rules."""
        return self.validate_business_constraints(task, operation_type)
    
    def _validate_content(self, task: Task) -> List[str]:
        """Validate content quality."""
        return self.validate_content_appropriateness(task)
    
    def _validate_creation_context(self, task: Task, context: Dict[str, Any]) -> List[str]:
        """Validate creation-specific context."""
        errors = []
        
        # Check for duplicate titles in the same branch (if context provides this info)
        similar_tasks = context.get('similar_tasks', [])
        if similar_tasks:
            for similar_task in similar_tasks:
                if similar_task.get('title', '').lower().strip() == task.title.lower().strip():
                    errors.append(f"A task with similar title already exists: '{similar_task.get('title')}'")
                    break
        
        return errors
    
    def _validate_update_constraints(self, current_task: Task, updated_task: Task) -> List[str]:
        """Validate update-specific constraints."""
        errors = []
        
        # Certain fields cannot be changed after creation
        immutable_fields = ['id']
        
        for field in immutable_fields:
            if hasattr(current_task, field) and hasattr(updated_task, field):
                current_value = getattr(current_task, field)
                updated_value = getattr(updated_task, field)
                if current_value != updated_value:
                    errors.append(f"Field '{field}' cannot be modified after creation")
        
        return errors
    
    def _validate_status_transition(self, current_task: Task, updated_task: Task) -> List[str]:
        """Validate status transition rules."""
        errors = []
        
        current_status = str(current_task.status).lower()
        new_status = str(updated_task.status).lower()
        
        # Define valid transitions
        valid_transitions = {
            'todo': ['in_progress', 'blocked', 'cancelled'],
            'in_progress': ['review', 'testing', 'done', 'blocked', 'todo'],
            'review': ['in_progress', 'done', 'testing'],
            'testing': ['review', 'done', 'in_progress'],
            'blocked': ['todo', 'in_progress'],
            'done': [],  # Generally, done tasks shouldn't change status
            'cancelled': []  # Cancelled tasks shouldn't change status
        }
        
        if current_status != new_status:
            allowed_transitions = valid_transitions.get(current_status, [])
            if new_status not in allowed_transitions:
                errors.append(f"Invalid status transition from '{current_status}' to '{new_status}'")
        
        return errors

    def validate_id_parameters(self, task_id: Optional[str] = None,
                              git_branch_id: Optional[str] = None,
                              project_id: Optional[str] = None,
                              user_id: Optional[str] = None) -> List[str]:
        """
        Validate ID parameters to prevent confusion between MCP task IDs and application IDs.

        This method should be called before any facade service operations to prevent
        the critical bug where MCP task IDs are incorrectly passed as git_branch_ids.

        Args:
            task_id: Application task ID
            git_branch_id: Git branch ID
            project_id: Project ID
            user_id: User ID

        Returns:
            List of validation error messages (empty if valid)
        """
        try:
            result = self._id_validator.validate_parameter_mapping(
                task_id=task_id,
                git_branch_id=git_branch_id,
                project_id=project_id,
                user_id=user_id
            )

            errors = []
            if not result.is_valid:
                errors.append(result.error_message or "ID parameter validation failed")

            # Log warnings for monitoring
            if result.warnings:
                for warning in result.warnings:
                    logger.warning(f"ID Parameter Warning: {warning}")

            return errors

        except Exception as e:
            logger.error(f"Error during ID parameter validation: {e}")
            return [f"ID parameter validation error: {str(e)}"]

    def validate_task_context_integrity(self, task_id: str, expected_git_branch_id: Optional[str] = None) -> List[str]:
        """
        Validate task context to ensure proper ID relationships.

        This method helps prevent the critical issue where MCP task IDs
        are incorrectly used as git_branch_ids in facade service calls.

        Args:
            task_id: The task ID to validate
            expected_git_branch_id: The expected git_branch_id for cross-validation

        Returns:
            List of validation error messages (empty if valid)
        """
        try:
            result = self._id_validator.validate_task_context(task_id, expected_git_branch_id)

            errors = []
            if not result.is_valid:
                errors.append(result.error_message or "Task context validation failed")

            # Log warnings for monitoring
            if result.warnings:
                for warning in result.warnings:
                    logger.warning(f"Task Context Warning: {warning}")

            return errors

        except Exception as e:
            logger.error(f"Error during task context validation: {e}")
            return [f"Task context validation error: {str(e)}"]

    def _validate_priority_status_combination(self, task: Task) -> List[str]:
        """Validate priority and status combinations."""
        errors = []
        
        priority_str = str(task.priority).lower()
        status_str = str(task.status).lower()
        
        # Business rule: Critical priority tasks cannot be in 'todo' status for long
        if priority_str == 'critical' and status_str == 'todo':
            # Could check task age here, but for simplicity, just warn
            errors.append("Critical priority tasks should be started immediately")
        
        # Business rule: Done tasks with urgent/critical priority should have completion summary
        if status_str == 'done' and priority_str in ['urgent', 'critical']:
            if not hasattr(task, '_completion_summary') or not task._completion_summary:
                errors.append("High priority completed tasks must include completion summary")
        
        return errors