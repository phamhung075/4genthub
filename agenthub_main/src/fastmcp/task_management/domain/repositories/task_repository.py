"""Task Repository Interface"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..entities.task import Task
from ..value_objects import Priority, TaskId, TaskStatus


class TaskRepository(ABC):
    """Repository interface for Task aggregate"""
    
    @abstractmethod
    def save(self, task: Task) -> Task | None:
        """Save a task, returns the saved task on success or None on failure"""
        pass
    
    @abstractmethod
    def find_by_id(self, task_id: TaskId) -> Task | None:
        """Find task by ID"""
        pass
    
    @abstractmethod
    def find_all(self) -> list[Task]:
        """Find all tasks"""
        pass
    
    @abstractmethod
    def find_by_status(self, status: TaskStatus) -> list[Task]:
        """Find tasks by status"""
        pass
    
    @abstractmethod
    def find_by_priority(self, priority: Priority) -> list[Task]:
        """Find tasks by priority"""
        pass
    
    @abstractmethod
    def find_by_assignee(self, assignee: str) -> list[Task]:
        """Find tasks by assignee"""
        pass
    
    @abstractmethod
    def find_by_labels(self, labels: list[str]) -> list[Task]:
        """Find tasks containing any of the specified labels"""
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[Task]:
        """Search tasks by query string"""
        pass
    
    @abstractmethod
    def delete(self, task_id: TaskId) -> bool:
        """Delete a task"""
        pass
    
    @abstractmethod
    def exists(self, task_id: TaskId) -> bool:
        """Check if task exists"""
        pass
    
    @abstractmethod
    def get_next_id(self) -> TaskId:
        """Get next available task ID"""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """Get total number of tasks"""
        pass
    
    @abstractmethod
    def get_statistics(self) -> dict[str, Any]:
        """Get task statistics"""
        pass
    
    @abstractmethod
    def find_by_criteria(self, filters: dict[str, Any], limit: int | None = None) -> list[Task]:
        """Find tasks by multiple criteria"""
        pass
    
    @abstractmethod
    def find_by_id_all_states(self, task_id: TaskId) -> Task | None:
        """Find task by ID across all states (active, completed, archived)"""
        pass 