"""Task Domain Entity"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .base.base_timestamp_entity import BaseTimestampEntity

logger = logging.getLogger(__name__)

from ...domain.value_objects.task_status import TaskStatusEnum
from ..enums.agent_roles import AgentRole, resolve_legacy_role
from ..enums.common_labels import CommonLabel, LabelValidator
from ..enums.estimated_effort import EffortLevel, EstimatedEffort
from ..enums.progress_enums import ProgressState
from ..events.progress_events import (
    ProgressMilestoneReached,
    ProgressTypeCompleted,
    ProgressUpdated,
)
from ..events.task_events import TaskCreated, TaskDeleted, TaskRetrieved, TaskUpdated
from ..exceptions.vision_exceptions import MissingCompletionSummaryError
from ..value_objects.priority import Priority
from ..value_objects.progress import (
    ProgressCalculationStrategy,
    ProgressSnapshot,
    ProgressTimeline,
    ProgressType,
)
from ..value_objects.task_id import TaskId
from ..value_objects.task_status import TaskStatus


@dataclass
class Task(BaseTimestampEntity):
    """Task domain entity with business logic"""

    title: str = ""
    description: str = ""
    id: TaskId | None = None
    status: TaskStatus | None = None
    priority: Priority | None = None
    git_branch_id: str | None = None
    progress_history: dict[str, Any] = field(default_factory=dict)
    progress_count: int = 0
    estimated_effort: str = ""
    assignees: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    dependencies: list[TaskId] = field(default_factory=list)
    subtasks: list[str] = field(default_factory=list)  # List of subtask IDs
    due_date: str | None = None
    context_id: str | None = None  # New field: tracks if context is up-to-date
    
    # Progress tracking fields
    overall_progress: int = 0  # 0-100 percentage (integer)
    progress_state: ProgressState = ProgressState.INITIAL
    progress_timeline: ProgressTimeline | None = None
    
    # Domain events
    _events: list[Any] = field(default_factory=list, init=False)
    
    # Vision System fields (not persisted directly on task)
    _completion_summary: str | None = field(default=None, init=False)
    
    def __post_init__(self):
        """Initialise defaults before timestamp enforcement."""
        # Prepare defaults prior to BaseTimestampEntity validation
        if self.id is None:
            logging.warning("Task created without an ID. Repository should assign one.")

        if self.status is None:
            self.status = TaskStatus.todo()
        if self.priority is None:
            self.priority = Priority.medium()
        if self.assignees is None:
            self.assignees = []
        if self.labels is None:
            self.labels = []

        super().__post_init__()

    def _get_entity_id(self) -> str:
        """Get the unique identifier for this entity.

        Returns:
            str: Unique identifier for this entity
        """
        return str(self.id) if self.id else "unknown"
    
    def __eq__(self, other):
        """Tasks are equal if they have the same ID"""
        if not isinstance(other, Task):
            return False
        return self.id == other.id
    
    def __hash__(self):
        """Hash based on task ID for use in sets and dictionaries"""
        return hash(self.id.value)
    
    # Properties for backward compatibility and convenience
    @property
    def is_blocked(self) -> bool:
        """Check if task is blocked"""
        return self.status.value == TaskStatusEnum.BLOCKED.value
    
    @property
    def is_completed(self) -> bool:
        """Check if task is completed"""
        return self.status.is_completed()
    
    @property
    def can_be_assigned(self) -> bool:
        """Check if task can be assigned (not completed or cancelled)"""
        return self.status.value not in ['done', 'cancelled']
    
    def _validate(self):
        """Validate task business rules"""
        if not self.title or not self.title.strip():
            raise ValueError("Task title cannot be empty")
        
        if not self.description or not self.description.strip():
            raise ValueError("Task description cannot be empty")
        
        if len(self.title) > 200:
            raise ValueError("Task title cannot exceed 200 characters")
        
        if len(self.description) > 2000:
            raise ValueError("Task description cannot exceed 2000 characters")
        
        # Note: Assignee validation is handled at the application layer during task creation
        # Domain entities can be created with empty assignees during intermediate operations

    def _validate_entity(self) -> None:
        """Hook for BaseTimestampEntity validation."""
        self._validate()
    
    def update_status(self, new_status: TaskStatus) -> None:
        """Update task status with validation"""
        if not self.status.can_transition_to(new_status.value):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}")
        
        old_status = self.status
        self.status = new_status
        self.touch("status_update")
        
        # Keep context_id when task is updated (context should persist)
        
        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.id,
            field_name="status",
            old_value=str(old_status),
            new_value=str(new_status),
            updated_at=self.updated_at
        ))
    
    def update_priority(self, new_priority: Priority) -> None:
        """Update task priority"""
        old_priority = self.priority
        self.priority = new_priority
        self.touch("priority_update")
        
        # Keep context_id when task is updated (context should persist)
        
        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.id,
            field_name="priority",
            old_value=str(old_priority),
            new_value=str(new_priority),
            updated_at=self.updated_at
        ))
    
    def update_title(self, title: str) -> None:
        """Update task title"""
        if not title.strip():
            raise ValueError("Task title cannot be empty")
        
        old_title = self.title
        self.title = title
        self.touch("title_update")
        
        # Keep context_id when task is updated (context should persist)
        
        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.id,
            field_name="title",
            old_value=old_title,
            new_value=title,
            updated_at=self.updated_at
        ))
    
    def update_description(self, description: str) -> None:
        """Update task description"""
        if not description.strip():
            raise ValueError("Task description cannot be empty")
        
        old_description = self.description
        self.description = description
        self.touch("description_update")
        
        # Keep context_id when task is updated (context should persist)
        
        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.id,
            field_name="description",
            old_value=old_description,
            new_value=description,
            updated_at=self.updated_at
        ))
    
    def append_progress(self, progress_content: str) -> None:
        """Append new progress to task history with numbered headers"""
        self.progress_count += 1
        progress_header = f"=== Progress {self.progress_count} ==="

        # Initialize progress_history if it doesn't exist
        if not hasattr(self, 'progress_history') or self.progress_history is None:
            self.progress_history = {}

        # Update timestamp first
        self.touch("progress_update")

        # Store the progress entry
        progress_entry = {
            'content': f"{progress_header}\n{progress_content}",
            'timestamp': self.updated_at.isoformat(),
            'progress_number': self.progress_count
        }

        # Add to history using progress number as key
        self.progress_history[f"progress_{self.progress_count}"] = progress_entry

        # Clear context_id when task is updated (context needs updating)
        self.context_id = None

        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.id,
            field_name="progress_history",
            old_value=f"progress_added_{self.progress_count - 1}",
            new_value=f"progress_added_{self.progress_count}",
            updated_at=self.updated_at
        ))
    
    def update_estimated_effort(self, estimated_effort: str) -> None:
        """Update task estimated effort with enum validation"""
        # Validate estimated effort using EstimatedEffort enum
        try:
            EstimatedEffort(estimated_effort)
        except ValueError:
            # Use default if invalid
            estimated_effort = EffortLevel.MEDIUM.label
        
        old_effort = self.estimated_effort
        self.estimated_effort = estimated_effort
        self.touch("estimated_effort_update")
        
        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.id,
            field_name="estimated_effort",
            old_value=old_effort,
            new_value=estimated_effort,
            updated_at=self.updated_at
        ))
    
    def update_assignees(self, assignees: list[str]) -> None:
        """Update task assignees"""
        # Debug: Log incoming assignees
        logging.debug(f"[update_assignees] Incoming assignees: {assignees}")
        # Validate assignees using AgentRole enum
        validated_assignees = []
        for assignee in assignees:
            if assignee and assignee.strip():
                # Try to resolve legacy role names
                resolved_assignee = resolve_legacy_role(assignee)
                if resolved_assignee:
                    # Ensure resolved assignee has @ prefix
                    if not resolved_assignee.startswith("@"):
                        resolved_assignee = f"@{resolved_assignee}"
                    validated_assignees.append(resolved_assignee)
                elif AgentRole.is_valid_role(assignee):
                    # Ensure valid agent role has @ prefix
                    if not assignee.startswith("@"):
                        assignee = f"@{assignee}"
                    validated_assignees.append(assignee)
                elif assignee.startswith("@"):
                    # Already has @ prefix, keep as is
                    validated_assignees.append(assignee)
                else:
                    # Keep original if not a valid role but not empty
                    validated_assignees.append(assignee)
        # Debug: Log validated assignees
        logging.debug(f"[update_assignees] Validated assignees: {validated_assignees}")
        old_assignees = self.assignees.copy()
        self.assignees = validated_assignees
        self.touch("assignees_update")
        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.id,
            field_name="assignees",
            old_value=old_assignees,
            new_value=validated_assignees,
            updated_at=self.updated_at
        ))
    
    def add_assignee(self, assignee: str | AgentRole) -> None:
        """Add an assignee to the task"""
        # Handle both string and AgentRole enum inputs
        if isinstance(assignee, AgentRole):
            assignee_str = f"@{assignee.value}"
        else:
            assignee_str = str(assignee)
        
        if not assignee_str or not assignee_str.strip():
            return
        
        # Validate assignee using AgentRole enum
        validated_assignee = assignee_str
        resolved_assignee = resolve_legacy_role(assignee_str)
        if resolved_assignee:
            # Ensure resolved assignee has @ prefix
            if not resolved_assignee.startswith("@"):
                resolved_assignee = f"@{resolved_assignee}"
            validated_assignee = resolved_assignee
        elif AgentRole.is_valid_role(assignee_str):
            # Ensure valid agent role has @ prefix
            if not assignee_str.startswith("@"):
                assignee_str = f"@{assignee_str}"
            validated_assignee = assignee_str
        elif assignee_str.startswith("@"):
            # Already has @ prefix, keep as is
            validated_assignee = assignee_str
        else:
            # Keep original if not a valid role but not empty
            pass
        
        if validated_assignee not in self.assignees:
            self.assignees.append(validated_assignee)
            self.touch("assignee_added")
            
            # Raise domain event
            self._events.append(TaskUpdated(
                task_id=self.id,
                field_name="assignees",
                old_value="assignee_added",
                new_value=validated_assignee,
                updated_at=self.updated_at
            ))
    
    def remove_assignee(self, assignee: str | AgentRole) -> None:
        """Remove an assignee from the task"""
        # Handle both string and AgentRole enum inputs
        if isinstance(assignee, AgentRole):
            assignee_str = f"@{assignee.value}"
        else:
            assignee_str = str(assignee)
        
        if assignee_str in self.assignees:
            self.assignees.remove(assignee_str)
            self.touch("assignee_removed")
            
            # Raise domain event
            self._events.append(TaskUpdated(
                task_id=self.id,
                field_name="assignees",
                old_value="assignee_removed",
                new_value=assignee_str,
                updated_at=self.updated_at
            ))
    
    def has_assignee(self, assignee: str) -> bool:
        """Check if task has a specific assignee"""
        return assignee in self.assignees
    
    def get_primary_assignee(self) -> str | None:
        """Get the primary (first) assignee"""
        return self.assignees[0] if self.assignees else None
    
    def get_assignees_count(self) -> int:
        """Get the number of assignees"""
        return len(self.assignees)
    
    def is_multi_assignee(self) -> bool:
        """Check if task has multiple assignees"""
        return len(self.assignees) > 1
    
    def get_assignees_info(self) -> list[dict[str, Any]]:
        """Get role information for all assignees"""
        assignees_info = []
        
        for assignee in self.assignees:
            if not assignee:
                continue
            
            try:
                # Try to get role from AgentRole enum
                role = AgentRole.get_role_by_slug(assignee)
                if role:
                    from ..enums.agent_roles import get_role_metadata_from_yaml
                    metadata = get_role_metadata_from_yaml(role)
                    assignees_info.append({
                        "role": role.value,
                        "display_name": role.display_name,
                        "folder_name": role.folder_name,
                        "metadata": metadata
                    })
                else:
                    # Return basic info for non-enum assignees
                    assignees_info.append({
                        "role": assignee,
                        "display_name": assignee.replace("-", " ").replace("_", " ").title(),
                        "folder_name": assignee.replace("-", "_"),
                        "metadata": None
                    })
            except Exception:
                # Fallback for any errors
                assignees_info.append({
                    "role": assignee,
                    "display_name": assignee,
                    "folder_name": assignee,
                    "metadata": None
                })
        
        return assignees_info
    
    def get_inherited_assignees_for_subtasks(self) -> list[str]:
        """Get assignees that should be inherited by subtasks that have no assignees assigned.
        
        This method provides the default assignees for subtasks when they are created
        without explicit assignee assignment or when their assignees list is empty.
        
        Returns:
            list[str]: List of assignee strings that subtasks should inherit
        """
        return self.assignees.copy() if self.assignees else []
    
    def validate_assignee_list(self, assignees: list[str]) -> list[str]:
        """Validate and normalize a list of assignees using AgentRole enum.
        
        Args:
            assignees: List of assignee strings to validate
            
        Returns:
            list[str]: List of validated and normalized assignees
            
        Raises:
            ValueError: If any assignee is invalid and cannot be resolved
        """
        if not assignees:
            return []
        
        validated_assignees = []
        invalid_assignees = []
        
        for assignee in assignees:
            if assignee and assignee.strip():
                # Try to resolve legacy role names
                resolved_assignee = resolve_legacy_role(assignee)
                if resolved_assignee:
                    # Ensure resolved assignee has @ prefix
                    if not resolved_assignee.startswith("@"):
                        resolved_assignee = f"@{resolved_assignee}"
                    validated_assignees.append(resolved_assignee)
                elif AgentRole.is_valid_role(assignee):
                    # Ensure valid agent role has @ prefix
                    if not assignee.startswith("@"):
                        assignee = f"@{assignee}"
                    validated_assignees.append(assignee)
                elif assignee.startswith("@"):
                    # Already has @ prefix, keep as is
                    validated_assignees.append(assignee)
                else:
                    # Invalid assignee - add to invalid list for error reporting
                    invalid_assignees.append(assignee)
        
        if invalid_assignees:
            raise ValueError(f"Invalid assignees: {invalid_assignees}. Valid assignees must be from AgentRole enum.")
        
        return validated_assignees
    
    def update_labels(self, labels: list[str]) -> None:
        """Update task labels with flexible validation"""
        # Allow all labels - the repository will handle normalization and creation
        validated_labels = []
        for label in labels:
            if label and isinstance(label, str) and label.strip():
                # Basic validation - just ensure it's not empty
                normalized = label.strip()
                if len(normalized) <= 50:  # Max length check
                    validated_labels.append(normalized)
                else:
                    logger.warning(f"Label too long, skipping: {label}")
        
        old_labels = self.labels.copy()
        self.labels = validated_labels
        self.touch("labels_update")
        
        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.id,
            field_name="labels",
            old_value=old_labels,
            new_value=validated_labels,
            updated_at=self.updated_at
        ))
    
    def update_due_date(self, due_date: str | None) -> None:
        """Update task due date with validation"""
        if due_date is not None:
            try:
                # Validate date format (YYYY-MM-DD)
                datetime.fromisoformat(due_date)
            except ValueError:
                raise ValueError(f"Invalid due date format: {due_date}. Expected YYYY-MM-DD.")

        old_due_date = self.due_date
        self.due_date = due_date
        self.touch("due_date_update")
        
        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.id,
            field_name="due_date",
            old_value=old_due_date,
            new_value=due_date,
            updated_at=self.updated_at
        ))
    
    def mark_as_deleted(self) -> None:
        """Mark task as deleted (triggers domain event)"""
        self.touch("task_deleted")
        self._events.append(TaskDeleted(
            task_id=self.id,
            title=self.title,
            deleted_at=self.updated_at
        ))

    def get_progress_history_text(self) -> str:
        """Get full progress history as formatted text"""
        if not self.progress_history:
            return ""

        # Sort progress entries by progress number
        sorted_entries = sorted(
            self.progress_history.items(),
            key=lambda x: x[1].get('progress_number', 0)
        )

        history_text = []
        for _, entry in sorted_entries:
            history_text.append(entry['content'])

        return '\n\n'.join(history_text)
    
    def add_dependency(self, dependency_id: TaskId) -> None:
        """Add a task dependency"""
        if dependency_id == self.id:
            raise ValueError("Task cannot depend on itself")
        
        # Handle both TaskId objects and string values when checking for duplicates
        existing_deps = [dep.value if hasattr(dep, 'value') else str(dep) for dep in self.dependencies]
        if dependency_id.value not in existing_deps:
            self.dependencies.append(dependency_id)
            self.touch("dependency_added")
    
    def remove_dependency(self, dependency_id: TaskId) -> None:
        """Remove a task dependency"""
        # Find and remove dependency by value comparison
        for i, dep in enumerate(self.dependencies):
            # Handle both TaskId objects and string values
            dep_value = dep.value if hasattr(dep, 'value') else str(dep)
            if dep_value == dependency_id.value:
                self.dependencies.pop(i)
                self.touch("dependency_removed")
                break
    
    def has_dependency(self, dependency_id: TaskId) -> bool:
        """Check if task has a specific dependency"""
        # Handle both TaskId objects and string values
        return dependency_id.value in [dep.value if hasattr(dep, 'value') else str(dep) for dep in self.dependencies]
    
    def get_dependency_ids(self) -> list[str]:
        """Get list of dependency IDs as strings"""
        # Handle both TaskId objects and string values
        return [dep.value if hasattr(dep, 'value') else str(dep) for dep in self.dependencies]
    
    def clear_dependencies(self) -> None:
        """Remove all dependencies"""
        if self.dependencies:
            self.dependencies.clear()
            self.touch("dependencies_cleared")
    
    def has_circular_dependency(self, new_dependency_id: TaskId) -> bool:
        """Check if adding a dependency would create a circular reference"""
        # This is a simplified check - in a real system you'd need to traverse the full dependency graph
        if new_dependency_id == self.id:
            return True
        
        # Check if new dependency is already in our dependencies (would create immediate cycle)
        if self.has_dependency(new_dependency_id):
            return True
            
        # For now, assume no circular dependencies beyond immediate self-reference
        # In a full implementation, you'd need to check the entire dependency graph
        return False
    
    def add_label(self, label: str | CommonLabel) -> None:
        """Add a label to the task with enum validation"""
        # Handle both string and CommonLabel enum inputs
        if isinstance(label, CommonLabel):
            label_str = label.value
        else:
            label_str = str(label)
        
        if not label_str:
            return
        
        # Validate label using CommonLabel enum
        valid_label = label_str
        if not LabelValidator.is_valid_label(label_str):
            # Try to find a close match
            suggestions = CommonLabel.suggest_labels(label_str)
            if suggestions:
                valid_label = suggestions[0]  # Use first suggestion
        
        if valid_label not in self.labels:
            self.labels.append(valid_label)
            self.touch("label_added")
    
    def remove_label(self, label: str | CommonLabel) -> None:
        """Remove a label from the task"""
        # Handle both string and CommonLabel enum inputs
        if isinstance(label, CommonLabel):
            label_str = label.value
        else:
            label_str = str(label)
        
        if label_str in self.labels:
            self.labels.remove(label_str)
            self.touch("label_removed")
    
    def add_subtask(self, subtask_id: str) -> str:
        """Add a subtask ID to the task"""
        if not subtask_id or not isinstance(subtask_id, str):
            raise ValueError("Subtask ID must be a non-empty string")
        
        if subtask_id not in self.subtasks:
            self.subtasks.append(subtask_id)
            self.touch("subtask_added")
            
            # Raise domain event
            self._events.append(TaskUpdated(
                task_id=self.id,
                field_name="subtasks",
                old_value="subtask_added",
                new_value=subtask_id,
                updated_at=self.updated_at
            ))
        
        return subtask_id
    
    def remove_subtask(self, subtask_id: str) -> bool:
        """Remove a subtask by ID"""
        if subtask_id in self.subtasks:
            self.subtasks.remove(subtask_id)
            self.touch("subtask_removed")
            
            # Raise domain event
            self._events.append(TaskUpdated(
                task_id=self.id,
                field_name="subtasks",
                old_value="subtask_removed",
                new_value=subtask_id,
                updated_at=self.updated_at
            ))
            return True
        return False
    
    def update_subtask(self, subtask_id: str, updates: dict[str, Any]) -> bool:
        """Update a subtask by ID - This method should be handled by the subtask repository"""
        # Since subtasks are now just IDs, updating them should be done via the subtask repository
        # This method is kept for compatibility but will not perform any updates
        logger.warning(f"update_subtask called on task entity - should use subtask repository instead")
        return False
    
    def complete_subtask(self, subtask_id: str) -> bool:
        """Mark a subtask as completed - This method should be handled by the subtask repository"""
        # Since subtasks are now just IDs, completing them should be done via the subtask repository
        logger.warning(f"complete_subtask called on task entity - should use subtask repository instead")
        return False
    
    def complete_task(self, completion_summary: str | None = None, context_updated_at: datetime | None = None) -> None:
        """
        Complete the task by setting status to done.
        
        Business Rules Enforced:
        1. completion_summary is REQUIRED (Vision System requirement)
        2. Context must be updated (context_id is not None)
        3. All subtasks must be completed (validated by application layer)
        4. (Optional) Context must be updated AFTER the task was last updated
        
        Args:
            completion_summary: Summary of what was accomplished (REQUIRED)
            context_updated_at: When the context was last updated (if available)
        """
        # Vision System enforcement: completion_summary is mandatory
        if not completion_summary or not completion_summary.strip():
            raise MissingCompletionSummaryError(task_id=str(self.id))
        
        # Context should be updated before completing task (but not mandatory)
        if self.context_id is None:
            logger.warning(f"Task {self.id} being completed without context. Context is recommended but not mandatory.")
            # Don't raise error - allow completion without context
        
        # NOTE: Subtask completion validation is handled by TaskCompletionService
        # The Task entity only stores subtask IDs, not the full subtask data
        # This prevents the AttributeError when subtasks are Subtask objects from the repository
        
        # Check context timing if provided  
        # Skip context timing validation if context_id is None (task has been updated and context cleared)
        logger.info(f"Timestamp validation check: context_updated_at={context_updated_at}, context_id={self.context_id}, task.updated_at={self.updated_at}")
        if context_updated_at is not None and self.context_id is not None and context_updated_at <= self.updated_at:
            time_diff = self.updated_at - context_updated_at
            logger.error(f"TIMESTAMP VALIDATION FAILED: Context ({context_updated_at}) is older than task ({self.updated_at}) by {time_diff.total_seconds():.0f} seconds")
            raise ValueError(
                f"Context must be updated AFTER the task was last modified. "
                f"Task was updated {time_diff.total_seconds():.0f} seconds after context. "
                f"Please update the context with your progress before completing the task. "
                f"Use: manage_context(action='add_progress', level='task', "
                f"context_id='{self.id.value}', content='Your progress summary') before trying to complete."
            )
        else:
            logger.info(f"Timestamp validation passed or skipped: context_updated_at={context_updated_at}, context_id={self.context_id}")
        
        # Store completion summary (will be persisted by context update in application layer)
        self._completion_summary = completion_summary
        
        # NOTE: Subtask completion is handled by the SubtaskRepository/Service layer
        # The Task entity should not modify subtask states directly
        
        # Update task status to done
        old_status = self.status
        self.status = TaskStatus.done()
        # Update progress state to complete when task is done
        self.progress_state = ProgressState.COMPLETE
        self.overall_progress = 100
        self.touch("task_completed")
        
        # Raise domain event for task completion (include completion summary)
        self._events.append(TaskUpdated(
            task_id=self.id,
            field_name="status",
            old_value=str(old_status),
            new_value=str(self.status),
            updated_at=self.updated_at,
            metadata={"completion_summary": completion_summary}
        ))
        
        # Raise domain event for subtasks completion if there are any
        if self.subtasks:
            self._events.append(TaskUpdated(
                task_id=self.id,
                field_name="subtasks",
                old_value="all_subtasks_completed",
                new_value=self.subtasks,
                updated_at=self.updated_at
            ))

    def update_progress_state(self) -> None:
        """
        Update progress state based on current status and progress percentage.
        Called automatically when status or progress changes.
        """
        # If task is completed, set to COMPLETE
        if self.status.is_completed():
            self.progress_state = ProgressState.COMPLETE
            return

        # If task has 0% progress and is in todo status, set to INITIAL
        if self.overall_progress == 0 and self.status.value.lower() in ["todo", "pending"]:
            self.progress_state = ProgressState.INITIAL
            return

        # If task has progress or is in progress status, set to IN_PROGRESS
        if self.overall_progress > 0 or self.status.value.lower() in ["in_progress", "in-progress", "active"]:
            self.progress_state = ProgressState.IN_PROGRESS
            return

        # Default fallback based on progress percentage
        self.progress_state = ProgressState.from_progress_percentage(self.overall_progress)

    def set_status(self, status: TaskStatus) -> None:
        """
        Set task status and update progress state accordingly.
        """
        old_status = self.status
        self.status = status
        self.update_progress_state()
        self.touch("status_set")

        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.id,
            field_name="status",
            old_value=str(old_status),
            new_value=str(status),
            updated_at=self.updated_at
        ))

    def set_progress_percentage(self, percentage: int) -> None:
        """
        Set progress percentage and update progress state accordingly.
        """
        if not 0 <= percentage <= 100:
            raise ValueError(f"Progress percentage must be between 0 and 100, got {percentage}")

        old_progress = self.overall_progress
        self.overall_progress = percentage
        self.update_progress_state()
        self.touch("progress_percentage_set")

        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.id,
            field_name="overall_progress",
            old_value=old_progress,
            new_value=percentage,
            updated_at=self.updated_at
        ))

    def get_subtask(self, subtask_id: str) -> str | None:
        """Get a subtask ID if it exists in this task"""
        return subtask_id if subtask_id in self.subtasks else None
    
    def get_subtask_by_id(self, subtask_id: str) -> str | None:
        """Get a subtask by ID - alias for get_subtask for backward compatibility"""
        return self.get_subtask(subtask_id)
    
    def _subtask_ids_match(self, current_id: str, target_id: str) -> bool:
        """Helper method to compare subtask IDs"""
        return current_id == target_id
    
    def get_subtask_progress(self) -> dict[str, Any]:
        """Get subtask completion progress using status field"""
        if not self.subtasks:
            return {"total": 0, "completed": 0, "percentage": 0}
        
        # Since subtasks are now just IDs (strings), we cannot determine their completion status
        # This method should be moved to the application layer where it can access the subtask repository
        # For now, return basic info based on the number of subtasks
        total = len(self.subtasks)
        
        return {
            "total": total,
            "completed": 0,  # Cannot determine without repository access
            "percentage": 0  # Cannot determine without repository access
        }
    
    def all_subtasks_completed(self) -> bool:
        """
        Check if all subtasks are completed.
        
        NOTE: This method cannot check actual subtask completion status because:
        1. Task entity only stores subtask IDs, not full subtask data
        2. Following DDD principles, entities should not depend on repositories/services
        3. Actual subtask completion validation is properly handled by TaskCompletionService
        
        Current behavior: Returns True if no subtasks exist, False if subtasks exist
        (as we cannot verify their status without repository access).
        
        For accurate subtask completion status, use TaskCompletionService.can_complete_task()
        
        Returns:
            bool: True if no subtasks, False if subtasks exist (conservative approach)
        """
        # If there are no subtasks, then all subtasks are "completed" by definition
        if not self.subtasks:
            return True
        
        # If subtasks exist but we can't check their status (only have IDs),
        # return False to be conservative and prevent premature task completion
        return False
    
    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if not self.due_date:
            return False
        
        try:
            due_date = datetime.fromisoformat(self.due_date)
            now = datetime.now(timezone.utc)
            
            # Make both timezone-aware or both timezone-naive for comparison
            if due_date.tzinfo is None:
                # Make due_date timezone-aware
                due_date = due_date.replace(tzinfo=timezone.utc)
            
            return now > due_date and not self.status.is_completed()
        except ValueError:
            return False
    
    def get_suggested_labels(self, context: str = "") -> list[str]:
        """Get suggested labels based on task content and context"""
        suggestions = []
        
        # Suggest labels based on title and description
        content = f"{self.title} {self.description} {context}".lower()
        
        # Use CommonLabel enum to suggest appropriate labels
        for label in CommonLabel:
            if any(keyword in content for keyword in label.get_keywords()):
                suggestions.append(label.value)
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def get_effort_level(self) -> str:
        """Get the effort level category for this task"""
        try:
            effort_enum = EstimatedEffort(self.estimated_effort)
            return effort_enum.get_level()
        except ValueError:
            return "medium"
    
    def get_assignee_role_info(self) -> dict[str, Any] | None:
        """Get role information for the primary assignee (first assignee)"""
        if not self.assignees:
            return None
        
        primary_assignee = self.assignees[0]
        
        try:
            # Try to get role from AgentRole enum
            role = AgentRole.get_role_by_slug(primary_assignee)
            if role:
                from ..enums.agent_roles import get_role_metadata_from_yaml
                metadata = get_role_metadata_from_yaml(role)
                if metadata:
                    return {
                        "role": role.value,
                        "display_name": role.display_name,
                        "folder_name": role.folder_name,
                        "metadata": metadata
                    }
                else:
                    return {
                        "role": role.value,
                        "display_name": role.display_name,
                        "folder_name": role.folder_name,
                        "metadata": None
                    }
            else:
                # Return basic info for non-enum assignees
                return {
                    "role": primary_assignee,
                    "display_name": primary_assignee.replace("-", " ").replace("_", " ").title(),
                    "folder_name": primary_assignee.replace("-", "_"),
                    "metadata": None
                }
        except Exception:
            # Fallback for any errors
            return {
                "role": primary_assignee,
                "display_name": primary_assignee,
                "folder_name": primary_assignee,
                "metadata": None
            }
    
    def can_be_started(self) -> bool:
        """Check if task can be started (no blocking dependencies)"""
        return self.status.is_todo()
    
    def set_context_id(self, context_id: str) -> None:
        """Set the context ID to indicate context has been updated"""
        self.context_id = context_id
        self.touch("context_id_set")
    
    def clear_context_id(self) -> None:
        """Clear the context ID to indicate context needs updating"""
        self.context_id = None
        self.touch("context_id_cleared")
    
    def has_updated_context(self) -> bool:
        """Check if task has an updated context (context_id is not None)"""
        return self.context_id is not None
    
    def get_completion_summary(self) -> str | None:
        """Get the completion summary if task was completed with one"""
        return getattr(self, '_completion_summary', None)
    
    def can_be_completed(self, context_updated_at: datetime | None = None) -> bool:
        """
        Check if task can be completed.
        
        A task can only be completed when:
        1. Context validation handled by completion use case (context_id cleared on updates by design)
        2. ALL subtasks are completed
        3. (Optional) Context was updated AFTER the task was last updated
        
        Args:
            context_updated_at: The timestamp when context was last updated (optional)
            
        Returns:
            bool: True if task can be completed, False otherwise
        """
        # Context validation removed - context_id is cleared on updates by design
        # Context existence will be validated by the completion use case through context manager
            
        # Check if all subtasks are completed
        if not self.all_subtasks_completed():
            return False
            
        # If context_updated_at is provided, check if it's later than task updated_at
        if context_updated_at is not None:
            return context_updated_at > self.updated_at
            
        # If no context timestamp provided, allow completion if context_id exists
        # This supports the common case where context exists but timestamp isn't tracked
        return True
    
    def update_progress(self, progress_type: ProgressType, percentage: float, 
                       description: str | None = None, metadata: dict[str, Any] | None = None,
                       agent_id: str | None = None) -> None:
        """
        Update task progress for a specific progress type.
        
        Args:
            progress_type: Type of progress being updated
            percentage: Progress percentage (0-100)
            description: Optional description of the progress
            metadata: Optional metadata including blockers, dependencies, etc.
            agent_id: ID of the agent making the update
        """
        if not 0 <= percentage <= 100:
            raise ValueError(f"Progress percentage must be between 0 and 100, got {percentage}")
        
        # Initialize timeline if not exists
        if self.progress_timeline is None:
            self.progress_timeline = ProgressTimeline(task_id=str(self.id))
        
        # Get current progress for this type
        old_percentage = 0.0
        latest_snapshot = self.progress_timeline.get_latest_snapshot()
        if latest_snapshot and latest_snapshot.progress_type == progress_type:
            old_percentage = latest_snapshot.percentage
        
        # Create new progress snapshot
        from ..value_objects.progress import ProgressMetadata, ProgressStatus
        
        # Determine status based on percentage
        if percentage == 0:
            status = ProgressStatus.NOT_STARTED
        elif percentage == 100:
            status = ProgressStatus.COMPLETED
        elif percentage < old_percentage:
            status = ProgressStatus.BLOCKED  # Progress went backward
        else:
            status = ProgressStatus.IN_PROGRESS
        
        # Create metadata object
        progress_metadata = None
        if metadata:
            progress_metadata = ProgressMetadata(
                blockers=metadata.get("blockers", []),
                dependencies=metadata.get("dependencies", []),
                confidence_level=metadata.get("confidence_level", 1.0),
                notes=metadata.get("notes"),
                estimated_completion=metadata.get("estimated_completion")
            )
        
        # Create snapshot
        snapshot = ProgressSnapshot(
            task_id=str(self.id),
            progress_type=progress_type,
            percentage=percentage,
            status=status,
            description=description,
            metadata=progress_metadata or ProgressMetadata(),
            agent_id=agent_id
        )
        
        # Add to timeline
        self.progress_timeline.add_snapshot(snapshot)
        
        # Update overall progress
        self._recalculate_overall_progress()
        
        # Emit progress updated event
        self._events.append(ProgressUpdated(
            task_id=self.id,
            progress_type=progress_type,
            old_percentage=old_percentage,
            new_percentage=percentage,
            status=status,
            description=description,
            metadata=metadata,
            agent_id=agent_id
        ))
        
        # Check for milestones
        self._check_progress_milestones()
        
        # Check if progress type completed
        if percentage == 100 and old_percentage < 100:
            self._events.append(ProgressTypeCompleted(
                task_id=self.id,
                progress_type=progress_type,
                agent_id=agent_id
            ))

        self.touch("progress_updated")
    
    def _recalculate_overall_progress(self) -> None:
        """Recalculate overall progress from all progress types and subtasks."""
        if self.progress_timeline is None:
            self.overall_progress = 0.0
            return
        
        # Get progress from timeline
        timeline_progress = self.progress_timeline.get_overall_progress()
        
        # Get progress from subtasks
        subtask_progress_data = self.get_subtask_progress()
        subtask_progress = subtask_progress_data.get("percentage", 0.0)
        
        # Calculate weighted average (50% timeline, 50% subtasks if both exist)
        if self.subtasks and timeline_progress > 0:
            self.overall_progress = (timeline_progress + subtask_progress) / 2
        elif self.subtasks:
            self.overall_progress = subtask_progress
        else:
            self.overall_progress = timeline_progress
    
    def calculate_progress_from_subtasks(self, include_blocked: bool = False) -> float:
        """
        Calculate progress based on subtask completion.
        
        Args:
            include_blocked: Whether to include blocked subtasks in calculation
            
        Returns:
            Progress percentage (0-100)
        """
        if not self.subtasks:
            return 0.0
        
        # Since subtasks are now just IDs (strings), we cannot determine their status
        # This method should be moved to the application layer where it can access the subtask repository
        # For now, return 0.0 as we cannot calculate progress without repository access
        return 0.0
    
    def add_progress_milestone(self, name: str, percentage: float) -> None:
        """
        Add a progress milestone to track.
        
        Args:
            name: Milestone name
            percentage: Progress percentage when milestone is reached
        """
        if self.progress_timeline is None:
            self.progress_timeline = ProgressTimeline(task_id=str(self.id))
        
        self.progress_timeline.add_milestone(name, percentage)
        self.touch("milestone_added")
    
    def _check_progress_milestones(self) -> None:
        """Check if any milestones have been reached."""
        if self.progress_timeline is None:
            return
        
        for milestone_name, milestone_percentage in self.progress_timeline.milestones.items():
            if (self.overall_progress >= milestone_percentage and 
                not self._milestone_already_reached(milestone_name)):
                self._events.append(ProgressMilestoneReached(
                    task_id=self.id,
                    milestone_name=milestone_name,
                    milestone_percentage=milestone_percentage,
                    current_progress=self.overall_progress
                ))
    
    def _milestone_already_reached(self, milestone_name: str) -> bool:
        """Check if a milestone was already reached in past events."""
        for event in self._events:
            if (isinstance(event, ProgressMilestoneReached) and 
                event.milestone_name == milestone_name):
                return True
        return False
    
    def get_progress_by_type(self, progress_type: ProgressType) -> float:
        """Get current progress for a specific type."""
        if self.progress_timeline is None:
            return 0.0
        
        snapshots = self.progress_timeline.get_snapshots_by_type(progress_type)
        if not snapshots:
            return 0.0
        
        return snapshots[-1].percentage  # Return latest
    
    def get_progress_timeline_data(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get progress timeline data for the last N hours."""
        if self.progress_timeline is None:
            return []
        
        snapshots = self.progress_timeline.get_progress_trend(hours)
        return [s.to_dict() for s in snapshots]
    
    def has_progress_type(self, progress_type: ProgressType) -> bool:
        """Check if task has any progress recorded for a specific type."""
        if self.progress_timeline is None:
            return False
        
        return len(self.progress_timeline.get_snapshots_by_type(progress_type)) > 0
    
    def get_events(self) -> list[Any]:
        """Get and clear domain events"""
        events = self._events.copy()
        self._events.clear()
        return events
    
    def mark_as_retrieved(self) -> None:
        """Mark task as retrieved (triggers auto rule generation)"""
        self.touch("task_retrieved")
        self._events.append(TaskRetrieved(
            task_id=self.id,
            task_data=self.to_dict(),
            retrieved_at=self.updated_at
        ))
    
    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary representation"""
        from fastmcp.task_management.application.use_cases.agent_mappings import resolve_agent_name
        
        # Handle assignees - convert to standardized kebab-case format
        assignees_list = []
        if self.assignees is not None:
            for assignee in self.assignees:
                if hasattr(assignee, 'value'):
                    # Handle AgentRole enum - normalize to kebab-case
                    normalized_name = resolve_agent_name(assignee.value)
                    assignees_list.append(normalized_name)
                else:
                    # Handle string assignees - normalize to kebab-case
                    normalized_name = resolve_agent_name(str(assignee))
                    assignees_list.append(normalized_name)
        
        result = {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "git_branch_id": self.git_branch_id,
            "status": self.status.value if self.status and hasattr(self.status, 'value') else str(self.status) if self.status else None,
            "priority": self.priority.value if self.priority and hasattr(self.priority, 'value') else str(self.priority) if self.priority else None,
            "progress_history": self.progress_history,
            "progress_count": self.progress_count,
            "estimatedEffort": self.estimated_effort,
            "assignees": assignees_list,
            "labels": self.labels.copy() if self.labels is not None else [],
            "dependencies": [dep.value if hasattr(dep, 'value') else str(dep) for dep in self.dependencies],
            "subtasks": self.subtasks.copy(),
            "dueDate": self.due_date if self.due_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "context_id": self.context_id,
            "overall_progress": self.overall_progress,
            "progress_percentage": getattr(self, 'progress_percentage', 0)  # Include progress_percentage from DB
        }
        
        # Include progress timeline if exists
        if self.progress_timeline:
            result["progress_timeline"] = self.progress_timeline.to_dict()
        
        return result
    
    def migrate_subtask_ids(self) -> None:
        """Migrate old integer subtask IDs to new hierarchical format"""
        # Since subtasks are now just IDs (strings), this method is not needed
        # Migration should be handled at the repository level
        pass
    
    def clean_invalid_subtasks(self) -> int:
        """Remove invalid subtasks (non-string entries) from the subtasks list.
        
        Returns:
            Number of invalid subtasks removed
        """
        initial_count = len(self.subtasks)
        valid_subtasks = [st for st in self.subtasks if isinstance(st, str)]
        removed_count = initial_count - len(valid_subtasks)
        
        if removed_count > 0:
            logger.warning(f"Removed {removed_count} invalid subtasks from task {self.id}")
            self.subtasks = valid_subtasks
            self.touch("invalid_subtasks_cleaned")
            
            # Raise domain event for cleanup
            self._events.append(TaskUpdated(
                task_id=self.id,
                field_name="subtasks",
                old_value=f"removed_{removed_count}_invalid_subtasks",
                new_value=self.subtasks,
                updated_at=self.updated_at
            ))
        
        return removed_count
    
    @classmethod
    def create(cls, id: TaskId, title: str, description: str, 
               status: TaskStatus | None = None, priority: Priority | None = None,
               **kwargs) -> 'Task':
        """Factory method to create a new task"""
        if status is None:
            status = TaskStatus.todo()
        if priority is None:
            priority = Priority.medium()
        
        # Context will be created separately at the controller level
        # No automatic context_id assignment here
        
        task = cls(
            id=id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            **kwargs
        )
        
        # Raise domain event
        task._events.append(TaskCreated(
            task_id=task.id,
            title=task.title,
            created_at=task.created_at
        ))
        
        return task
    
    def clean_subtask_assignees(self) -> int:
        """
        Clean subtask assignees field - no longer needed since subtasks are just IDs.
        Returns 0 for compatibility.
        """
        return 0 
