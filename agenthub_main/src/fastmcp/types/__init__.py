"""
API Response Models (DTOs)
Pydantic models that match frontend TypeScript interfaces for type-safe API contracts

Organized by category:
- entities: Core domain objects (Task, Subtask, Project, Branch, Rule)
- summaries: Lightweight objects for list views
- responses: API response wrappers
- bulk: Bulk operation models
- converters: Domain entity to DTO conversion helpers
"""

# Import submodules for module-level access
from . import entities, responses, summaries, converters

# Entity DTOs
from .entities import (
    TaskDTO,
    SubtaskDTO,
    ProjectDTO,
    BranchDTO,
    RuleDTO,
)

# Summary DTOs
from .summaries import (
    TaskSummaryDTO,
    SubtaskSummaryDTO,
    BranchSummaryDTO,
    ProjectSummaryDTO,
)

# Response wrappers
from .responses import (
    ApiResponse,
    TaskResponse,
    TasksResponse,
    TaskSummariesResponse,
    SubtaskResponse,
    SubtasksResponse,
    ProjectResponse,
    ProjectsResponse,
    BranchResponse,
    BranchesResponse,
    ContextResponse,
    DeleteResponse,
    HealthResponse,
    AgentsResponse,
    StatisticsResponse,
    CountResponse,
)

# Bulk operations
from .bulk import (
    BulkSummaryRequest,
    BulkSummaryResponse,
    BulkSummaryMetadata,
)

# Conversion helpers
from .converters import (
    task_to_dto,
    subtask_to_dto,
    task_summary_to_dto,
    subtask_summary_to_dto,
)

__all__ = [
    # Submodules
    "entities",
    "responses",
    "summaries",
    "converters",
    # Entity DTOs
    "TaskDTO",
    "SubtaskDTO",
    "ProjectDTO",
    "BranchDTO",
    "RuleDTO",
    # Summary DTOs
    "TaskSummaryDTO",
    "SubtaskSummaryDTO",
    "BranchSummaryDTO",
    "ProjectSummaryDTO",
    # API Response Wrappers
    "ApiResponse",
    "TaskResponse",
    "TasksResponse",
    "TaskSummariesResponse",
    "SubtaskResponse",
    "SubtasksResponse",
    "ProjectResponse",
    "ProjectsResponse",
    "BranchResponse",
    "BranchesResponse",
    "ContextResponse",
    "DeleteResponse",
    "HealthResponse",
    "AgentsResponse",
    "StatisticsResponse",
    "CountResponse",
    # Bulk Operations
    "BulkSummaryRequest",
    "BulkSummaryResponse",
    "BulkSummaryMetadata",
    # Conversion Helpers
    "task_to_dto",
    "subtask_to_dto",
    "task_summary_to_dto",
    "subtask_summary_to_dto",
]