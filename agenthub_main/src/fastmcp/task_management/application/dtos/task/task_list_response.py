"""Response DTO for task list operations"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from .task_response import TaskResponse

@dataclass
class TaskListResponse:
    """Response DTO for task list operations"""
    tasks: List[TaskResponse]
    count: int
    filters_applied: Optional[Dict[str, Any]] = None
    query: Optional[str] = None
    
    @classmethod
    def from_domain_list(cls, tasks, git_branch_repository=None, filters_applied: Optional[Dict[str, Any]] = None, query: Optional[str] = None) -> 'TaskListResponse':
        """Create response DTO from list of domain entities with project_id via repository join"""
        task_responses = [TaskResponse.from_domain(task, git_branch_repository=git_branch_repository) for task in tasks]
        return cls(
            tasks=task_responses,
            count=len(task_responses),
            filters_applied=filters_applied,
            query=query
        ) 