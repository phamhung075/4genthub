"""Dependencie Application Service"""

from typing import Any, Dict, Optional, TYPE_CHECKING

from ...application.dtos.dependency import (
    AddDependencyRequest,
    DependencyResponse
)

from ...domain import TaskRepository

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ..use_cases import (
        AddDependencyUseCase,
        RemoveDependencyUseCase,
        GetDependenciesUseCase,
        ClearDependenciesUseCase,
        GetBlockingTasksUseCase
    )

class DependencieApplicationService:
    """Application service for dependency operations"""
    def __init__(self, task_repository: TaskRepository, user_id: Optional[str] = None):
        self._task_repository = task_repository
        self._user_id = user_id  # Store user context
        # Lazy initialization of use cases to avoid circular imports
        self._add_dependency_use_case = None
        self._remove_dependency_use_case = None
        self._get_dependencies_use_case = None
        self._clear_dependencies_use_case = None
        self._get_blocking_tasks_use_case = None

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

    def with_user(self, user_id: str) -> 'DependencieApplicationService':
        """Create a new service instance scoped to a specific user."""
        return DependencieApplicationService(self._task_repository, user_id)

    def add_dependency(self, request: AddDependencyRequest) -> DependencyResponse:
        if self._add_dependency_use_case is None:
            from ..use_cases.add_dependency import AddDependencyUseCase
            repo = self._get_user_scoped_repository(self._task_repository)
            self._add_dependency_use_case = AddDependencyUseCase(repo)
        return self._add_dependency_use_case.execute(request)

    def remove_dependency(self, task_id: str, dependency_id: str) -> DependencyResponse:
        if self._remove_dependency_use_case is None:
            from ..use_cases.remove_dependency import RemoveDependencyUseCase
            repo = self._get_user_scoped_repository(self._task_repository)
            self._remove_dependency_use_case = RemoveDependencyUseCase(repo)
        return self._remove_dependency_use_case.execute(task_id, dependency_id)

    def get_dependencies(self, task_id: str) -> Dict[str, Any]:
        if self._get_dependencies_use_case is None:
            from ..use_cases.get_dependencies import GetDependenciesUseCase
            repo = self._get_user_scoped_repository(self._task_repository)
            self._get_dependencies_use_case = GetDependenciesUseCase(repo)
        return self._get_dependencies_use_case.execute(task_id)

    def clear_dependencies(self, task_id: str) -> DependencyResponse:
        if self._clear_dependencies_use_case is None:
            from ..use_cases.clear_dependencies import ClearDependenciesUseCase
            repo = self._get_user_scoped_repository(self._task_repository)
            self._clear_dependencies_use_case = ClearDependenciesUseCase(repo)
        return self._clear_dependencies_use_case.execute(task_id)

    def get_blocking_tasks(self, task_id: str) -> Dict[str, Any]:
        if self._get_blocking_tasks_use_case is None:
            from ..use_cases.get_blocking_tasks import GetBlockingTasksUseCase
            repo = self._get_user_scoped_repository(self._task_repository)
            self._get_blocking_tasks_use_case = GetBlockingTasksUseCase(repo)
        return self._get_blocking_tasks_use_case.execute(task_id) 