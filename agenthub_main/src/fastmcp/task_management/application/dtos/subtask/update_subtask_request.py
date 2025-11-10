"""Request DTO for updating a subtask"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UpdateSubtaskRequest:
    task_id: str | int
    id: str | int
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assignees: list | None = None
    progress_percentage: int | None = None  # Progress tracking (0-100)
    progress_notes: str | None = None  # Progress notes to append to history

    def __init__(self, task_id: str, id: str, title: str = None, description: str = None,
                 status: str = None, priority: str = None, assignees: list = None,
                 progress_percentage: int = None, progress_notes: str = None):
        self.task_id = task_id
        self.id = id
        self.title = title
        self.description = description
        self.status = status
        self.priority = priority
        self.assignees = assignees
        self.progress_percentage = progress_percentage
        self.progress_notes = progress_notes 