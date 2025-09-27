"""Task State Transition Service - Domain Service for Task Status Business Rules"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Protocol
from datetime import datetime, timezone
from enum import Enum

from ..entities.task import Task
from ..entities.subtask import Subtask
from ..value_objects.task_status import TaskStatus
from ..value_objects.task_id import TaskId
from ..exceptions.task_exceptions import TaskStateTransitionError

logger = logging.getLogger(__name__)


class TransitionContext(Enum):
    """Context for state transitions."""
    USER_INITIATED = "user_initiated"
    SYSTEM_INITIATED = "system_initiated"
    DEPENDENCY_TRIGGERED = "dependency_triggered"
    COMPLETION_TRIGGERED = "completion_triggered"


class SubtaskRepositoryProtocol(Protocol):
    """Protocol for subtask repository to avoid infrastructure dependency."""
    
    def find_by_parent_task_id(self, task_id: TaskId) -> List[Subtask]:
        """Find all subtasks for a given parent task."""
        pass


class TaskRepositoryProtocol(Protocol):
    """Protocol for task repository to avoid infrastructure dependency."""
    
    def find_all(self) -> List[Task]:
        """Find all tasks."""
        pass


class TaskStateTransitionService:
    """
    Domain service that manages task state transitions and enforces business rules.
    
    This service centralizes the logic for:
    - Valid state transitions
    - Transition prerequisites and conditions
    - Automatic state changes based on dependencies
    - State-specific business rules and side effects
    
    State Machine:
    TODO → IN_PROGRESS → REVIEW → TESTING → DONE
      ↓         ↓          ↓        ↓
    BLOCKED ← ← ← ← ← ← ← ← ← ← ← ← ← ←
      ↓
    CANCELLED
    """
    
    def __init__(self, 
                 subtask_repository: Optional[SubtaskRepositoryProtocol] = None,
                 task_repository: Optional[TaskRepositoryProtocol] = None):
        """
        Initialize the task state transition service.
        
        Args:
            subtask_repository: Repository for subtask validation (optional)
            task_repository: Repository for dependency validation (optional)
        """
        self._subtask_repository = subtask_repository
        self._task_repository = task_repository
        
        # Define the state transition rules
        self._transition_rules = self._initialize_transition_rules()
    
    def can_transition_to(self, task: Task, target_status: TaskStatus, context: TransitionContext = TransitionContext.USER_INITIATED) -> Tuple[bool, Optional[str]]:
        """
        Check if a task can transition to a target status.
        
        Args:
            task: The task to check
            target_status: The desired target status
            context: Context of the transition
            
        Returns:
            Tuple of (can_transition: bool, reason: Optional[str])
        """
        try:
            current_status = str(task.status).lower()
            target_status_str = str(target_status).lower()
            
            # Check if transition is allowed by state machine rules
            allowed_transitions = self._transition_rules.get(current_status, [])
            if target_status_str not in allowed_transitions:
                return False, f"Cannot transition from '{current_status}' to '{target_status_str}'"
            
            # Check context-specific prerequisites
            can_transition, reason = self._check_transition_prerequisites(task, target_status, context)
            if not can_transition:
                return False, reason
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error checking transition for task {task.id} to {target_status}: {e}")
            return False, f"Transition validation error: {str(e)}"
    
    def transition_to(self, task: Task, target_status: TaskStatus, context: TransitionContext = TransitionContext.USER_INITIATED, metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """
        Perform a state transition on a task.
        
        Args:
            task: The task to transition
            target_status: The target status
            context: Context of the transition
            metadata: Additional metadata for the transition
            
        Returns:
            Tuple of (success: bool, message: Optional[str])
        """
        try:
            metadata = metadata or {}
            
            # Check if transition is allowed
            can_transition, reason = self.can_transition_to(task, target_status, context)
            if not can_transition:
                return False, reason
            
            old_status = task.status
            
            # Perform pre-transition actions
            self._perform_pre_transition_actions(task, target_status, context, metadata)
            
            # Update task status
            task.update_status(target_status)
            
            # Perform post-transition actions
            self._perform_post_transition_actions(task, old_status, target_status, context, metadata)
            
            logger.info(f"Task {task.id} successfully transitioned from '{old_status}' to '{target_status}' (context: {context.value})")
            return True, f"Status changed from '{old_status}' to '{target_status}'"
            
        except Exception as e:
            logger.error(f"Error transitioning task {task.id} to {target_status}: {e}")
            return False, f"Transition failed: {str(e)}"
    
    def get_allowed_transitions(self, task: Task) -> Dict[str, Dict[str, Any]]:
        """
        Get all allowed transitions for a task with their conditions.
        
        Args:
            task: The task to check
            
        Returns:
            Dictionary of allowed transitions with metadata
        """
        try:
            current_status = str(task.status).lower()
            allowed_transitions = self._transition_rules.get(current_status, [])
            
            result = {}
            
            for target_status in allowed_transitions:
                target_status_obj = self._create_status_from_string(target_status)
                can_transition, reason = self.can_transition_to(task, target_status_obj)
                
                result[target_status] = {
                    "allowed": can_transition,
                    "reason": reason,
                    "description": self._get_transition_description(current_status, target_status),
                    "prerequisites": self._get_transition_prerequisites_description(current_status, target_status)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting allowed transitions for task {task.id}: {e}")
            return {}
    
    def suggest_next_status(self, task: Task) -> Optional[Dict[str, Any]]:
        """
        Suggest the next logical status for a task based on its current state.
        
        Args:
            task: The task to analyze
            
        Returns:
            Dictionary with suggested status and reasoning, or None
        """
        try:
            current_status = str(task.status).lower()
            
            # Define logical progression paths
            progression_paths = {
                'todo': 'in_progress',
                'in_progress': 'review',
                'review': 'testing',
                'testing': 'done',
                'blocked': 'todo'  # Assuming blocker was resolved
            }
            
            suggested_status = progression_paths.get(current_status)
            if not suggested_status:
                return None
            
            # Check if suggested transition is possible
            suggested_status_obj = self._create_status_from_string(suggested_status)
            can_transition, reason = self.can_transition_to(task, suggested_status_obj)
            
            if can_transition:
                return {
                    "suggested_status": suggested_status,
                    "current_status": current_status,
                    "reason": f"Natural progression from '{current_status}' to '{suggested_status}'",
                    "description": self._get_transition_description(current_status, suggested_status)
                }
            else:
                return {
                    "suggested_status": suggested_status,
                    "current_status": current_status,
                    "blocked": True,
                    "blocked_reason": reason,
                    "alternative_suggestions": self._get_alternative_suggestions(task)
                }
                
        except Exception as e:
            logger.error(f"Error suggesting next status for task {task.id}: {e}")
            return None
    
    def handle_dependency_completion(self, completed_task: Task) -> List[Dict[str, Any]]:
        """
        Handle automatic state transitions when a dependency is completed.
        
        Args:
            completed_task: The task that was just completed
            
        Returns:
            List of tasks that had their status updated
        """
        if not self._task_repository:
            return []
        
        try:
            updated_tasks = []
            all_tasks = self._task_repository.find_all()
            
            # Find tasks that depend on the completed task
            dependent_tasks = self._find_dependent_tasks(completed_task, all_tasks)
            
            for dependent_task in dependent_tasks:
                # Check if this completion unblocks the dependent task
                if str(dependent_task.status).lower() == 'blocked':
                    # Check if all dependencies are now satisfied
                    if self._all_dependencies_satisfied(dependent_task, all_tasks):
                        success, message = self.transition_to(
                            dependent_task, 
                            self._create_status_from_string('todo'), 
                            TransitionContext.DEPENDENCY_TRIGGERED,
                            {"trigger_task": str(completed_task.id)}
                        )
                        
                        if success:
                            updated_tasks.append({
                                "task_id": str(dependent_task.id),
                                "title": dependent_task.title,
                                "old_status": "blocked",
                                "new_status": "todo",
                                "reason": f"Unblocked by completion of task {completed_task.id}"
                            })
                        
            return updated_tasks
            
        except Exception as e:
            logger.error(f"Error handling dependency completion for task {completed_task.id}: {e}")
            return []
    
    def _initialize_transition_rules(self) -> Dict[str, List[str]]:
        """Initialize the state transition rules."""
        return {
            'todo': ['in_progress', 'blocked', 'cancelled'],
            'in_progress': ['review', 'testing', 'done', 'blocked', 'todo'],
            'review': ['in_progress', 'testing', 'done', 'blocked'],
            'testing': ['review', 'done', 'in_progress', 'blocked'],
            'blocked': ['todo', 'in_progress', 'cancelled'],
            'done': [],  # Done tasks generally shouldn't change status
            'cancelled': []  # Cancelled tasks shouldn't change status
        }
    
    def _check_transition_prerequisites(self, task: Task, target_status: TaskStatus, context: TransitionContext) -> Tuple[bool, Optional[str]]:
        """Check if prerequisites are met for a specific transition."""
        target_status_str = str(target_status).lower()
        current_status_str = str(task.status).lower()
        
        # Prerequisites for transitioning to 'done'
        if target_status_str == 'done':
            # Check if all subtasks are completed
            if self._subtask_repository:
                subtasks = self._subtask_repository.find_by_parent_task_id(task.id)
                incomplete_subtasks = [s for s in subtasks if not s.is_completed]
                
                if incomplete_subtasks:
                    return False, f"Cannot complete task: {len(incomplete_subtasks)} subtasks are still incomplete"
        
        # Prerequisites for transitioning to 'in_progress'
        if target_status_str == 'in_progress' and current_status_str == 'blocked':
            # When transitioning from blocked to in_progress, ensure blockers are resolved
            # This would require additional context about what was blocking the task
            pass
        
        # Prerequisites for transitioning to 'review'
        if target_status_str == 'review':
            # Could check if work has been completed to a reviewable state
            # For now, we allow this transition if the task is in_progress
            if current_status_str != 'in_progress':
                return False, "Task must be in progress before moving to review"
        
        return True, None
    
    def _perform_pre_transition_actions(self, task: Task, target_status: TaskStatus, context: TransitionContext, metadata: Dict[str, Any]):
        """Perform actions before the status transition."""
        target_status_str = str(target_status).lower()
        
        # Actions when transitioning to 'in_progress'
        if target_status_str == 'in_progress':
            # Could update started_at timestamp, assign default assignee, etc.
            pass
        
        # Actions when transitioning to 'done'
        if target_status_str == 'done':
            # Could validate completion requirements, update completion timestamp
            if not hasattr(task, '_completion_summary') or not task._completion_summary:
                # This could be a warning rather than blocking the transition
                logger.warning(f"Task {task.id} completed without completion summary")
    
    def _perform_post_transition_actions(self, task: Task, old_status: TaskStatus, new_status: TaskStatus, context: TransitionContext, metadata: Dict[str, Any]):
        """Perform actions after the status transition."""
        new_status_str = str(new_status).lower()
        
        # Actions after transitioning to 'done'
        if new_status_str == 'done':
            # Trigger dependency resolution for other tasks
            if self._task_repository:
                self.handle_dependency_completion(task)
        
        # Actions after transitioning to 'blocked'
        if new_status_str == 'blocked':
            # Could send notifications, log blocking reasons, etc.
            logger.info(f"Task {task.id} has been blocked. Reason: {metadata.get('blocking_reason', 'Not specified')}")
    
    def _find_dependent_tasks(self, completed_task: Task, all_tasks: List[Task]) -> List[Task]:
        """Find tasks that depend on the completed task."""
        dependent_tasks = []
        completed_task_id = str(completed_task.id)
        
        for task in all_tasks:
            if hasattr(task, 'dependencies') and task.dependencies:
                for dep_id in task.dependencies:
                    if str(dep_id) == completed_task_id:
                        dependent_tasks.append(task)
                        break
        
        return dependent_tasks
    
    def _all_dependencies_satisfied(self, task: Task, all_tasks: List[Task]) -> bool:
        """Check if all dependencies of a task are satisfied."""
        if not hasattr(task, 'dependencies') or not task.dependencies:
            return True
        
        for dep_id in task.dependencies:
            dep_id_str = str(dep_id)
            dependency_satisfied = False
            
            for other_task in all_tasks:
                if str(other_task.id) == dep_id_str:
                    if other_task.status.is_done() if hasattr(other_task.status, 'is_done') else str(other_task.status).lower() == 'done':
                        dependency_satisfied = True
                    break
            
            if not dependency_satisfied:
                return False
        
        return True
    
    def _create_status_from_string(self, status_str: str) -> TaskStatus:
        """Create TaskStatus object from string."""
        # This is a simplified implementation - in reality, you'd use the proper TaskStatus factory
        return TaskStatus(status_str)
    
    def _get_transition_description(self, from_status: str, to_status: str) -> str:
        """Get human-readable description of a transition."""
        descriptions = {
            ('todo', 'in_progress'): "Start working on this task",
            ('in_progress', 'review'): "Submit work for review",
            ('review', 'testing'): "Move to testing phase",
            ('testing', 'done'): "Mark as completed",
            ('blocked', 'todo'): "Unblock and return to todo",
            ('in_progress', 'blocked'): "Block due to impediment"
        }
        
        return descriptions.get((from_status, to_status), f"Change status from {from_status} to {to_status}")
    
    def _get_transition_prerequisites_description(self, from_status: str, to_status: str) -> List[str]:
        """Get description of prerequisites for a transition."""
        prerequisites = {
            ('todo', 'in_progress'): ["Task assignee available", "Dependencies satisfied"],
            ('in_progress', 'review'): ["Work completed", "Ready for review"],
            ('review', 'testing'): ["Review passed", "Code approved"],
            ('testing', 'done'): ["Tests passed", "All subtasks completed"],
            ('blocked', 'todo'): ["Blocking issues resolved"]
        }
        
        return prerequisites.get((from_status, to_status), [])
    
    def _get_alternative_suggestions(self, task: Task) -> List[str]:
        """Get alternative status suggestions when primary suggestion is blocked."""
        current_status = str(task.status).lower()
        
        alternatives = {
            'todo': ['blocked'],  # If can't start, maybe it's blocked
            'in_progress': ['blocked', 'todo'],  # If can't progress, maybe blocked or need to restart
            'review': ['in_progress'],  # If review failed, back to in_progress
            'testing': ['review', 'in_progress'],  # If testing failed, back to review or rework
            'blocked': ['cancelled']  # If still blocked, maybe cancel
        }
        
        return alternatives.get(current_status, [])