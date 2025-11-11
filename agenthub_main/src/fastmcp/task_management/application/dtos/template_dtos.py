"""Template Data Transfer Objects"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TemplateCreateDTO:
    """DTO for creating a new template"""

    name: str
    description: str
    content: str
    template_type: str
    category: str
    priority: str = "medium"
    compatible_agents: list[str] = None
    file_patterns: list[str] = None
    variables: list[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.compatible_agents is None:
            self.compatible_agents = ["*"]
        if self.file_patterns is None:
            self.file_patterns = []
        if self.variables is None:
            self.variables = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TemplateUpdateDTO:
    """DTO for updating an existing template"""

    template_id: str
    name: str | None = None
    description: str | None = None
    content: str | None = None
    template_type: str | None = None
    category: str | None = None
    priority: str | None = None
    compatible_agents: list[str] | None = None
    file_patterns: list[str] | None = None
    variables: list[str] | None = None
    metadata: dict[str, Any] | None = None
    is_active: bool | None = None


@dataclass
class TemplateResponseDTO:
    """DTO for template response"""

    id: str
    name: str
    description: str
    content: str
    template_type: str
    category: str
    status: str
    priority: str
    compatible_agents: list[str]
    file_patterns: list[str]
    variables: list[str]
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    version: int
    is_active: bool


@dataclass
class TemplateListDTO:
    """DTO for template list response"""

    templates: list[TemplateResponseDTO]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


@dataclass
class TemplateRenderRequestDTO:
    """DTO for template render request"""

    template_id: str
    variables: dict[str, Any]
    task_context: dict[str, Any] | None = None
    output_path: str | None = None
    cache_strategy: str = "default"
    force_regenerate: bool = False


@dataclass
class TemplateRenderResponseDTO:
    """DTO for template render response"""

    content: str
    template_id: str
    variables_used: dict[str, Any]
    generated_at: str
    generation_time_ms: int
    cache_hit: bool
    output_path: str | None = None


@dataclass
class TemplateSuggestionDTO:
    """DTO for template suggestion"""

    template_id: str
    name: str
    description: str
    template_type: str
    category: str
    priority: str
    suggestion_score: float
    suggestion_reason: str
    compatible_agents: list[str]
    file_patterns: list[str]
    variables: list[str]


@dataclass
class TemplateSuggestionRequestDTO:
    """DTO for template suggestion request"""

    task_context: dict[str, Any]
    agent_type: str | None = None
    file_patterns: list[str] | None = None
    limit: int = 10


@dataclass
class TemplateUsageDTO:
    """DTO for template usage tracking following clean relationship chain"""

    template_id: str
    task_id: str | None = (
        None  # Contains all necessary context via task -> git_branch -> project -> user
    )
    agent_name: str | None = None
    variables_used: dict[str, Any] = None
    output_path: str | None = None
    generation_time_ms: int = 0
    cache_hit: bool = False
    used_at: str | None = None

    def __post_init__(self):
        if self.variables_used is None:
            self.variables_used = {}
        # Note: used_at timestamp should be set by the service layer when creating usage records
        # This DTO should receive the timestamp from the business logic, not generate it automatically


@dataclass
class TemplateAnalyticsDTO:
    """DTO for template analytics following clean relationship chain"""

    template_id: str | None = None
    usage_count: int = 0
    success_rate: float = 0.0
    avg_generation_time: float = 0.0
    total_generation_time: int = 0
    cache_hit_rate: float = 0.0
    most_used_variables: list[dict[str, Any]] = None
    usage_by_agent: dict[str, int] = None
    usage_by_task: dict[str, int] = (
        None  # Task usage instead of project (follows clean relationship chain)
    )
    usage_over_time: list[dict[str, Any]] = None

    def __post_init__(self):
        if self.most_used_variables is None:
            self.most_used_variables = []
        if self.usage_by_agent is None:
            self.usage_by_agent = {}
        if self.usage_by_task is None:
            self.usage_by_task = {}
        if self.usage_over_time is None:
            self.usage_over_time = []


@dataclass
class TemplateSearchDTO:
    """DTO for template search"""

    query: str
    template_type: str | None = None
    category: str | None = None
    agent_compatible: str | None = None
    is_active: bool | None = None
    limit: int = 50
    offset: int = 0


@dataclass
class TemplateValidationDTO:
    """DTO for template validation response"""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    template_id: str | None = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class TemplateCacheDTO:
    """DTO for template cache operations"""

    template_id: str | None = None
    cache_key: str | None = None
    operation: str = "get"  # get, set, delete, clear
    ttl: int | None = None
    data: dict[str, Any] | None = None
