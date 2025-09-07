"""Task Application Service (task operations only)"""

from typing import Optional, Any

from ...application.dtos.task import (
    CreateTaskRequest,
    CreateTaskResponse,
    TaskResponse,
    UpdateTaskRequest,
    ListTasksRequest,
    TaskListResponse,
    SearchTasksRequest
)
from ...domain.exceptions.task_exceptions import TaskNotFoundError
from ...domain.repositories.task_repository import TaskRepository
from ..use_cases.create_task import CreateTaskUseCase
from ..use_cases.get_task import GetTaskUseCase
from ..use_cases.update_task import UpdateTaskUseCase
from ..use_cases.list_tasks import ListTasksUseCase
from ..use_cases.search_tasks import SearchTasksUseCase
from ..use_cases.delete_task import DeleteTaskUseCase
from ..use_cases.complete_task import CompleteTaskUseCase


class TaskApplicationService:
    """Application service for task CRUD, search, and completion"""
    def __init__(self, task_repository: TaskRepository, context_service: Optional[Any] = None, user_id: Optional[str] = None):
        from ..factories.unified_context_facade_factory import UnifiedContextFacadeFactory
        from .unified_context_service import UnifiedContextService
        self._task_repository = task_repository
        self._user_id = user_id  # Store user context
        
        # Initialize hierarchical context service
        factory = UnifiedContextFacadeFactory()
        self._hierarchical_context_service = factory.create_unified_service()
        self._context_service = context_service
        
        # Initialize use cases with user context if repository supports it
        self._create_task_use_case = CreateTaskUseCase(self._get_user_scoped_repository())
        self._get_task_use_case = GetTaskUseCase(self._get_user_scoped_repository(), context_service)
        self._update_task_use_case = UpdateTaskUseCase(self._get_user_scoped_repository())
        self._list_tasks_use_case = ListTasksUseCase(self._get_user_scoped_repository())
        self._search_tasks_use_case = SearchTasksUseCase(self._get_user_scoped_repository())
        self._delete_task_use_case = DeleteTaskUseCase(self._get_user_scoped_repository())
        
        # Initialize task context repository for unified context system
        from ...infrastructure.repositories.task_context_repository import TaskContextRepository
        from ...infrastructure.database.database_config import get_db_config
        db_config = get_db_config()
        task_context_repository = TaskContextRepository(db_config.SessionLocal)
        
        # Pass task context repository to complete task use case
        # Note: subtask repository is not available here, so pass None
        self._complete_task_use_case = CompleteTaskUseCase(self._get_user_scoped_repository(), None, task_context_repository)
    
    def _get_user_scoped_repository(self) -> TaskRepository:
        """Get a user-scoped version of the repository if it supports user context."""
        if hasattr(self._task_repository, 'with_user') and self._user_id:
            # Repository supports user scoping
            return self._task_repository.with_user(self._user_id)
        elif hasattr(self._task_repository, 'user_id'):
            # Repository has user_id property, set it if needed
            if self._user_id and self._task_repository.user_id != self._user_id:
                # Create new instance with user_id
                repo_class = type(self._task_repository)
                if hasattr(self._task_repository, 'session'):
                    return repo_class(self._task_repository.session, user_id=self._user_id)
        return self._task_repository
    
    def with_user(self, user_id: str) -> 'TaskApplicationService':
        """Create a new service instance scoped to a specific user."""
        return TaskApplicationService(self._task_repository, self._context_service, user_id)

    async def create_task(self, request: CreateTaskRequest) -> CreateTaskResponse:
        response = self._create_task_use_case.execute(request)
        if getattr(response, 'success', False) and hasattr(response, 'task') and response.task:
            task = response.task
            # Create task context in hierarchical system
            self._hierarchical_context_service.create_context(
                level="task",
                context_id=str(task.id.value if hasattr(task.id, 'value') else task.id),
                data={
                    "task_data": {
                        "title": task.title,
                        "description": task.description,
                        "status": task.status.value if hasattr(task.status, 'value') else str(task.status),
                        "priority": task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
                        "assignees": task.assignees,
                        "labels": task.labels,
                        "estimated_effort": task.estimated_effort,
                        "due_date": task.due_date if task.due_date else None
                    }
                }
            )
        return response

    async def get_task(self, task_id: str, generate_rules: bool = True, force_full_generation: bool = False,
                      include_context: bool = False, user_id: Optional[str] = None, 
                      project_id: str = "", git_branch_name: str = "main") -> Optional[TaskResponse]:
        try:
            return await self._get_task_use_case.execute(
                task_id,
                generate_rules=generate_rules,
                force_full_generation=force_full_generation,
                include_context=include_context
            )
        except TaskNotFoundError:
            return None

    async def update_task(self, request: UpdateTaskRequest) -> Optional[TaskResponse]:
        response = self._update_task_use_case.execute(request)
        if getattr(response, 'success', False) and hasattr(response, 'task') and response.task:
            task = response.task
            # Update task context in hierarchical system
            self._hierarchical_context_service.update_context(
                level="task",
                context_id=str(task.id.value if hasattr(task.id, 'value') else task.id),
                changes={
                    "task_data": {
                        "title": task.title,
                        "description": task.description,
                        "status": task.status.value if hasattr(task.status, 'value') else str(task.status),
                        "priority": task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
                        "assignees": task.assignees,
                        "labels": task.labels,
                        "estimated_effort": task.estimated_effort,
                        "due_date": task.due_date if task.due_date else None
                    }
                }
            )
        return response

    async def list_tasks(self, request: ListTasksRequest) -> TaskListResponse:
        return await self._list_tasks_use_case.execute(request)

    async def search_tasks(self, request: SearchTasksRequest) -> TaskListResponse:
        return await self._search_tasks_use_case.execute(request)

    async def delete_task(self, task_id: str, user_id: str = 'default_id', project_id: str = '', git_branch_name: str = 'main') -> bool:
        result = self._delete_task_use_case.execute(task_id)
        if result:
            # Delete task context from hierarchical system
            self._hierarchical_context_service.delete_context("task", task_id)
        return result

    async def complete_task(self, task_id: str) -> dict:
        return await self._complete_task_use_case.execute(task_id)

    async def get_all_tasks(self) -> TaskListResponse:
        request = ListTasksRequest()
        return await self.list_tasks(request)

    async def get_tasks_by_status(self, status: str) -> TaskListResponse:
        request = ListTasksRequest(status=status)
        return await self.list_tasks(request)

    async def get_tasks_by_assignee(self, assignee: str) -> TaskListResponse:
        request = ListTasksRequest(assignees=[assignee])
        return await self.list_tasks(request) 