"""Task Progress Service - Domain Service for Task Progress Calculations"""

import logging
from typing import Dict, Any, List, Optional, Protocol
from decimal import Decimal, ROUND_HALF_UP

from ..entities.task import Task
from ..entities.subtask import Subtask
from ..value_objects.task_id import TaskId
from ..value_objects.task_status import TaskStatus

logger = logging.getLogger(__name__)


class SubtaskRepositoryProtocol(Protocol):
    """Protocol for subtask repository to avoid infrastructure dependency."""
    
    def find_by_parent_task_id(self, task_id: TaskId) -> List[Subtask]:
        """Find all subtasks for a given parent task."""
        pass


class TaskProgressService:
    """
    Domain service that handles all task progress calculations.
    
    This service centralizes progress calculation logic that was previously
    scattered across multiple use cases and entities.
    
    Responsibilities:
    - Calculate task completion percentages
    - Aggregate subtask progress into parent task progress
    - Determine if tasks can be completed based on progress rules
    - Generate progress summaries and reports
    """
    
    def __init__(self, subtask_repository: Optional[SubtaskRepositoryProtocol] = None):
        """
        Initialize the task progress service.
        
        Args:
            subtask_repository: Repository for accessing subtask data (optional for compatibility)
        """
        self._subtask_repository = subtask_repository
    
    def calculate_task_progress(self, task: Task) -> Dict[str, Any]:
        """
        Calculate comprehensive progress information for a task.
        
        Args:
            task: The task to calculate progress for
            
        Returns:
            Dictionary containing all progress metrics
        """
        try:
            # Base task progress
            base_progress = self._calculate_base_task_progress(task)
            
            # Subtask progress (if subtask repository is available)
            subtask_progress = self._calculate_subtask_progress(task) if self._subtask_repository else None
            
            # Overall progress combining base task and subtasks
            overall_progress = self._calculate_overall_progress(base_progress, subtask_progress)
            
            return {
                "task_id": str(task.id),
                "base_progress": base_progress,
                "subtask_progress": subtask_progress,
                "overall_progress": overall_progress,
                "can_complete": self._can_complete_based_on_progress(overall_progress, subtask_progress),
                "blocking_factors": self._identify_blocking_factors(task, subtask_progress)
            }
            
        except Exception as e:
            logger.error(f"Error calculating progress for task {task.id}: {e}")
            return self._create_error_progress_response(task, str(e))
    
    def calculate_subtask_completion_percentage(self, task: Task) -> float:
        """
        Calculate the percentage of completed subtasks for a task.
        
        Args:
            task: The parent task
            
        Returns:
            Completion percentage as float (0.0 to 100.0)
        """
        if not self._subtask_repository:
            return 100.0  # No subtasks = 100% complete
        
        try:
            subtasks = self._subtask_repository.find_by_parent_task_id(task.id)
            
            if not subtasks:
                return 100.0  # No subtasks = 100% complete
            
            completed_count = sum(1 for subtask in subtasks if subtask.is_completed)
            total_count = len(subtasks)
            
            if total_count == 0:
                return 100.0
            
            # Use Decimal for precise calculation
            percentage = Decimal(completed_count) / Decimal(total_count) * Decimal('100')
            return float(percentage.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))
            
        except Exception as e:
            logger.error(f"Error calculating subtask completion percentage for task {task.id}: {e}")
            return 0.0
    
    def get_subtask_summary(self, task: Task) -> Dict[str, Any]:
        """
        Get a comprehensive summary of subtask completion status.
        
        Args:
            task: The parent task
            
        Returns:
            Dictionary with detailed subtask statistics
        """
        if not self._subtask_repository:
            return {
                "total": 0,
                "completed": 0,
                "incomplete": 0,
                "completion_percentage": 100.0,
                "can_complete_parent": True,
                "details": []
            }
        
        try:
            subtasks = self._subtask_repository.find_by_parent_task_id(task.id)
            
            if not subtasks:
                return {
                    "total": 0,
                    "completed": 0,
                    "incomplete": 0,
                    "completion_percentage": 100.0,
                    "can_complete_parent": True,
                    "details": []
                }
            
            completed_subtasks = [s for s in subtasks if s.is_completed]
            incomplete_subtasks = [s for s in subtasks if not s.is_completed]
            
            total = len(subtasks)
            completed = len(completed_subtasks)
            incomplete = len(incomplete_subtasks)
            
            completion_percentage = self.calculate_subtask_completion_percentage(task)
            
            # Create detailed breakdown
            details = []
            for subtask in subtasks:
                details.append({
                    "id": str(subtask.id),
                    "title": subtask.title,
                    "status": "completed" if subtask.is_completed else "incomplete",
                    "progress_percentage": getattr(subtask, 'progress_percentage', 0 if not subtask.is_completed else 100)
                })
            
            return {
                "total": total,
                "completed": completed,
                "incomplete": incomplete,
                "completion_percentage": completion_percentage,
                "can_complete_parent": incomplete == 0,
                "details": details,
                "incomplete_titles": [s.title for s in incomplete_subtasks[:5]],  # First 5 for UI display
                "completed_titles": [s.title for s in completed_subtasks[:5]]  # First 5 for UI display
            }
            
        except Exception as e:
            logger.error(f"Error getting subtask summary for task {task.id}: {e}")
            return {
                "total": 0,
                "completed": 0,
                "incomplete": 0,
                "completion_percentage": 0.0,
                "can_complete_parent": False,
                "details": [],
                "error": str(e)
            }
    
    def calculate_progress_score(self, task: Task) -> float:
        """
        Calculate a weighted progress score for task prioritization.
        
        Args:
            task: The task to score
            
        Returns:
            Progress score (0.0 to 1.0)
        """
        try:
            # Base task status contributes 60% to score
            status_score = self._get_status_progress_value(task.status)
            
            # Subtask completion contributes 40% to score
            subtask_percentage = self.calculate_subtask_completion_percentage(task)
            subtask_score = subtask_percentage / 100.0
            
            # Weighted combination
            overall_score = (status_score * 0.6) + (subtask_score * 0.4)
            
            # Clamp to [0.0, 1.0]
            return max(0.0, min(1.0, overall_score))
            
        except Exception as e:
            logger.error(f"Error calculating progress score for task {task.id}: {e}")
            return 0.0
    
    def _calculate_base_task_progress(self, task: Task) -> Dict[str, Any]:
        """Calculate progress based on task status alone."""
        status_value = self._get_status_progress_value(task.status)
        
        return {
            "status": str(task.status),
            "progress_percentage": status_value * 100,
            "is_completed": task.status.is_done() if hasattr(task.status, 'is_done') else False,
            "is_in_progress": self._is_status_in_progress(task.status),
            "is_blocked": self._is_status_blocked(task.status)
        }
    
    def _calculate_subtask_progress(self, task: Task) -> Optional[Dict[str, Any]]:
        """Calculate progress based on subtasks."""
        if not self._subtask_repository:
            return None
        
        return self.get_subtask_summary(task)
    
    def _calculate_overall_progress(self, base_progress: Dict[str, Any], subtask_progress: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine base task and subtask progress into overall progress."""
        base_percentage = base_progress["progress_percentage"]
        
        if subtask_progress is None or subtask_progress["total"] == 0:
            # No subtasks, use base task progress
            return {
                "percentage": base_percentage,
                "weighted_percentage": base_percentage,
                "calculation_method": "task_status_only"
            }
        
        # Combine task status (60%) and subtask completion (40%)
        subtask_percentage = subtask_progress["completion_percentage"]
        weighted_percentage = (base_percentage * 0.6) + (subtask_percentage * 0.4)
        
        return {
            "percentage": weighted_percentage,
            "weighted_percentage": weighted_percentage,
            "base_contribution": base_percentage,
            "subtask_contribution": subtask_percentage,
            "calculation_method": "weighted_combination"
        }
    
    def _can_complete_based_on_progress(self, overall_progress: Dict[str, Any], subtask_progress: Optional[Dict[str, Any]]) -> bool:
        """Determine if task can be completed based on progress rules."""
        # Rule 1: If there are subtasks, all must be completed
        if subtask_progress and subtask_progress["total"] > 0:
            return subtask_progress["incomplete"] == 0
        
        # Rule 2: Task can be completed if progress is sufficient (configurable threshold)
        return overall_progress["percentage"] >= 0.0  # Allow completion at any progress level for now
    
    def _identify_blocking_factors(self, task: Task, subtask_progress: Optional[Dict[str, Any]]) -> List[str]:
        """Identify factors that prevent task completion."""
        blocking_factors = []
        
        # Check subtask blocking factors
        if subtask_progress and subtask_progress["incomplete"] > 0:
            incomplete_count = subtask_progress["incomplete"]
            total_count = subtask_progress["total"]
            blocking_factors.append(f"{incomplete_count} of {total_count} subtasks incomplete")
        
        # Check task status blocking factors
        if self._is_status_blocked(task.status):
            blocking_factors.append("Task status is blocked")
        
        # Check for missing dependencies (if task has dependency information)
        if hasattr(task, 'dependencies') and task.dependencies:
            # This would require a dependency service to check, which we'll implement next
            blocking_factors.append("Dependencies may not be satisfied")
        
        return blocking_factors
    
    def _get_status_progress_value(self, status: TaskStatus) -> float:
        """Convert task status to progress value (0.0 to 1.0)."""
        status_str = str(status).lower()
        
        progress_map = {
            'todo': 0.0,
            'in_progress': 0.5,
            'review': 0.8,
            'testing': 0.9,
            'done': 1.0,
            'blocked': 0.0,
            'cancelled': 0.0
        }
        
        return progress_map.get(status_str, 0.0)
    
    def _is_status_in_progress(self, status: TaskStatus) -> bool:
        """Check if status indicates task is in progress."""
        status_str = str(status).lower()
        return status_str in ['in_progress', 'review', 'testing']
    
    def _is_status_blocked(self, status: TaskStatus) -> bool:
        """Check if status indicates task is blocked."""
        status_str = str(status).lower()
        return status_str == 'blocked'
    
    def _create_error_progress_response(self, task: Task, error_msg: str) -> Dict[str, Any]:
        """Create error response for progress calculation failures."""
        return {
            "task_id": str(task.id),
            "base_progress": {
                "status": str(task.status),
                "progress_percentage": 0,
                "is_completed": False,
                "is_in_progress": False,
                "is_blocked": True
            },
            "subtask_progress": None,
            "overall_progress": {
                "percentage": 0,
                "weighted_percentage": 0,
                "calculation_method": "error"
            },
            "can_complete": False,
            "blocking_factors": [f"Calculation error: {error_msg}"],
            "error": error_msg
        }