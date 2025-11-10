"""Task Application Service (task operations only)"""

from __future__ import annotations

from typing import Any

from fastmcp.task_management.application.dtos.task import (
    CreateTaskRequest,
    CreateTaskResponse,
    ListTasksRequest,
    SearchTasksRequest,
    TaskListResponse,
    TaskResponse,
    UpdateTaskRequest,
    UpdateTaskResponse,
)
from fastmcp.task_management.application.use_cases.create_task import CreateTaskUseCase
from fastmcp.task_management.application.use_cases.delete_task import DeleteTaskUseCase
from fastmcp.task_management.application.use_cases.get_task import GetTaskUseCase
from fastmcp.task_management.application.use_cases.list_tasks import ListTasksUseCase
from fastmcp.task_management.application.use_cases.search_tasks import (
    SearchTasksUseCase,
)
from fastmcp.task_management.application.use_cases.update_task import UpdateTaskUseCase
from fastmcp.task_management.domain.exceptions.task_exceptions import TaskNotFoundError
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository

# Import delayed to avoid circular import


class TaskApplicationService:
    """Application service for task CRUD, search, and completion"""
    def __init__(self, task_repository: TaskRepository, context_service: Any | None = None, user_id: str | None = None):
        from .facade_service import FacadeService
        self._task_repository = task_repository
        self._user_id = user_id  # Store user context
        
        # Initialize hierarchical context service using FacadeService
        self._hierarchical_context_service = FacadeService.get_unified_context_facade(user_id=user_id)
        self._context_service = context_service
        
        # Get git_branch_repository for dependency injection
        git_branch_repo = self._get_git_branch_repository()

        # Initialize use cases with user context and git_branch_repository dependency injection
        self._create_task_use_case = CreateTaskUseCase(self._get_user_scoped_repository(), git_branch_repo)
        self._get_task_use_case = GetTaskUseCase(self._get_user_scoped_repository(), context_service, git_branch_repo)
        self._update_task_use_case = UpdateTaskUseCase(self._get_user_scoped_repository(), git_branch_repo)
        self._list_tasks_use_case = ListTasksUseCase(self._get_user_scoped_repository(), git_branch_repo)
        self._search_tasks_use_case = SearchTasksUseCase(self._get_user_scoped_repository())
        self._delete_task_use_case = DeleteTaskUseCase(self._get_user_scoped_repository())
        
        # Initialize complete task use case with delayed import to avoid circular import
        from fastmcp.task_management.application.use_cases.complete_task import (
            CompleteTaskUseCase,
        )
        self._complete_task_use_case = CompleteTaskUseCase(self._get_user_scoped_repository(), None, None)
    
    def _get_git_branch_repository(self):
        """Get git_branch_repository from RepositoryProviderService - single source of truth.

        FAIL FAST: Raises RepositoryProviderError if repository provider fails.
        This is critical infrastructure - project_id is REQUIRED by frontend contract.

        Raises:
            RepositoryProviderError: When repository provider fails or returns None
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            from ...application.services.repository_provider_service import (
                RepositoryProviderService,
            )
            from ..exceptions import RepositoryProviderError

            provider = RepositoryProviderService.get_instance()
            git_branch_repo = provider.get_git_branch_repository()

            if git_branch_repo is None:
                raise RepositoryProviderError("git_branch_repository is None - cannot lookup project_id")

            return git_branch_repo

        except RepositoryProviderError:
            # Re-raise our custom exception
            raise
        except Exception as e:
            # Log as ERROR (not warning) with full stack trace
            logger.error(
                f"CRITICAL: Failed to get git_branch_repository - cannot fetch project_id: {e}",
                exc_info=True  # Include stack trace for debugging
            )
            # Fail fast - raise custom exception
            from ..exceptions import RepositoryProviderError
            raise RepositoryProviderError(
                f"Cannot fetch project_id without git_branch_repository: {e}"
            ) from e

    def _get_user_scoped_repository(self) -> TaskRepository:
        """Get a user-scoped version of the repository if it supports user context."""
        # Debug: Check repository state
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"_get_user_scoped_repository: self._user_id={self._user_id}, "
                    f"repo has with_user={hasattr(self._task_repository, 'with_user')}, "
                    f"repo.user_id={getattr(self._task_repository, 'user_id', 'N/A')}")
        
        if hasattr(self._task_repository, 'with_user') and self._user_id:
            # Repository supports user scoping
            logger.debug(f"Creating user-scoped repository with user_id={self._user_id}")
            scoped_repo = self._task_repository.with_user(self._user_id)
            logger.debug(f"Scoped repo created with user_id={getattr(scoped_repo, 'user_id', 'N/A')}")
            return scoped_repo
        elif hasattr(self._task_repository, 'user_id'):
            # Repository has user_id property, set it if needed
            if self._user_id and self._task_repository.user_id != self._user_id:
                # Create new instance with user_id
                repo_class = type(self._task_repository)
                if hasattr(self._task_repository, 'session'):
                    return repo_class(self._task_repository.session, user_id=self._user_id)
        return self._task_repository
    
    def with_user(self, user_id: str) -> TaskApplicationService:
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
                      include_context: bool = False, user_id: str | None = None, 
                      project_id: str = "", git_branch_name: str = "main") -> TaskResponse | None:
        try:
            return await self._get_task_use_case.execute(
                task_id,
                generate_rules=generate_rules,
                force_full_generation=force_full_generation,
                include_context=include_context
            )
        except TaskNotFoundError:
            return None

    async def update_task(self, request: UpdateTaskRequest) -> UpdateTaskResponse:
        response = self._update_task_use_case.execute(request)
        if getattr(response, 'success', False) and hasattr(response, 'task') and response.task:
            task = response.task
            # Update task context in hierarchical system
            self._hierarchical_context_service.update_context(
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

    async def list_tasks(self, request: ListTasksRequest) -> TaskListResponse:
        return await self._list_tasks_use_case.execute(request)

    async def search_tasks(self, request: SearchTasksRequest) -> TaskListResponse:
        return await self._search_tasks_use_case.execute(request)

    async def delete_task(self, task_id: str, user_id: str, project_id: str = '', git_branch_name: str = 'main') -> bool:
        result = self._delete_task_use_case.execute(task_id)
        if result:
            # Delete task context from hierarchical system
            self._hierarchical_context_service.delete_context("task", task_id)
        return result

    async def complete_task(self, task_id: str, completion_summary: str = None, 
                          testing_notes: str = None, next_recommendations: str = None) -> dict:
        # CompleteTaskUseCase.execute is not async, so don't await it
        return self._complete_task_use_case.execute(
            task_id=task_id,
            completion_summary=completion_summary,
            testing_notes=testing_notes,
            next_recommendations=next_recommendations
        )

    async def get_all_tasks(self) -> TaskListResponse:
        request = ListTasksRequest()
        return await self.list_tasks(request)

    async def get_tasks_by_status(self, status: str) -> TaskListResponse:
        request = ListTasksRequest(status=status)
        return await self.list_tasks(request)

    async def get_tasks_by_assignee(self, assignee: str) -> TaskListResponse:
        request = ListTasksRequest(assignees=[assignee])
        return await self.list_tasks(request) 