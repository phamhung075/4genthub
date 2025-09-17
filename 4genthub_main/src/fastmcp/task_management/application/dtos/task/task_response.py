"""Response DTO for task operations"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from .dependency_info import DependencyRelationships

@dataclass
class TaskResponse:
    """Response DTO for task operations following clean relationship chain"""
    id: str
    title: str
    description: str
    status: str
    priority: str
    details: str
    estimated_effort: str
    assignees: List[str]
    labels: List[str]
    dependencies: List[str]
    subtasks: List[Dict[str, Any]]
    due_date: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    git_branch_id: Optional[str] = None  # Links to git_branch which contains project and user info
    context_id: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None
    dependency_relationships: Optional[DependencyRelationships] = None  # Enhanced dependency information
    progress_percentage: int = 0  # Task completion progress (0-100)
    
    def __init__(
            self, 
            id: str, 
            title: str, 
            description: str, 
            status: str, 
            priority: str,                  
            details: str, 
            estimated_effort: str, 
            assignees: List[str], 
            labels: List[str],
            dependencies: List[str], 
            subtasks: List[Dict[str, Any]], 
            due_date: Optional[str],
            created_at: Optional[datetime], 
            updated_at: Optional[datetime], 
            git_branch_id: Optional[str] = None,  # Following clean relationship chain
            context_id: Optional[str] = None,
            context_data: Optional[Dict[str, Any]] = None,
            dependency_relationships: Optional[DependencyRelationships] = None,
            progress_percentage: int = 0 
        ):
        """Initialize TaskResponse following clean relationship chain with git_branch_id, context_id, and context_data"""
        self.id = id
        self.title = title
        self.description = description
        self.git_branch_id = git_branch_id
        self.status = status
        self.priority = priority
        self.details = details
        self.estimated_effort = estimated_effort
        self.assignees = assignees
        self.labels = labels
        self.dependencies = dependencies
        self.subtasks = subtasks
        self.due_date = due_date
        self.created_at = created_at
        self.updated_at = updated_at
        self.context_id = context_id
        self.context_data = context_data
        self.dependency_relationships = dependency_relationships
        self.progress_percentage = progress_percentage    
    @classmethod
    def from_domain(cls, task, context_data: Optional[Dict[str, Any]] = None, 
                   dependency_relationships: Optional[DependencyRelationships] = None) -> 'TaskResponse':
        """Create response DTO from domain entity with optional context data"""
        task_dict = task.to_dict()
        
        # Parse datetime strings back to datetime objects if they're strings
        created_at = task_dict["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        updated_at = task_dict["updated_at"]  
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        
        return cls(
            id=task_dict["id"],
            title=task_dict["title"],
            description=task_dict["description"],
            status=task_dict["status"],
            priority=task_dict["priority"],
            details=task_dict["details"],
            estimated_effort=task_dict["estimatedEffort"],
            assignees=task_dict["assignees"],
            labels=task_dict["labels"],
            dependencies=task_dict["dependencies"],
            subtasks=task_dict["subtasks"],
            due_date=task_dict["dueDate"],
            created_at=created_at,
            updated_at=updated_at,
            git_branch_id=task_dict.get("git_branch_id"),  # Following clean relationship chain
            context_id=task_dict.get("context_id"),
            context_data=context_data,
            dependency_relationships=dependency_relationships,
            progress_percentage=task_dict.get("progress_percentage", 0)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert TaskResponse to dictionary representation with JSON-safe datetime serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "details": self.details,
            "estimatedEffort": self.estimated_effort,
            "assignees": self.assignees,
            "labels": self.labels,
            "dependencies": self.dependencies,
            "subtasks": self.subtasks,
            "dueDate": self.due_date,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "git_branch_id": self.git_branch_id,
            "context_id": self.context_id,
            "context_data": self.context_data,
            "dependency_relationships": self.dependency_relationships.to_dict() if self.dependency_relationships else None,
            "progress_percentage": self.progress_percentage
        } 