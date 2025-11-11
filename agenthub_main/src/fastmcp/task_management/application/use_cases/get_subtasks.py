"""Get Subtasks Use Case"""

from __future__ import annotations

from typing import Any

from ...domain import TaskId, TaskNotFoundError, TaskRepository
from ...domain.repositories.subtask_repository import SubtaskRepository


class GetSubtasksUseCase:
    def __init__(
        self,
        task_repository: TaskRepository,
        subtask_repository: SubtaskRepository = None,
    ):
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository

    def execute(self, task_id: str | int) -> dict[str, Any]:
        task_id_obj = self._convert_to_task_id(task_id)
        task = self._task_repository.find_by_id(task_id_obj)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")

        # Use dedicated subtask repository if available
        if self._subtask_repository:
            subtasks = self._subtask_repository.find_by_parent_task_id(task_id_obj)
            # Standalone subtask list response - include parent_task_id
            subtasks_data = [
                subtask.to_dict(include_parent_id=True) for subtask in subtasks
            ]

            # Calculate progress from subtask entities
            total_subtasks = len(subtasks)
            completed_subtasks = sum(1 for subtask in subtasks if subtask.is_completed)
            progress = {
                "total": total_subtasks,
                "completed": completed_subtasks,
                "percentage": (completed_subtasks / total_subtasks * 100)
                if total_subtasks > 0
                else 0,
            }
        else:
            # Fallback to existing task entity method for backward compatibility
            # Clean subtask assignees before returning
            task.clean_subtask_assignees()

            # Ensure each subtask has proper assignees field
            subtasks_data = []
            for subtask in task.subtasks:
                if isinstance(subtask, dict):
                    # Ensure assignees is always a list
                    if "assignees" not in subtask:
                        subtask["assignees"] = []
                    elif not isinstance(subtask["assignees"], list):
                        subtask["assignees"] = []
                    subtasks_data.append(subtask)

            progress = task.get_subtask_progress()

        return {
            "task_id": str(task_id),
            "subtasks": subtasks_data,
            "progress": progress,
        }

    def _convert_to_task_id(self, task_id: str | int) -> TaskId:
        if isinstance(task_id, int):
            return TaskId.from_int(task_id)
        else:
            return TaskId.from_string(str(task_id))
