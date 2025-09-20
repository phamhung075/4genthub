"""Context Validation Service for Vision System.

This service provides validation logic for context updates,
ensuring Vision System requirements are met.
"""

from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime
import logging

from ...domain.entities.context import TaskContext
from ...domain.entities.task import Task
from ...domain.value_objects.context_enums import ContextLevel
from ...domain.exceptions.vision_exceptions import (
    InvalidContextUpdateError,
    MissingCompletionSummaryError
)
from ....utilities.id_validator import IDValidator, IDValidationError


logger = logging.getLogger(__name__)


class ContextValidationService:
    """Service for validating context updates according to Vision System rules."""

    def __init__(self, user_id: Optional[str] = None, id_validator: Optional[IDValidator] = None):
        """Initialize the context validation service."""
        self._user_id = user_id  # Store user context
        self._id_validator = id_validator or IDValidator()

    def _get_user_scoped_repository(self, repository: Any) -> Any:
        """Get a user-scoped version of the repository if it supports user context."""
        if not repository:
            return repository
        if hasattr(repository, 'with_user') and self._user_id:
            return repository.with_user(self._user_id)
        elif hasattr(repository, 'user_id'):
            if self._user_id and repository.user_id != self._user_id:
                repo_class = type(repository)
                if hasattr(repository, 'session'):
                    return repo_class(repository.session, user_id=self._user_id)
        return repository

    def with_user(self, user_id: str) -> 'ContextValidationService':
        """Create a new service instance scoped to a specific user."""
        return ContextValidationService(user_id, self._id_validator)
    
    def validate_completion_context(self, 
                                  task: Task, 
                                  context: TaskContext,
                                  completion_summary: str,
                                  testing_notes: Optional[str] = None,
                                  next_recommendations: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        Validate context for task completion.
        
        Args:
            task: The task being completed
            context: The task's context
            completion_summary: Summary of what was accomplished
            testing_notes: Optional testing notes
            next_recommendations: Optional next recommendations
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # 1. Validate completion_summary is provided and not empty
        if not completion_summary or not completion_summary.strip():
            errors.append("completion_summary is required and cannot be empty")
            
        # 2. Validate task ID format
        task_id_result = self._id_validator.detect_id_type(str(task.id), "task_id")
        if not task_id_result.is_valid:
            errors.append(f"Invalid task ID format: {task_id_result.error_message}")

        # 3. Validate context belongs to the task
        if context.metadata.task_id != str(task.id):
            errors.append(f"Context task_id {context.metadata.task_id} does not match task {task.id}")

            # Additional check for ID confusion
            context_id_result = self._id_validator.detect_id_type(context.metadata.task_id, "task_id")
            if not context_id_result.is_valid:
                errors.append(f"Invalid context task_id format: {context_id_result.error_message}")
            elif context.metadata.task_id == str(task.id):
                errors.append("CRITICAL: Context task_id and task ID mismatch may indicate ID confusion")
            
        # 3. Validate task is not already completed
        if task.is_completed:
            errors.append("Task is already completed")
            
        # 4. Validate all subtasks are completed
        # NOTE: Subtask completion validation is now handled by TaskCompletionService
        # which queries the SubtaskRepository. Task entity only stores subtask IDs.
            
        # 5. Log validation attempt
        logger.info(f"Validating completion context for task {task.id}: "
                   f"errors={len(errors)}, has_summary={bool(completion_summary)}")
        
        return len(errors) == 0, errors
    
    def validate_context_update(self,
                              context: TaskContext,
                              update_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate general context update.
        
        Args:
            context: The current context
            update_data: Data to update
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate data types
        if 'completion_percentage' in update_data:
            percentage = update_data['completion_percentage']
            if not isinstance(percentage, (int, float)) or percentage < 0 or percentage > 100:
                errors.append("completion_percentage must be a number between 0 and 100")
                
        if 'next_steps' in update_data:
            if not isinstance(update_data['next_steps'], list):
                errors.append("next_steps must be a list")
                
        if 'vision_alignment_score' in update_data:
            score = update_data['vision_alignment_score']
            if not isinstance(score, (int, float)) or score < 0 or score > 1:
                errors.append("vision_alignment_score must be a number between 0 and 1")
                
        return len(errors) == 0, errors
    
    def ensure_completion_summary_in_context(self,
                                           context: TaskContext,
                                           completion_summary: str,
                                           testing_notes: Optional[str] = None,
                                           next_recommendations: Optional[str] = None) -> None:
        """
        Ensure completion summary is properly set in context.
        
        Args:
            context: The task context to update
            completion_summary: Summary of what was accomplished
            testing_notes: Optional testing notes
            next_recommendations: Optional next recommendations
            
        Raises:
            InvalidContextUpdateError: If update fails validation
        """
        try:
            context.update_completion_summary(
                completion_summary=completion_summary,
                testing_notes=testing_notes,
                next_recommendations=next_recommendations
            )
        except ValueError as e:
            raise InvalidContextUpdateError(
                message=str(e),
                task_id=context.metadata.task_id,
                field="completion_summary"
            )
    
    def validate_progress_update(self,
                               progress_type: str,
                               details: str,
                               percentage: Optional[float] = None) -> Tuple[bool, List[str]]:
        """
        Validate progress update parameters.
        
        Args:
            progress_type: Type of progress (analysis, implementation, etc.)
            details: Progress details
            percentage: Optional progress percentage
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Valid progress types
        valid_types = [
            'analysis', 'design', 'implementation', 'testing', 
            'documentation', 'review', 'deployment', 'general'
        ]
        
        if progress_type not in valid_types:
            errors.append(f"Invalid progress_type. Must be one of: {', '.join(valid_types)}")
            
        if not details or not details.strip():
            errors.append("Progress details cannot be empty")
            
        if percentage is not None:
            if not isinstance(percentage, (int, float)) or percentage < 0 or percentage > 100:
                errors.append("Progress percentage must be between 0 and 100")
                
        return len(errors) == 0, errors
    
    def validate_checkpoint(self,
                          checkpoint_name: str,
                          state_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate checkpoint data.
        
        Args:
            checkpoint_name: Name of the checkpoint
            state_data: State data to save
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not checkpoint_name or not checkpoint_name.strip():
            errors.append("Checkpoint name cannot be empty")
            
        if not isinstance(state_data, dict):
            errors.append("State data must be a dictionary")
            
        # Validate state data size (prevent huge checkpoints)
        import json
        try:
            state_json = json.dumps(state_data)
            if len(state_json) > 1_000_000:  # 1MB limit
                errors.append("State data too large (max 1MB)")
        except Exception:
            errors.append("State data must be JSON serializable")
            
        return len(errors) == 0, errors
    
    def validate_context_data(self, 
                                   level: ContextLevel, 
                                   data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate context data for unified context system.
        
        Args:
            level: The context level being validated
            data: The context data to validate
            
        Returns:
            Dictionary with validation result: {"valid": bool, "errors": List[str]}
        """
        errors = []
        
        # Validate required fields based on level
        if level == ContextLevel.TASK:
            # Task level requirements
            if 'title' in data and not data['title'].strip():
                errors.append("Task title cannot be empty")
                
            if 'status' in data and data['status'] not in ['todo', 'in_progress', 'blocked', 'review', 'testing', 'done', 'cancelled']:
                errors.append("Invalid task status")
                
            if 'priority' in data and data['priority'] not in ['low', 'medium', 'high', 'urgent', 'critical']:
                errors.append("Invalid task priority")
                
        elif level == ContextLevel.PROJECT:
            # Project level requirements
            if 'name' in data and not data['name'].strip():
                errors.append("Project name cannot be empty")
                
        elif level == ContextLevel.BRANCH:
            # Branch level requirements
            if 'name' in data and not data['name'].strip():
                errors.append("Branch name cannot be empty")
                
        elif level == ContextLevel.GLOBAL:
            # Global level requirements (minimal validation)
            pass
        
        # Common validations for all levels
        if 'completion_percentage' in data:
            percentage = data['completion_percentage']
            if not isinstance(percentage, (int, float)) or percentage < 0 or percentage > 100:
                errors.append("completion_percentage must be a number between 0 and 100")
                
        if 'vision_alignment_score' in data:
            score = data['vision_alignment_score']
            if not isinstance(score, (int, float)) or score < 0 or score > 1:
                errors.append("vision_alignment_score must be a number between 0 and 1")
                
        if 'labels' in data and not isinstance(data['labels'], list):
            errors.append("labels must be a list")
            
        if 'assignees' in data and not isinstance(data['assignees'], list):
            errors.append("assignees must be a list")
            
        return {"valid": len(errors) == 0, "errors": errors}