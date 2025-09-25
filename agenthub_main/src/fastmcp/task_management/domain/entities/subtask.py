"""Subtask Domain Entity"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union

from ..value_objects.task_id import TaskId
from ..value_objects.subtask_id import SubtaskId
from ..value_objects.task_status import TaskStatus, TaskStatusEnum
from ..value_objects.priority import Priority
from ..enums.agent_roles import AgentRole, resolve_legacy_role
from ..events.task_events import TaskUpdated
from .base.base_timestamp_entity import BaseTimestampEntity


@dataclass
class Subtask(BaseTimestampEntity):
    """Subtask domain entity with business logic"""

    title: str = ""
    description: str = ""
    parent_task_id: Optional[TaskId] = None
    id: Optional[SubtaskId] = None
    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    assignees: List[str] = field(default_factory=list)
    progress_percentage: int = 0  # Progress tracking (0-100)
    
    # Domain events
    _events: List[Any] = field(default_factory=list, init=False)
    
    def _get_entity_id(self) -> str:
        """Get the unique identifier for this entity."""
        return str(self.id) if self.id else f"subtask_{id(self)}"

    def __post_init__(self):
        """Validate subtask data after initialization"""
        # Set default values if not provided before base validation
        if self.status is None:
            self.status = TaskStatus.todo()
        if self.priority is None:
            self.priority = Priority.medium()
        if self.assignees is None:
            self.assignees = []

        # Normalize assignees to ensure consistent @ prefix format
        if self.assignees:
            normalized_assignees = []
            for assignee in self.assignees:
                if assignee and assignee.strip():
                    # Try to resolve legacy role names
                    resolved_assignee = resolve_legacy_role(assignee)
                    if resolved_assignee:
                        # Ensure resolved assignee has @ prefix
                        if not resolved_assignee.startswith("@"):
                            resolved_assignee = f"@{resolved_assignee}"
                        normalized_assignees.append(resolved_assignee)
                    elif AgentRole.is_valid_role(assignee):
                        # Ensure valid agent role has @ prefix
                        if not assignee.startswith("@"):
                            assignee = f"@{assignee}"
                        normalized_assignees.append(assignee)
                    elif assignee.startswith("@"):
                        # Already has @ prefix, keep as is
                        normalized_assignees.append(assignee)
                    else:
                        # Keep original if not a valid role but not empty
                        normalized_assignees.append(assignee)
            self.assignees = normalized_assignees

        # Initialize timestamps through BaseTimestampEntity (runs _validate_entity)
        super().__post_init__()
    
    def __eq__(self, other):
        """Subtasks are equal if they have the same ID."""
        if not isinstance(other, Subtask):
            return False
        if self.id is None or other.id is None:
            return False
        return self.id == other.id
    
    def __hash__(self):
        """Hash based on subtask ID for use in sets and dictionaries"""
        return hash(self.id) if self.id else hash(self.title)
    
    # Properties for backward compatibility and convenience
    @property
    def is_completed(self) -> bool:
        """Check if subtask is completed"""
        return self.status.is_completed()
    
    @property
    def can_be_assigned(self) -> bool:
        """Check if subtask can be assigned (not completed or cancelled)"""
        return not self.is_completed and self.status.value != TaskStatusEnum.CANCELLED.value
    
    
    def _validate(self):
        """Validate subtask business rules"""
        if not self.title or not self.title.strip():
            raise ValueError("Subtask title cannot be empty")
        
        if len(self.title) > 200:
            raise ValueError("Subtask title cannot exceed 200 characters")
        
        if len(self.description) > 500:
            raise ValueError("Subtask description cannot exceed 500 characters")
        
        if self.parent_task_id is None:
            raise ValueError("Subtask must have a parent task ID")

    def _validate_entity(self) -> None:
        """Hook for BaseTimestampEntity validation."""
        self._validate()
    
    def update_status(self, new_status: TaskStatus) -> None:
        """Update subtask status with validation"""
        if not self.status.can_transition_to(new_status.value):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}")

        old_status = self.status
        self.status = new_status
        self.touch("status_changed")

        # Automatically set progress_percentage when status changes to done
        if new_status.value == TaskStatusEnum.DONE.value:
            self.progress_percentage = 100
        elif new_status.value == TaskStatusEnum.TODO.value:
            # Only reset to 0 if progress is currently 100 (was completed)
            if self.progress_percentage == 100:
                self.progress_percentage = 0

        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.parent_task_id,
            field_name="subtask_status",
            old_value=f"{self.id}:{old_status}",
            new_value=f"{self.id}:{new_status}",
            updated_at=self.updated_at
        ))
    
    def update_priority(self, new_priority: Priority) -> None:
        """Update subtask priority"""
        old_priority = self.priority
        self.priority = new_priority
        self.touch("priority_updated")

        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.parent_task_id,
            field_name="subtask_priority",
            old_value=f"{self.id}:{old_priority}",
            new_value=f"{self.id}:{new_priority}",
            updated_at=self.updated_at
        ))
    
    def update_title(self, title: str) -> None:
        """Update subtask title"""
        if not title.strip():
            raise ValueError("Subtask title cannot be empty")

        old_title = self.title
        self.title = title
        self.touch("title_updated")

        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.parent_task_id,
            field_name="subtask_title",
            old_value=f"{self.id}:{old_title}",
            new_value=f"{self.id}:{title}",
            updated_at=self.updated_at
        ))
    
    def update_description(self, description: str) -> None:
        """Update subtask description"""
        old_description = self.description
        self.description = description
        self.touch("description_updated")

        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.parent_task_id,
            field_name="subtask_description",
            old_value=f"{self.id}:{old_description}",
            new_value=f"{self.id}:{description}",
            updated_at=self.updated_at
        ))
    
    def update_assignees(self, assignees: List[str]) -> None:
        """Update subtask assignees"""
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
        
        old_assignees = self.assignees.copy()
        self.assignees = validated_assignees
        self.touch("assignees_updated")
        
        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.parent_task_id,
            field_name="subtask_assignees",
            old_value=f"{self.id}:{old_assignees}",
            new_value=f"{self.id}:{validated_assignees}",
            updated_at=self.updated_at
        ))
    
    def update_progress_percentage(self, progress_percentage: int) -> None:
        """Update subtask progress percentage"""
        if not isinstance(progress_percentage, int) or not (0 <= progress_percentage <= 100):
            raise ValueError(f"Progress percentage must be integer between 0-100, got: {progress_percentage}")
        
        old_progress = self.progress_percentage
        self.progress_percentage = progress_percentage
        self.touch("progress_updated")
        
        # Auto-update status based on progress percentage
        if progress_percentage == 0:
            self.status = TaskStatus.todo()
        elif progress_percentage == 100:
            self.status = TaskStatus.done()
        elif 1 <= progress_percentage <= 99:
            self.status = TaskStatus.in_progress()
        
        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.parent_task_id,
            field_name="subtask_progress",
            old_value=f"{self.id}:{old_progress}",
            new_value=f"{self.id}:{progress_percentage}",
            updated_at=self.updated_at
        ))
    
    def add_assignee(self, assignee: Union[str, AgentRole]) -> None:
        """Add an assignee to the subtask"""
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
        
        if validated_assignee not in self.assignees:
            self.assignees.append(validated_assignee)
            self.touch("assignee_added")
            
            # Raise domain event
            self._events.append(TaskUpdated(
                task_id=self.parent_task_id,
                field_name="subtask_assignees",
                old_value=f"{self.id}:assignee_added",
                new_value=f"{self.id}:{validated_assignee}",
                updated_at=self.updated_at
            ))
    
    def remove_assignee(self, assignee: Union[str, AgentRole]) -> None:
        """Remove an assignee from the subtask"""
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
                task_id=self.parent_task_id,
                field_name="subtask_assignees",
                old_value=f"{self.id}:assignee_removed",
                new_value=f"{self.id}:{assignee_str}",
                updated_at=self.updated_at
            ))
    
    def inherit_assignees_from_parent(self, parent_assignees: List[str]) -> None:
        """Inherit assignees from parent task if this subtask has no assignees.
        
        This method implements the inheritance logic where subtasks without
        assignees automatically inherit their parent task's assignees.
        
        Args:
            parent_assignees: List of assignees from the parent task
        """
        if not self.assignees and parent_assignees:
            # Only inherit if subtask has no assignees assigned
            old_assignees = self.assignees.copy()
            self.assignees = parent_assignees.copy()
            self.touch("assignees_inherited")
            
            # Raise domain event for inheritance
            self._events.append(TaskUpdated(
                task_id=self.parent_task_id,
                field_name="subtask_assignees",
                old_value=f"{self.id}:inherited_from_parent",
                new_value=f"{self.id}:{self.assignees}",
                updated_at=self.updated_at
            ))
    
    def has_assignees(self) -> bool:
        """Check if subtask has any assignees assigned.
        
        Returns:
            bool: True if subtask has assignees, False otherwise
        """
        return bool(self.assignees)
    
    def should_inherit_assignees(self) -> bool:
        """Check if subtask should inherit assignees from parent.
        
        Returns:
            bool: True if subtask should inherit (has no assignees), False otherwise
        """
        return not self.has_assignees()
    
    def complete(self) -> None:
        """Mark subtask as completed"""
        if self.is_completed:
            return
        
        old_status = self.status
        self.status = TaskStatus.done()
        self.progress_percentage = 100  # Automatically set progress to 100% when completed
        self.touch("subtask_completed")
        
        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.parent_task_id,
            field_name="subtask_status",
            old_value=f"{self.id}:{old_status}",
            new_value=f"{self.id}:{self.status}",
            updated_at=self.updated_at
        ))
    
    def reopen(self) -> None:
        """Reopen a completed subtask"""
        if not self.is_completed:
            return
        
        old_status = self.status
        self.status = TaskStatus.todo()
        self.touch("subtask_reopened")
        
        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.parent_task_id,
            field_name="subtask_status",
            old_value=f"{self.id}:{old_status}",
            new_value=f"{self.id}:{self.status}",
            updated_at=self.updated_at
        ))
    
    def get_events(self) -> List[Any]:
        """Get and clear domain events"""
        events = self._events.copy()
        self._events.clear()
        return events
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert subtask to dictionary representation"""
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
        
        return {
            "id": self.id.value if self.id else None,
            "title": self.title,
            "description": self.description,
            "parent_task_id": str(self.parent_task_id),
            "status": str(self.status),
            "priority": str(self.priority),
            "assignees": assignees_list,
            "progress_percentage": self.progress_percentage,  # Include progress percentage
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create(cls, id: SubtaskId, title: str, description: str, parent_task_id: TaskId,
               status: Optional[TaskStatus] = None, priority: Optional[Priority] = None,
               **kwargs) -> 'Subtask':
        """Factory method to create a new subtask"""
        if status is None:
            status = TaskStatus.todo()
        if priority is None:
            priority = Priority.medium()
        
        # Extract only valid parameters from kwargs
        valid_params = {}
        if 'assignees' in kwargs:
            valid_params['assignees'] = kwargs['assignees']
        if 'progress_percentage' in kwargs:
            valid_params['progress_percentage'] = kwargs['progress_percentage']
        if 'created_at' in kwargs:
            valid_params['created_at'] = kwargs['created_at']
        if 'updated_at' in kwargs:
            valid_params['updated_at'] = kwargs['updated_at']
        
        return cls(
            id=id,
            title=title,
            description=description,
            parent_task_id=parent_task_id,
            status=status,
            priority=priority,
            **valid_params
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], parent_task_id: TaskId) -> 'Subtask':
        """Create a subtask from dictionary data"""
        # Convert timestamps if present
        created_at = None
        updated_at = None
        
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at'])
        
        # Convert status and priority strings to objects
        status = TaskStatus.from_string(data.get('status', 'todo'))
        priority = Priority.from_string(data.get('priority', 'medium'))

        subtask_id = SubtaskId(data['id']) if data.get('id') else None
        
        return cls(
            id=subtask_id,
            title=data.get('title', ''),
            description=data.get('description', ''),
            parent_task_id=parent_task_id,
            status=status,
            priority=priority,
            assignees=data.get('assignees', []),
            progress_percentage=data.get('progress_percentage', 0),  # Include progress percentage
            created_at=created_at,
            updated_at=updated_at
        )
