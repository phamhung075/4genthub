"""Task Priority Service - Domain Service for Task Priority Business Rules"""

import logging
from typing import List, Dict, Any, Optional, Protocol
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from ..entities.task import Task
from ..value_objects.priority import Priority
from ..value_objects.task_status import TaskStatus
from ..value_objects.task_id import TaskId

logger = logging.getLogger(__name__)


class TaskRepositoryProtocol(Protocol):
    """Protocol for task repository to avoid infrastructure dependency."""
    
    def find_all(self) -> List[Task]:
        """Find all tasks."""
        pass
    
    def find_by_git_branch_id(self, git_branch_id: str) -> List[Task]:
        """Find tasks by git branch ID."""
        pass


class TaskPriorityService:
    """
    Domain service that handles task priority calculations and ordering.
    
    This service implements business rules for:
    - Priority scoring based on multiple factors
    - Task ordering for "next task" recommendations
    - Priority-based filtering and sorting
    - Dynamic priority adjustments based on context
    
    Priority Scoring Factors:
    - Base priority (high, medium, low)
    - Due date proximity
    - Dependency blocking factor
    - Task age (stale tasks get higher priority)
    - Progress status
    """
    
    def __init__(self, task_repository: Optional[TaskRepositoryProtocol] = None):
        """
        Initialize the task priority service.
        
        Args:
            task_repository: Repository for accessing task data (optional for basic calculations)
        """
        self._task_repository = task_repository
    
    def calculate_priority_score(self, task: Task, context_factors: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate a comprehensive priority score for a task.
        
        Args:
            task: The task to score
            context_factors: Additional context factors for scoring
            
        Returns:
            Priority score (0.0 to 100.0, higher = higher priority)
        """
        try:
            context_factors = context_factors or {}
            
            # Base priority weight (30%)
            base_score = self._calculate_base_priority_score(task) * 0.30
            
            # Due date urgency (25%)
            urgency_score = self._calculate_urgency_score(task) * 0.25
            
            # Blocking factor (20%)
            blocking_score = self._calculate_blocking_score(task, context_factors) * 0.20
            
            # Task age factor (15%)
            age_score = self._calculate_age_score(task) * 0.15
            
            # Progress factor (10%)
            progress_score = self._calculate_progress_score(task) * 0.10
            
            total_score = base_score + urgency_score + blocking_score + age_score + progress_score
            
            # Clamp to [0.0, 100.0]
            return max(0.0, min(100.0, total_score))
            
        except Exception as e:
            logger.error(f"Error calculating priority score for task {task.id}: {e}")
            return 0.0
    
    def order_tasks_by_priority(self, tasks: List[Task], context_factors: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Order tasks by priority score in descending order (highest priority first).
        
        Args:
            tasks: List of tasks to order
            context_factors: Additional context for priority calculation
            
        Returns:
            List of dictionaries with task and priority information
        """
        try:
            task_scores = []
            
            for task in tasks:
                score = self.calculate_priority_score(task, context_factors)
                task_scores.append({
                    "task": task,
                    "task_id": str(task.id),
                    "title": task.title,
                    "priority_score": score,
                    "base_priority": str(task.priority),
                    "status": str(task.status),
                    "priority_factors": self._get_priority_factors(task, context_factors)
                })
            
            # Sort by priority score (descending)
            task_scores.sort(key=lambda x: x["priority_score"], reverse=True)
            
            return task_scores
            
        except Exception as e:
            logger.error(f"Error ordering tasks by priority: {e}")
            return [{"task": task, "priority_score": 0.0, "error": str(e)} for task in tasks]
    
    def get_next_task_recommendation(self, git_branch_id: str, exclude_statuses: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Get the highest priority task recommendation for work.
        
        Args:
            git_branch_id: Git branch to filter tasks
            exclude_statuses: Task statuses to exclude (default: ['done', 'cancelled'])
            
        Returns:
            Dictionary with recommended task and reasoning, or None if no suitable task
        """
        if not self._task_repository:
            logger.warning("Cannot get next task recommendation without task repository")
            return None
        
        try:
            # Get tasks for the branch
            all_tasks = self._task_repository.find_by_git_branch_id(git_branch_id)
            
            if not all_tasks:
                return None
            
            # Filter out excluded statuses
            exclude_statuses = exclude_statuses or ['done', 'cancelled']
            eligible_tasks = [
                task for task in all_tasks 
                if str(task.status).lower() not in [status.lower() for status in exclude_statuses]
            ]
            
            if not eligible_tasks:
                return None
            
            # Order by priority
            ordered_tasks = self.order_tasks_by_priority(eligible_tasks)
            
            if not ordered_tasks:
                return None
            
            # Get the highest priority task
            recommended = ordered_tasks[0]
            
            return {
                "task": recommended["task"],
                "task_id": recommended["task_id"],
                "title": recommended["title"],
                "priority_score": recommended["priority_score"],
                "recommendation_reason": self._generate_recommendation_reason(recommended),
                "alternative_tasks": [
                    {
                        "task_id": task["task_id"],
                        "title": task["title"],
                        "priority_score": task["priority_score"]
                    }
                    for task in ordered_tasks[1:3]  # Next 2 alternatives
                ],
                "total_eligible_tasks": len(eligible_tasks)
            }
            
        except Exception as e:
            logger.error(f"Error getting next task recommendation for branch {git_branch_id}: {e}")
            return None
    
    def adjust_priority_for_dependencies(self, task: Task, all_tasks: Optional[List[Task]] = None) -> float:
        """
        Adjust task priority based on dependency relationships.
        
        Args:
            task: The task to adjust priority for
            all_tasks: All tasks in the system (for dependency analysis)
            
        Returns:
            Adjusted priority multiplier (0.5 to 2.0)
        """
        try:
            # If task has incomplete dependencies, lower its priority
            if hasattr(task, 'dependencies') and task.dependencies and all_tasks:
                incomplete_deps = self._count_incomplete_dependencies(task, all_tasks)
                if incomplete_deps > 0:
                    # Reduce priority based on number of incomplete dependencies
                    reduction = min(0.4, incomplete_deps * 0.1)
                    return max(0.5, 1.0 - reduction)
            
            # If other tasks depend on this task, increase its priority
            if all_tasks:
                dependent_count = self._count_tasks_depending_on(task, all_tasks)
                if dependent_count > 0:
                    # Increase priority based on number of dependent tasks
                    increase = min(1.0, dependent_count * 0.2)
                    return min(2.0, 1.0 + increase)
            
            return 1.0  # No adjustment
            
        except Exception as e:
            logger.error(f"Error adjusting priority for dependencies for task {task.id}: {e}")
            return 1.0
    
    def _calculate_base_priority_score(self, task: Task) -> float:
        """Calculate score based on task's assigned priority."""
        priority_str = str(task.priority).lower()
        
        priority_scores = {
            'critical': 100.0,
            'urgent': 90.0,
            'high': 75.0,
            'medium': 50.0,
            'low': 25.0
        }
        
        return priority_scores.get(priority_str, 50.0)  # Default to medium
    
    def _calculate_urgency_score(self, task: Task) -> float:
        """Calculate urgency score based on due date proximity."""
        if not hasattr(task, 'due_date') or not task.due_date:
            return 30.0  # Medium urgency for tasks without due dates
        
        try:
            now = datetime.now(timezone.utc)
            due_date = task.due_date
            
            # Ensure due_date is timezone-aware
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
            
            days_until_due = (due_date - now).days
            
            if days_until_due < 0:
                return 100.0  # Overdue = maximum urgency
            elif days_until_due == 0:
                return 90.0  # Due today
            elif days_until_due == 1:
                return 80.0  # Due tomorrow
            elif days_until_due <= 3:
                return 70.0  # Due within 3 days
            elif days_until_due <= 7:
                return 50.0  # Due within a week
            elif days_until_due <= 30:
                return 30.0  # Due within a month
            else:
                return 10.0  # Due later
                
        except Exception as e:
            logger.warning(f"Error calculating urgency for task {task.id}: {e}")
            return 30.0
    
    def _calculate_blocking_score(self, task: Task, context_factors: Dict[str, Any]) -> float:
        """Calculate score based on how much this task blocks others."""
        # If we have information about dependent tasks, factor that in
        dependent_count = context_factors.get('dependent_task_count', 0)
        
        if dependent_count == 0:
            return 20.0  # Base score for non-blocking tasks
        elif dependent_count == 1:
            return 40.0
        elif dependent_count <= 3:
            return 60.0
        elif dependent_count <= 5:
            return 80.0
        else:
            return 100.0  # High blocking factor
    
    def _calculate_age_score(self, task: Task) -> float:
        """Calculate score based on task age (older tasks get higher priority)."""
        try:
            now = datetime.now(timezone.utc)
            created_at = task.created_at
            
            # Ensure created_at is timezone-aware
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            
            age_days = (now - created_at).days
            
            if age_days <= 1:
                return 10.0  # Very new
            elif age_days <= 3:
                return 20.0  # New
            elif age_days <= 7:
                return 40.0  # A week old
            elif age_days <= 30:
                return 60.0  # A month old
            elif age_days <= 90:
                return 80.0  # 3 months old
            else:
                return 100.0  # Very stale
                
        except Exception as e:
            logger.warning(f"Error calculating age score for task {task.id}: {e}")
            return 40.0
    
    def _calculate_progress_score(self, task: Task) -> float:
        """Calculate score based on task progress (in-progress tasks get higher priority)."""
        status_str = str(task.status).lower()
        
        progress_scores = {
            'in_progress': 100.0,  # Highest priority to continue work
            'review': 80.0,  # High priority to finish review
            'testing': 70.0,  # High priority to complete testing
            'blocked': 0.0,  # Cannot work on blocked tasks
            'todo': 50.0,  # Medium priority for new work
            'done': 0.0,  # No priority for completed tasks
            'cancelled': 0.0  # No priority for cancelled tasks
        }
        
        return progress_scores.get(status_str, 50.0)
    
    def _get_priority_factors(self, task: Task, context_factors: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get detailed breakdown of priority factors for a task."""
        context_factors = context_factors or {}
        
        return {
            "base_priority": {
                "value": str(task.priority),
                "score": self._calculate_base_priority_score(task)
            },
            "urgency": {
                "due_date": task.due_date.isoformat() if hasattr(task, 'due_date') and task.due_date else None,
                "score": self._calculate_urgency_score(task)
            },
            "blocking_factor": {
                "dependent_tasks": context_factors.get('dependent_task_count', 0),
                "score": self._calculate_blocking_score(task, context_factors)
            },
            "age_factor": {
                "created_at": task.created_at.isoformat(),
                "score": self._calculate_age_score(task)
            },
            "progress_factor": {
                "status": str(task.status),
                "score": self._calculate_progress_score(task)
            }
        }
    
    def _generate_recommendation_reason(self, recommended_task: Dict[str, Any]) -> str:
        """Generate human-readable reason for task recommendation."""
        task = recommended_task["task"]
        score = recommended_task["priority_score"]
        
        reasons = []
        
        # Check main factors
        if score >= 80:
            reasons.append("high priority score")
        
        if hasattr(task, 'due_date') and task.due_date:
            days_until_due = (task.due_date - datetime.now(timezone.utc)).days
            if days_until_due <= 1:
                reasons.append("due soon" if days_until_due >= 0 else "overdue")
        
        if str(task.status).lower() == 'in_progress':
            reasons.append("already in progress")
        
        if str(task.priority).lower() in ['high', 'urgent', 'critical']:
            reasons.append(f"{str(task.priority).lower()} priority")
        
        if not reasons:
            reasons.append("best available option")
        
        return f"Recommended because: {', '.join(reasons)}"
    
    def _count_incomplete_dependencies(self, task: Task, all_tasks: List[Task]) -> int:
        """Count how many dependencies are incomplete."""
        if not hasattr(task, 'dependencies') or not task.dependencies:
            return 0
        
        incomplete_count = 0
        for dep_id in task.dependencies:
            dep_id_str = str(dep_id)
            for other_task in all_tasks:
                if str(other_task.id) == dep_id_str:
                    if not other_task.status.is_done() if hasattr(other_task.status, 'is_done') else str(other_task.status).lower() != 'done':
                        incomplete_count += 1
                    break
        
        return incomplete_count
    
    def _count_tasks_depending_on(self, task: Task, all_tasks: List[Task]) -> int:
        """Count how many tasks depend on this task."""
        dependent_count = 0
        task_id_str = str(task.id)
        
        for other_task in all_tasks:
            if hasattr(other_task, 'dependencies') and other_task.dependencies:
                for dep_id in other_task.dependencies:
                    if str(dep_id) == task_id_str:
                        dependent_count += 1
                        break
        
        return dependent_count