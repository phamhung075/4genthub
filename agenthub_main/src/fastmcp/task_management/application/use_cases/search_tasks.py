"""Search Tasks Use Case"""

from ...application.dtos.task import (
    SearchTasksRequest,
    TaskListResponse
)

from ...domain import TaskRepository


class SearchTasksUseCase:
    """Use case for searching tasks by query"""
    
    def __init__(self, task_repository: TaskRepository):
        self._task_repository = task_repository
    
    def execute(self, request: SearchTasksRequest) -> TaskListResponse:
        """Execute the search tasks use case"""
        # Search tasks in repository
        tasks = self._task_repository.search(request.query, limit=request.limit)
        
        # Convert to response DTO with query parameter
        return TaskListResponse.from_domain_list(tasks, query=request.query) 