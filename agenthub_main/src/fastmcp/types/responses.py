"""
API Response Wrappers
Standard response formats matching frontend api.types.ts
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from .entities import BranchDTO, ProjectDTO, SubtaskDTO, TaskDTO
from .summaries import TaskSummaryDTO


class ApiResponse(BaseModel):
    """Base API response matching frontend ApiResponse<T> interface"""
    success: bool
    data: Any | None = None
    error: str | None = None
    message: str | None = None
    timestamp: str | None = None


class TaskResponse(BaseModel):
    """Task response matching frontend TaskResponse interface"""
    success: bool = True
    task: TaskDTO | None = None
    error: str | None = None
    message: str | None = None
    timestamp: str | None = None


class TasksResponse(BaseModel):
    """Tasks list response matching frontend TasksResponse interface"""
    success: bool = True
    tasks: list[TaskDTO]
    total: int | None = None
    page: int | None = None
    limit: int | None = None
    error: str | None = None
    message: str | None = None
    timestamp: str | None = None


class TaskSummariesResponse(BaseModel):
    """Task summaries list response for lightweight task lists"""
    success: bool = True
    tasks: list[TaskSummaryDTO]
    total: int | None = None
    page: int | None = None
    limit: int | None = None
    error: str | None = None
    message: str | None = None
    timestamp: str | None = None


class SubtaskResponse(BaseModel):
    """Subtask response matching frontend SubtaskResponse interface"""
    success: bool = True
    subtask: SubtaskDTO | None = None
    error: str | None = None
    message: str | None = None
    timestamp: str | None = None


class SubtasksResponse(BaseModel):
    """Subtasks list response matching frontend SubtasksResponse interface"""
    success: bool = True
    subtasks: list[SubtaskDTO]
    total: int | None = None
    error: str | None = None
    message: str | None = None
    timestamp: str | None = None


class ProjectResponse(BaseModel):
    """Project response matching frontend ProjectResponse interface"""
    success: bool = True
    project: ProjectDTO | None = None
    error: str | None = None
    message: str | None = None
    timestamp: str | None = None


class ProjectsResponse(BaseModel):
    """Projects list response matching frontend ProjectsResponse interface"""
    success: bool = True
    projects: list[ProjectDTO]
    total: int | None = None
    error: str | None = None
    message: str | None = None
    timestamp: str | None = None


class BranchResponse(BaseModel):
    """Branch response matching frontend BranchResponse interface"""
    success: bool = True
    branch: BranchDTO | None = None
    error: str | None = None
    message: str | None = None
    timestamp: str | None = None


class BranchesResponse(BaseModel):
    """Branches list response matching frontend BranchesResponse interface"""
    success: bool = True
    branches: list[BranchDTO]
    total: int | None = None
    error: str | None = None
    message: str | None = None
    timestamp: str | None = None


class ContextResponse(BaseModel):
    """Context response matching frontend ContextResponse interface"""
    success: bool = True
    context: Any
    level: str | None = None
    inherited: Any | None = None
    error: str | None = None
    message: str | None = None
    timestamp: str | None = None


class DeleteResponse(BaseModel):
    """Delete response matching frontend DeleteResponse interface"""
    success: bool = True
    deleted: bool | None = None
    id: str | None = None
    error: str | None = None
    message: str | None = None
    timestamp: str | None = None


class HealthResponse(BaseModel):
    """Health check response matching frontend HealthResponse interface"""
    success: bool = True
    status: str
    version: str | None = None
    timestamp: str
    error: str | None = None
    message: str | None = None


class AgentsResponse(BaseModel):
    """Agents response matching frontend AgentsResponse interface"""
    success: bool = True
    agents: list[Any]
    total: int | None = None
    error: str | None = None
    message: str | None = None
    timestamp: str | None = None


class StatisticsResponse(BaseModel):
    """Statistics response for task/project metrics"""
    success: bool = True
    statistics: Any | None = None
    error: str | None = None
    message: str | None = None
    timestamp: str | None = None


class CountResponse(BaseModel):
    """Count response for filtered queries"""
    success: bool = True
    count: int | None = None
    filters: Any | None = None
    error: str | None = None
    message: str | None = None
    timestamp: str | None = None


