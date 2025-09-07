"""Subtask Repository Interface"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from ..entities.subtask import Subtask
from ..value_objects.task_id import TaskId
from ..value_objects.subtask_id import SubtaskId


class SubtaskRepository(ABC):
    """Repository interface for Subtask aggregate"""
    
    @abstractmethod
    def save(self, subtask: Subtask) -> bool:
        """Save a subtask"""
        pass
    
    @abstractmethod
    def find_by_id(self, id: str) -> Optional[Subtask]:
        """Find a subtask by its id."""
        pass
    
    @abstractmethod
    def find_by_parent_task_id(self, parent_task_id: TaskId) -> List[Subtask]:
        """Find all subtasks for a parent task"""
        pass
    
    @abstractmethod
    def find_by_assignee(self, assignee: str) -> List[Subtask]:
        """Find subtasks by assignee"""
        pass
    
    @abstractmethod
    def find_by_status(self, status: str) -> List[Subtask]:
        """Find subtasks by status"""
        pass
    
    @abstractmethod
    def find_completed(self, parent_task_id: TaskId) -> List[Subtask]:
        """Find completed subtasks for a parent task"""
        pass
    
    @abstractmethod
    def find_pending(self, parent_task_id: TaskId) -> List[Subtask]:
        """Find pending subtasks for a parent task"""
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete a subtask by its id."""
        pass
    
    @abstractmethod
    def delete_by_parent_task_id(self, parent_task_id: TaskId) -> bool:
        """Delete all subtasks for a parent task"""
        pass
    
    @abstractmethod
    def exists(self, id: str) -> bool:
        """Check if a subtask exists by its id."""
        pass
    
    @abstractmethod
    def count_by_parent_task_id(self, parent_task_id: TaskId) -> int:
        """Count subtasks for a parent task"""
        pass
    
    @abstractmethod
    def count_completed_by_parent_task_id(self, parent_task_id: TaskId) -> int:
        """Count completed subtasks for a parent task"""
        pass
    
    @abstractmethod
    def get_next_id(self, parent_task_id: TaskId) -> SubtaskId:
        """Get next available subtask ID for a parent task"""
        pass
    
    @abstractmethod
    def get_subtask_progress(self, parent_task_id: TaskId) -> Dict[str, Any]:
        """Get subtask progress statistics for a parent task"""
        pass
    
    @abstractmethod
    def bulk_update_status(self, parent_task_id: TaskId, status: str) -> bool:
        """Update status of all subtasks for a parent task"""
        pass
    
    @abstractmethod
    def bulk_complete(self, parent_task_id: TaskId) -> bool:
        """Mark all subtasks as completed for a parent task"""
        pass
    
    @abstractmethod
    def remove_subtask(self, parent_task_id: str, subtask_id: str) -> bool:
        """Remove a subtask from a parent task by subtask ID."""
        pass