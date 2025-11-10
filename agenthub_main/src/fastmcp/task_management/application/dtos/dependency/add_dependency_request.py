"""Request DTO for adding a dependency between tasks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AddDependencyRequest:
    task_id: str | int
    depends_on_task_id: str | int
    dependency_type: str = "blocks"  # e.g., 'blocks', 'relates_to', etc. 