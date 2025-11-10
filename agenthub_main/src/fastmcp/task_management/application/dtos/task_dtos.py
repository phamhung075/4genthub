"""Task Data Transfer Objects for Vision System Integration"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class CreateTaskDTO:
    """DTO for creating a new task"""
    title: str
    description: str
    git_branch_id: str | None = None
    status: str | None = None
    priority: str | None = None
    assignees: list[str] | None = None
    labels: list[str] | None = None
    due_date: str | None = None
    estimated_effort: str | None = None
    details: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API usage"""
        return {
            "title": self.title,
            "description": self.description,
            "git_branch_id": self.git_branch_id,
            "status": self.status,
            "priority": self.priority,
            "assignees": self.assignees or [],
            "labels": self.labels or [],
            "due_date": self.due_date,
            "estimated_effort": self.estimated_effort,
            "details": self.details or ""
        }

@dataclass
class UpdateTaskDTO:
    """DTO for updating an existing task"""
    task_id: str
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assignees: list[str] | None = None
    labels: list[str] | None = None
    due_date: str | None = None
    estimated_effort: str | None = None
    details: str | None = None
    context_id: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API usage"""
        result = {"task_id": self.task_id}
        
        if self.title is not None:
            result["title"] = self.title
        if self.description is not None:
            result["description"] = self.description
        if self.status is not None:
            result["status"] = self.status
        if self.priority is not None:
            result["priority"] = self.priority
        if self.assignees is not None:
            result["assignees"] = self.assignees
        if self.labels is not None:
            result["labels"] = self.labels
        if self.due_date is not None:
            result["due_date"] = self.due_date
        if self.estimated_effort is not None:
            result["estimated_effort"] = self.estimated_effort
        if self.details is not None:
            result["details"] = self.details
        if self.context_id is not None:
            result["context_id"] = self.context_id
            
        return result

@dataclass
class TaskResponseDTO:
    """DTO for task response"""
    success: bool
    task_id: str | None = None
    message: str | None = None
    task_data: dict[str, Any] | None = None
    errors: list[str] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API usage"""
        result = {"success": self.success}
        
        if self.task_id is not None:
            result["task_id"] = self.task_id
        if self.message is not None:
            result["message"] = self.message
        if self.task_data is not None:
            result["task_data"] = self.task_data
        if self.errors is not None:
            result["errors"] = self.errors
            
        return result

@dataclass
class CompleteTaskDTO:
    """DTO for completing a task"""
    task_id: str
    completion_summary: str
    context_updated_at: datetime | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API usage"""
        result = {
            "task_id": self.task_id,
            "completion_summary": self.completion_summary
        }
        
        if self.context_updated_at is not None:
            result["context_updated_at"] = self.context_updated_at.isoformat()
            
        return result