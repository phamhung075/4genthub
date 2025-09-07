"""Subtask Application Service"""

from typing import Any, Dict, Optional

from ...application.dtos.subtask import (
    AddSubtaskRequest,
    UpdateSubtaskRequest,
    SubtaskResponse
)

from ...domain import TaskRepository
from ...domain.repositories.subtask_repository import SubtaskRepository
from ..use_cases.add_subtask import AddSubtaskUseCase
from ..use_cases.update_subtask import UpdateSubtaskUseCase
from ..use_cases.remove_subtask import RemoveSubtaskUseCase
from ..use_cases.complete_subtask import CompleteSubtaskUseCase
from ..use_cases.get_subtasks import GetSubtasksUseCase
from ..use_cases.get_subtask import GetSubtaskUseCase


class SubtaskApplicationService:
    """Application service for subtask operations with DDD support"""
    def __init__(self, task_repository: TaskRepository, subtask_repository: SubtaskRepository = None, user_id: Optional[str] = None):
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository
        self._user_id = user_id  # Store user context
        
        # Initialize use cases with user-scoped repositories
        self._add_subtask_use_case = AddSubtaskUseCase(
            self._get_user_scoped_repository(task_repository),
            self._get_user_scoped_repository(subtask_repository) if subtask_repository else None
        )
        self._update_subtask_use_case = UpdateSubtaskUseCase(
            self._get_user_scoped_repository(task_repository),
            self._get_user_scoped_repository(subtask_repository) if subtask_repository else None
        )
        self._remove_subtask_use_case = RemoveSubtaskUseCase(
            self._get_user_scoped_repository(task_repository),
            self._get_user_scoped_repository(subtask_repository) if subtask_repository else None
        )
        self._complete_subtask_use_case = CompleteSubtaskUseCase(
            self._get_user_scoped_repository(task_repository),
            self._get_user_scoped_repository(subtask_repository) if subtask_repository else None
        )
        self._get_subtasks_use_case = GetSubtasksUseCase(
            self._get_user_scoped_repository(task_repository),
            self._get_user_scoped_repository(subtask_repository) if subtask_repository else None
        )
        self._get_subtask_use_case = GetSubtaskUseCase(
            self._get_user_scoped_repository(task_repository),
            self._get_user_scoped_repository(subtask_repository) if subtask_repository else None
        )
    
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
    
    def with_user(self, user_id: str) -> 'SubtaskApplicationService':
        """Create a new service instance scoped to a specific user."""
        return SubtaskApplicationService(self._task_repository, self._subtask_repository, user_id)

    def add_subtask(self, request: AddSubtaskRequest) -> SubtaskResponse:
        return self._add_subtask_use_case.execute(request)

    def remove_subtask(self, task_id: str, id: str) -> Dict[str, Any]:
        return self._remove_subtask_use_case.execute(task_id, id)

    def update_subtask(self, request: UpdateSubtaskRequest) -> SubtaskResponse:
        return self._update_subtask_use_case.execute(request)

    def complete_subtask(self, task_id: str, id: str) -> Dict[str, Any]:
        return self._complete_subtask_use_case.execute(task_id, id)

    def get_subtasks(self, task_id: str) -> Dict[str, Any]:
        return self._get_subtasks_use_case.execute(task_id)

    def get_subtask(self, task_id: str, id: str) -> Dict[str, Any]:
        """Get a single subtask by ID"""
        return self._get_subtask_use_case.execute(task_id, id)

    def manage_subtasks(self, task_id: str, action: str, subtask_data: dict) -> dict:
        """Manage subtasks with enhanced DDD support"""
        if action in ["add_subtask", "add"]:
            # Handle both singular and plural assignee formats
            assignees = []
            if "assignees" in subtask_data:
                assignees = subtask_data["assignees"] if isinstance(subtask_data["assignees"], list) else [subtask_data["assignees"]]
            elif "assignee" in subtask_data and subtask_data["assignee"]:
                assignees = [subtask_data["assignee"]]
            
            request = AddSubtaskRequest(
                task_id=task_id,
                title=subtask_data.get("title", ""),
                description=subtask_data.get("description", ""),
                assignees=assignees
            )
            return self.add_subtask(request).__dict__
        elif action in ["complete_subtask", "complete"]:
            id = subtask_data.get("id")
            if id is None:
                raise ValueError("id is required for completing a subtask")
            return self.complete_subtask(task_id, id)
        elif action in ["update_subtask", "update"]:
            # Handle both singular and plural assignee formats
            assignees = None
            if "assignees" in subtask_data:
                assignees = subtask_data["assignees"] if isinstance(subtask_data["assignees"], list) else [subtask_data["assignees"]]
            elif "assignee" in subtask_data and subtask_data["assignee"]:
                assignees = [subtask_data["assignee"]]
            
            # Handle completed -> status mapping
            status = subtask_data.get("status")
            if "completed" in subtask_data and subtask_data["completed"]:
                status = "completed"
            
            request = UpdateSubtaskRequest(
                task_id=task_id,
                id=subtask_data.get("id"),
                title=subtask_data.get("title"),
                description=subtask_data.get("description"),
                status=status,
                assignees=assignees,
                priority=subtask_data.get("priority"),
                progress_percentage=subtask_data.get("progress_percentage")
            )
            return self.update_subtask(request).__dict__
        elif action in ["remove_subtask", "remove"]:
            id = subtask_data.get("id")
            if id is None:
                raise ValueError("id is required for removing a subtask")
            return self.remove_subtask(task_id, id)
        elif action in ["get_subtask", "get"]:
            id = subtask_data.get("id")
            if id is None:
                raise ValueError("id is required for getting a subtask")
            return self.get_subtask(task_id, id)
        elif action in ["list_subtasks", "list"]:
            return self.get_subtasks(task_id)
        else:
            raise ValueError(f"Unknown subtask action: {action}") 