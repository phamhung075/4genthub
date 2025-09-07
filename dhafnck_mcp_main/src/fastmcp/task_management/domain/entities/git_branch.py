"""GitBranch Domain Entity"""

import uuid
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from .task import Task
from ..value_objects.task_id import TaskId
from ..value_objects.task_status import TaskStatus
from ..value_objects.priority import Priority


@dataclass
class GitBranch:
    """GitBranch entity representing a git branch with hierarchical task structure"""
    
    id: str
    name: str
    description: str
    project_id: str
    created_at: datetime
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Task hierarchy
    root_tasks: Dict[str, Task] = field(default_factory=dict)  # task_id -> Task
    all_tasks: Dict[str, Task] = field(default_factory=dict)   # Flattened view for quick lookup
    
    # Branch metadata
    assigned_agent_id: Optional[str] = None
    assigned_agents: List[str] = field(default_factory=list)  # Support multiple agents
    priority: Priority = field(default_factory=Priority.medium)  # Branch-level priority
    status: TaskStatus = field(default_factory=TaskStatus.todo)    # todo, in_progress, blocked, review, testing, done, cancelled, archived
    archived: bool = False  # Support for archiving branches
    
    @classmethod
    def create(cls, name: str, description: str, project_id: str) -> 'GitBranch':
        """Create a new GitBranch with a generated UUID"""
        now = datetime.now()
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            project_id=project_id,
            created_at=now,
            updated_at=now
        )
    
    def add_root_task(self, task: Task) -> None:
        """Add a root-level task to this branch"""
        self.root_tasks[task.id.value] = task
        self.all_tasks[task.id.value] = task
        self.updated_at = datetime.now()
    
    def add_child_task(self, parent_task_id: str, child_task: Task) -> None:
        """Add a child task under a parent task"""
        if parent_task_id in self.all_tasks:
            parent = self.all_tasks[parent_task_id]
            # Convert Task object to dictionary for add_subtask
            subtask_dict = {
                "id": child_task.id.value,
                "title": child_task.title,
                "description": child_task.description,
                "status": child_task.status.value if hasattr(child_task.status, 'value') else str(child_task.status),
                "priority": child_task.priority.value if hasattr(child_task.priority, 'value') else str(child_task.priority),
                "assignee": getattr(child_task, 'assignee', None),
                "estimated_effort": getattr(child_task, 'estimated_effort', None),
                "created_at": child_task.created_at.isoformat() if hasattr(child_task, 'created_at') else None,
                "updated_at": child_task.updated_at.isoformat() if hasattr(child_task, 'updated_at') else None
            }
            parent.add_subtask(subtask_dict)
            self.all_tasks[child_task.id.value] = child_task
            self.updated_at = datetime.now()
        else:
            raise ValueError(f"Parent task {parent_task_id} not found in branch")
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a task and all its children from the branch"""
        if task_id not in self.all_tasks:
            return False
        
        task = self.all_tasks[task_id]
        
        # Remove from root tasks if it's a root task
        if task_id in self.root_tasks:
            del self.root_tasks[task_id]
        
        # Remove from parent's children if it has a parent
        for potential_parent in self.all_tasks.values():
            if hasattr(potential_parent, 'subtasks') and task_id in potential_parent.subtasks:
                del potential_parent.subtasks[task_id]
        
        # Remove all children recursively
        children_to_remove = []
        if hasattr(task, 'subtasks'):
            children_to_remove = list(task.subtasks.keys())
        
        for child_id in children_to_remove:
            self.remove_task(child_id)
        
        # Remove the task itself
        del self.all_tasks[task_id]
        self.updated_at = datetime.now()
        return True
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self.all_tasks.get(task_id)
    
    def has_task(self, task_id: str) -> bool:
        """Check if a task exists in the branch"""
        return task_id in self.all_tasks
    
    def get_all_tasks(self) -> Dict[str, Task]:
        """Get all tasks in the branch"""
        return self.all_tasks.copy()
    
    def get_root_tasks(self) -> Dict[str, Task]:
        """Get all root-level tasks"""
        return self.root_tasks.copy()
    
    def get_task_count(self) -> int:
        """Get total number of tasks in the branch"""
        return len(self.all_tasks)
    
    def get_completed_task_count(self) -> int:
        """Get number of completed tasks"""
        def is_task_done(task):
            # Handle both Task entity and dict representation
            if hasattr(task, 'status'):
                return task.status == TaskStatus.done()
            elif isinstance(task, dict):
                return task.get('status') == 'done'
            else:
                return False
        
        return sum(1 for task in self.all_tasks.values() if is_task_done(task))
    
    def get_active_task_count(self) -> int:
        """Get number of active tasks (in_progress status)"""
        def is_task_active(task):
            # Handle both Task entity and dict representation
            if hasattr(task, 'status'):
                return task.status == TaskStatus.in_progress()
            elif isinstance(task, dict):
                return task.get('status') == 'in_progress'
            else:
                return False
        
        return sum(1 for task in self.all_tasks.values() if is_task_active(task))
    
    def get_progress_percentage(self) -> float:
        """Get completion percentage"""
        total = self.get_task_count()
        if total == 0:
            return 0.0
        completed = self.get_completed_task_count()
        return (completed / total) * 100.0
    
    def get_tree_status(self) -> Dict:
        """Get comprehensive tree status"""
        status_counts = {}
        priority_counts = {}
        
        for task in self.all_tasks.values():
            # Count by status
            status_key = task.status.value if hasattr(task.status, 'value') else str(task.status)
            status_counts[status_key] = status_counts.get(status_key, 0) + 1
            
            # Count by priority
            priority_key = task.priority.value if hasattr(task.priority, 'value') else str(task.priority)
            priority_counts[priority_key] = priority_counts.get(priority_key, 0) + 1
        
        return {
            "tree_name": self.name,
            "total_tasks": self.get_task_count(),
            "completed_tasks": self.get_completed_task_count(),
            "progress_percentage": self.get_progress_percentage(),
            "status_breakdown": status_counts,
            "priority_breakdown": priority_counts
        }
    
    def get_available_tasks(self) -> List[Task]:
        """Get tasks that are available for work"""
        available = []
        for task in self.all_tasks.values():
            if task.status != TaskStatus.done():
                available.append(task)
        return available
    
    def get_next_task(self) -> Optional[Task]:
        """Get the next highest priority task"""
        available_tasks = self.get_available_tasks()
        if not available_tasks:
            return None
        
        # Sort by priority (highest first)
        priority_order = {
            'critical': 5,
            'urgent': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }
        
        def get_priority_value(task):
            priority_str = task.priority.value if hasattr(task.priority, 'value') else str(task.priority)
            return priority_order.get(priority_str, 2)  # Default to medium
        
        available_tasks.sort(key=get_priority_value, reverse=True)
        return available_tasks[0]
    
    def update_status_based_on_tasks(self) -> None:
        """Update branch status based on task statuses"""
        if not self.all_tasks:
            self.status = TaskStatus.todo()
            return
        
        task_statuses = [task.status for task in self.all_tasks.values()]
        
        # If all tasks are done, mark branch as done
        if all(status == TaskStatus.done() for status in task_statuses):
            self.status = TaskStatus.done()
        # If any task is in progress, mark branch as in progress
        elif any(status == TaskStatus.in_progress() for status in task_statuses):
            self.status = TaskStatus.in_progress()
        # If any task is blocked, mark branch as blocked
        elif any(status == TaskStatus.blocked() for status in task_statuses):
            self.status = TaskStatus.blocked()
        # If any task is in review, mark branch as review
        elif any(status == TaskStatus.review() for status in task_statuses):
            self.status = TaskStatus.review()
        # If any task is testing, mark branch as testing
        elif any(status == TaskStatus.testing() for status in task_statuses):
            self.status = TaskStatus.testing()
        else:
            self.status = TaskStatus.todo()
        
        self.updated_at = datetime.now()
    
    def assign_agent(self, agent_id: str) -> None:
        """Assign an agent to this branch"""
        self.assigned_agent_id = agent_id
        self.updated_at = datetime.now()
    
    def unassign_agent(self) -> None:
        """Remove agent assignment from this branch"""
        self.assigned_agent_id = None
        self.updated_at = datetime.now()
    
    def is_assigned_to_agent(self, agent_id: str) -> bool:
        """Check if branch is assigned to specific agent"""
        return self.assigned_agent_id == agent_id
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'project_id': self.project_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'assigned_agent_id': self.assigned_agent_id,
            'assigned_agents': self.assigned_agents.copy(),  # Include assigned_agents list
            'priority': self.priority.value if hasattr(self.priority, 'value') else str(self.priority),
            'status': self.status.value if hasattr(self.status, 'value') else str(self.status),
            'archived': self.archived,
            'task_count': self.get_task_count(),
            'completed_task_count': self.get_completed_task_count(),
            'progress_percentage': self.get_progress_percentage()
        }
    
    def __repr__(self) -> str:
        return f"GitBranch(id='{self.id}', name='{self.name}', project_id='{self.project_id}', tasks={self.get_task_count()})"