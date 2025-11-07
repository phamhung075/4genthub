"""
API Response Wrappers
Standard response formats matching frontend api.types.ts
"""

from typing import Optional, List, Any
from pydantic import BaseModel

from .entities import TaskDTO, SubtaskDTO, ProjectDTO, BranchDTO
from .summaries import TaskSummaryDTO


class ApiResponse(BaseModel):
    """Base API response matching frontend ApiResponse<T> interface"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


class TaskResponse(BaseModel):
    """Task response matching frontend TaskResponse interface"""
    success: bool = True
    task: Optional[TaskDTO] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


class TasksResponse(BaseModel):
    """Tasks list response matching frontend TasksResponse interface"""
    success: bool = True
    tasks: List[TaskDTO]
    total: Optional[int] = None
    page: Optional[int] = None
    limit: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


class TaskSummariesResponse(BaseModel):
    """Task summaries list response for lightweight task lists"""
    success: bool = True
    tasks: List[TaskSummaryDTO]
    total: Optional[int] = None
    page: Optional[int] = None
    limit: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


class SubtaskResponse(BaseModel):
    """Subtask response matching frontend SubtaskResponse interface"""
    success: bool = True
    subtask: Optional[SubtaskDTO] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


class SubtasksResponse(BaseModel):
    """Subtasks list response matching frontend SubtasksResponse interface"""
    success: bool = True
    subtasks: List[SubtaskDTO]
    total: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


class ProjectResponse(BaseModel):
    """Project response matching frontend ProjectResponse interface"""
    success: bool = True
    project: Optional[ProjectDTO] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


class ProjectsResponse(BaseModel):
    """Projects list response matching frontend ProjectsResponse interface"""
    success: bool = True
    projects: List[ProjectDTO]
    total: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


class BranchResponse(BaseModel):
    """Branch response matching frontend BranchResponse interface"""
    success: bool = True
    branch: Optional[BranchDTO] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


class BranchesResponse(BaseModel):
    """Branches list response matching frontend BranchesResponse interface"""
    success: bool = True
    branches: List[BranchDTO]
    total: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


class ContextResponse(BaseModel):
    """Context response matching frontend ContextResponse interface"""
    success: bool = True
    context: Any
    level: Optional[str] = None
    inherited: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


class DeleteResponse(BaseModel):
    """Delete response matching frontend DeleteResponse interface"""
    success: bool = True
    deleted: Optional[bool] = None
    id: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response matching frontend HealthResponse interface"""
    success: bool = True
    status: str
    version: Optional[str] = None
    timestamp: str
    error: Optional[str] = None
    message: Optional[str] = None


class AgentsResponse(BaseModel):
    """Agents response matching frontend AgentsResponse interface"""
    success: bool = True
    agents: List[Any]
    total: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


class StatisticsResponse(BaseModel):
    """Statistics response for task/project metrics"""
    success: bool = True
    statistics: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


class CountResponse(BaseModel):
    """Count response for filtered queries"""
    success: bool = True
    count: Optional[int] = None
    filters: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


